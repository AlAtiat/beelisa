import pandas as pd
import numpy as np
from .selection import ModelSelector
from .models.registry import ModelRegistry


class AnalysisEngine:
    """ELISA analysis orchestration with QC, curve fitting, and LOD/LOQ calculations."""

    def __init__(self, app):
        self.app = app
        self.calibrant_concentrations = {}
        self.dilution_factor = 1.0
        self.lod_loq_mode = "per_plate"  # "per_plate" or "global"
        self.apply_blank_subtraction = True
        self.apply_plate_factor_correction = False

    def run_analysis(self, connected_df):
        """
        Main analysis workflow.

        Parameters:
            connected_df: DataFrame with merged plate data

        Returns:
            dict with keys:
                - success: bool
                - data_df: DataFrame with concentrations and classifications
                - qc_summary: dict of QC metrics per plate
                - curve_fits: dict of curve parameters per plate
                - lod_loq: dict of LOD/LOQ values per plate
                - glob_lod_loq: dict of LOD/LOQ values globaly
                - errors: list of error messages (if any)
        """
        # Validate inputs
        errors = self._validate_inputs(connected_df)
        if errors:
            return {'success': False, 'errors': errors}

        # Initialize results storage
        all_plate_results = []
        qc_summary = {}
        curve_fits = {}
        lod_loq_values = {}
        glob_lod_loq_values = {}
    
        # Process each plate separately
        plate_names = connected_df['plate_name'].unique()

        # Create one blank-subtracted copy upfront; reused for global LOD/LOQ and plate factors.
        # When blank subtraction is off, sub_df is identical to connected_df.
        sub_df = connected_df.copy()
        if self.apply_blank_subtraction:
            for pn in plate_names:
                pdata = sub_df[sub_df['plate_name'] == pn]
                bm = self._compute_blank_mean(pdata)
                if bm != 0.0:
                    sub_df.loc[sub_df['plate_name'] == pn, 'od_value'] -= bm

        # Global LOD/LOQ computed on the same blank-subtracted OD space as per-plate computation
        global_lod = None
        global_loq = None
        global_lod, global_loq = self._calculate_lod_loq_global(connected_df)

        # Pre-compute plate factors from blank-subtracted calibrant ODs (needs all plates at once)
        # Factors are computed per group when plate_groups are defined so that independent
        # experimental runs are not normalised against each other.
        plate_factors = {}
        if self.apply_plate_factor_correction:
            plate_groups = getattr(self.app, 'plate_groups', {})
            if plate_groups:
                grouped_plates = set()
                for group_name, group_plates in plate_groups.items():
                    valid_group = [pn for pn in group_plates if pn in set(plate_names)]
                    if not valid_group:
                        continue
                    if len(valid_group) < 2:
                        for pn in valid_group:
                            plate_factors[pn] = 1.0
                        grouped_plates.update(valid_group)
                        self.app.log(f'[Group: {group_name}] Only 1 plate — F = 1.0 (no-op)')
                        continue
                    group_sub = sub_df[sub_df['plate_name'].isin(valid_group)]
                    group_factors = self._compute_plate_factors(group_sub)
                    plate_factors.update(group_factors)
                    grouped_plates.update(valid_group)
                    self.app.log(f'[Group: {group_name}] Factors from {len(valid_group)} plates')
                ungrouped = [pn for pn in plate_names if pn not in grouped_plates]
                if ungrouped:
                    ug_sub = sub_df[sub_df['plate_name'].isin(ungrouped)]
                    ug_factors = self._compute_plate_factors(ug_sub)
                    plate_factors.update(ug_factors)
                    self.app.log(f'[Ungrouped] Factors from {len(ungrouped)} plates')
            else:
                plate_factors = self._compute_plate_factors(sub_df)

            for pn, f in plate_factors.items():
                self.app.log(f'Plate factor [{pn}]: F = {f:.4f}')

        for plate_name in plate_names:
            lod_loq_method = None  # "per_plate_od" or "global_od" or None
            lod_od = loq_od = None
            lod = loq = None
            plate_data = connected_df[connected_df['plate_name'] == plate_name].copy()

            # Step A: QC from raw ODs (before any blank subtraction)
            qc = self._compute_qc_metrics(plate_data)
            qc_summary[plate_name] = qc

            # Step C': Compute LOD/LOQ from RAW plate_data (before any subtraction)
            #          LOD_raw = μₙ + 3·σₙ  where μₙ, σₙ are from raw NC/blank wells
            lod_od_raw = loq_od_raw = None
            if self.lod_loq_mode == "per_plate":
                lod_od_raw, loq_od_raw = self._calculate_lod_loq(plate_data, None)
                if lod_od_raw is not None:
                    lod_loq_method = "per_plate_od"
                else:
                    self.app.log(f"[{plate_name}] Per plate unavailable -> using GLOBAL fallback.")

            # Step B: Blank subtraction
            blank_mean = 0.0
            if self.apply_blank_subtraction:
                blank_mean = self._compute_blank_mean(plate_data)
                if blank_mean != 0.0:
                    plate_data['od_value'] = plate_data['od_value'] - blank_mean
                    self.app.log(f'[{plate_name}] Blank-subtracted {blank_mean:.4f} OD from all wells')

            # Step C'': Convert LOD/LOQ thresholds into blank-subtracted space
            #           LOD' = LOD_raw − μₙ = 3·σₙ  (always > 0)
            if lod_od_raw is not None:
                lod_od = lod_od_raw - blank_mean
                loq_od = loq_od_raw - blank_mean
            else:
                # Global fallback already in blank-subtracted space from pre-loop
                lod_od, loq_od = global_lod, global_loq
                lod_loq_method = "global_od"
                if self.lod_loq_mode != "per_plate":
                    self.app.log(f"[{plate_name}] Using GLOBAL OD LOD/LOQ (mode=global).")

            # Step B.5: Plate factor correction + scale LOD/LOQ thresholds into corrected space
            if self.apply_plate_factor_correction:
                f = plate_factors.get(plate_name, 1.0)
                if f > 0 and f != 1.0:
                    plate_data['od_value'] = plate_data['od_value'] / f
                    if lod_od is not None:
                        lod_od = lod_od / f
                    if loq_od is not None:
                        loq_od = loq_od / f

            # Step D: Clip to 0 after LOD computation
            # if blank_mean != 0.0:
            #     plate_data['od_value'] = plate_data['od_value'].clip(lower=0)

            # Step E: Fit standard curve and calculate concentrations (on clipped data)
            curve_result = self._fit_standard_curve(plate_data)
            curve_fits[plate_name] = curve_result

            if curve_result['success']:
                plate_data = self._calculate_concentrations(plate_data, curve_result)
            else:
                plate_data['concentration'] = None
                plate_data['concentration_dilution_corrected'] = None

            # OD thresholds -> concentration using each plate curve
            model = curve_result.get("model")
            params = curve_result.get("params")

            if model is not None and params is not None and lod_od is not None and loq_od is not None:
                lod_tmp = model.inverse(lod_od, params)
                loq_tmp = model.inverse(loq_od, params)

                lod = (lod_tmp * self.dilution_factor) if (lod_tmp is not None and np.isfinite(lod_tmp)) else None
                loq = (loq_tmp * self.dilution_factor) if (loq_tmp is not None and np.isfinite(loq_tmp)) else None
            else:
                lod = loq = None
                

            lod_loq_values[plate_name] = {
                'lod': lod,
                'loq': loq,
                'lod_od': lod_od,
                'loq_od': loq_od,
                'lod_loq_method': lod_loq_method
            }

            glob_lod_loq_values[plate_name] = {
                'global_lod_od': global_lod,
                'global_loq_od': global_loq
            }



            # Classify results
            plate_data = self._classify_results(plate_data, lod_od, loq_od)

            all_plate_results.append(plate_data)

        # Concatenate all plate results
        results_df = pd.concat(all_plate_results, ignore_index=True)

        return {
            'success': True,
            'data_df': results_df,
            'qc_summary': qc_summary,
            'curve_fits': curve_fits,
            'lod_loq': lod_loq_values,
            'glob_lod_loq': glob_lod_loq_values,
            'plate_factors': plate_factors,

        }

    def _validate_inputs(self, connected_df):
        """Validate analysis inputs."""
        errors = []

        if connected_df is None or connected_df.empty:
            errors.append("No data loaded. Please load plate data first.")
            self.app.log("No data loaded. Please load plate data first.")
            return errors

        # Check for required columns
        required_cols = ['plate_name', 'well_type', 'od_value']
        missing_cols = [col for col in required_cols if col not in connected_df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {', '.join(missing_cols)}")
            self.app.log(f"Missing required columns: {', '.join(missing_cols)}")

        # Check for calibrants
        if 'well_type' in connected_df.columns:
            has_calibrants = (connected_df['well_type'] == 'CALIBRANT').any()
            if not has_calibrants:
                errors.append("No CALIBRANT wells found. Please define calibrants in plate design.")
                self.app.log("No CALIBRANT wells found. Please define calibrants in plate design.")

        # Check for calibrant concentrations
        if not self.calibrant_concentrations:
            errors.append("No calibrant concentrations provided. Please enter calibrant concentrations.")
            self.app.log("No calibrant concentrations provided. Please enter calibrant concentrations.")

        # Check for blank or negative control wells (either satisfies LOD/LOQ requirement)
        if 'well_type' in connected_df.columns:
            has_blanks    = (connected_df['well_type'] == 'BLANK').any()
            has_negatives = (connected_df['well_type'] == 'NEGATIVE_CONTROL').any()
            if not has_blanks and not has_negatives:
                errors.append("WARNING: No BLANK or NEGATIVE_CONTROL wells found. LOD/LOQ cannot be calculated.")
                self.app.log("WARNING: No BLANK or NEGATIVE_CONTROL wells found. LOD/LOQ cannot be calculated.")

        return errors

    def _compute_blank_mean(self, plate_data):
        """Mean OD of BLANK wells; falls back to NEGATIVE_CONTROL if none."""
        blanks = plate_data[plate_data['well_type'] == 'BLANK']['od_value'].dropna()
        if len(blanks) == 0:
            blanks = plate_data[plate_data['well_type'] == 'NEGATIVE_CONTROL']['od_value'].dropna()
        if len(blanks) == 0:
            return 0.0
        return float(blanks.mean())

    def _compute_plate_factors(self, sub_df):
        """ multiplicative plate factors using mid-range calibrant ODs.

        Algorithm:
        1. Compute per-plate per-order median OD: m_{p,k}  (median within plate/level,
           avoids replicate-count distortion).
        2. Compute per-order across-plate median reference: r_k  (median of m_{p,k},
           robust to one outlier plate).
        3. all levels where r_k > 0 are included in the factor computation.
        4. Compute log(m_{p,k} / r_k) for each plate at each included order.
        5. F_plate = exp(median of log-ratios).  Median is robust to one bad level.

        Returns {plate_name: F_plate}. Single-plate runs return F=1.0 (no-op).
        """
        calibrants = sub_df[sub_df['well_type'] == 'CALIBRANT'].copy()
        if calibrants.empty:
            return {}

        plate_names = calibrants['plate_name'].unique()
        if len(plate_names) < 2:
            return {pn: 1.0 for pn in plate_names}

        # Step 1: per-plate per-order median OD (m_{p,k})
        plate_order_medians = calibrants.groupby(['plate_name', 'order'])['od_value'].median()

        # Step 2: per-order across-plate median reference (r_k)
        order_vals = calibrants['order'].dropna().unique()
        order_refs = {}
        for order_val in order_vals:
            vals = []
            for pn in plate_names:
                try:
                    m = plate_order_medians.loc[(pn, order_val)]
                    if pd.notna(m):
                        vals.append(float(m))
                except KeyError:
                    pass
            if len(vals) >= 2:
                order_refs[order_val] = float(np.median(vals))

        if not order_refs:
            return {pn: 1.0 for pn in plate_names}

        # Step 3: use all levels; skip only those with non-positive reference
        # (r_k <= 0 means no usable signal at that level after blank subtraction)
        mid_range = {k for k, r in order_refs.items() if r > 0}
        if not mid_range:
            mid_range = set(order_refs.keys())

        # Steps 4 & 5: log-ratios per plate → median → factor
        log_ratios = {pn: [] for pn in plate_names}
        for order_val in mid_range:
            r_k = order_refs[order_val]
            if r_k <= 0:
                continue
            for pn in plate_names:
                try:
                    m_pk = plate_order_medians.loc[(pn, order_val)]
                    if pd.notna(m_pk) and float(m_pk) > 0:
                        log_ratios[pn].append(np.log(float(m_pk) / r_k))
                except KeyError:
                    pass

        factors = {}
        for pn in plate_names:
            logs = log_ratios.get(pn, [])
            factors[pn] = float(np.exp(np.median(logs))) if logs else 1.0
        return factors

    def _fit_standard_curve(self, plate_data):
        """Fit multiple models and select best using AIC/BIC."""
        # Filter calibrants
        calibrants = plate_data[plate_data['well_type'] == 'CALIBRANT'].copy()

        if calibrants.empty:
            return {
                'success': False,
                'error': 'No calibrant wells in this plate',
                'comparison_df': None
            }

        # Map order to concentration
        calibrants['concentration'] = calibrants['order'].map(self.calibrant_concentrations)

        # Filter valid calibrants (have both concentration and OD)
        valid = calibrants.dropna(subset=['concentration', 'od_value'])
        self.app.log(f'Amount of Calibrants per plate: {len(valid)}')
        if len(valid) < 2:  # Need at least 2 points for any model
            return {
                'success': False,
                'error': f'Need at least 2 calibrant points, found {len(valid)}',
                'comparison_df': None
            }

        # Fit all models and compare
        selector = ModelSelector(selection_method="bic")
        comparison = selector.compare_models(
            valid['concentration'].values,
            valid['od_value'].values
        )

        # Get best fit
        best_fit = selector.get_best_fit(comparison)

        if best_fit is None or not best_fit.success:
            return {
                'success': False,
                'error': 'All models failed to fit',
                'comparison_df': comparison.comparison_df
            }

        # Get the model instance for inverse calculations
        best_model = ModelRegistry.get_model(best_fit.model_name)

        return {
            'success': True,
            'selection_method': comparison.selection_method,
            'model_name': best_fit.model_name,
            'model': best_model,
            'params': best_fit.params,
            'param_names': best_fit.param_names,
            'r_squared': best_fit.r_squared,
            'adjusted_r_squared': best_fit.adjusted_r_squared,
            'aic': best_fit.aic,
            'bic': best_fit.bic,
            'rmse': best_fit.rmse,
            'residuals': best_fit.residuals,
            'fitted_values': best_fit.fitted_values,
            'comparison_df': comparison.comparison_df,
            'all_model_results': comparison.all_results
        }

    def _calculate_concentrations(self, plate_data, curve_result):
        """Calculate concentrations for all wells using fitted curve."""
        model = curve_result.get('model')
        params = curve_result.get('params')

        concentrations = []
        concentrations_corrected = []

        for _, row in plate_data.iterrows():
            od_value = row['od_value']
            well_type = row['well_type']
            
            if pd.isna(od_value):
                concentrations.append(None)
                concentrations_corrected.append(None)
                continue

            # Wrap inverse call in try-except for robustness
            try:
                conc = model.inverse(od_value, params)
                # Validate result
                if conc is None or not np.isfinite(conc) or conc < 0:
                    conc = None
            except Exception:
                conc = None

            # Apply dilution factor for samples only and keep other well types same concentrations
            if conc is not None and well_type == 'SAMPLE':
                conc_corrected = conc * self.dilution_factor
            else:
                conc_corrected = conc

            concentrations.append(conc)
            concentrations_corrected.append(conc_corrected)

        plate_data['concentration'] = concentrations
        plate_data['concentration_dilution_corrected'] = concentrations_corrected

        # Calibrant concentrations are known configured values — never derive them
        # from curve inversion (which fails for low-OD calibrants near the LOD).
        if 'order' in plate_data.columns:
            cal_mask = plate_data['well_type'] == 'CALIBRANT'
            original_conc = plate_data.loc[cal_mask, 'order'].map(self.calibrant_concentrations)
            plate_data.loc[cal_mask, 'concentration'] = original_conc
            plate_data.loc[cal_mask, 'concentration_dilution_corrected'] = original_conc

        return plate_data

    def _compute_qc_metrics(self, plate_data):
        """Compute QC metrics per well type with correct replicate CV."""
        qc = {}
        MIN_FOR_CV = 2
        NEAR_ZERO_THRESHOLD = 0.01  # Below this mean, CV is unreliable

        for well_type in ['NEGATIVE_CONTROL', 'CALIBRANT', 'SAMPLE', 'BLANK', 'POSITIVE_CONTROL']:
            wells = plate_data[plate_data['well_type'] == well_type]
            od_values = wells['od_value'].dropna()

            if len(od_values) == 0:
                continue

            mean_od = od_values.mean()
            std_od = od_values.std() if len(od_values) >= MIN_FOR_CV else None
            median_cv = None

            # Compute replicate CV correctly based on well type
            if well_type == 'CALIBRANT' and 'order' in wells.columns:
                # CV per concentration level (order), report worst CV
                replicate_cvs = []
                for order_val in wells['order'].dropna().unique():
                    order_wells = wells[wells['order'] == order_val]['od_value'].dropna()
                    if len(order_wells) >= MIN_FOR_CV:
                        m = order_wells.mean()
                        if m > NEAR_ZERO_THRESHOLD:
                            cv = (order_wells.std(ddof=1) / m) * 100
                            replicate_cvs.append(cv)
                cv_percent = max(replicate_cvs) if replicate_cvs else None
                median_cv = np.median(replicate_cvs) if replicate_cvs else None

            elif well_type == 'SAMPLE' and 'sample_id' in wells.columns:
                # CV per sample_id (replicates only)
                replicate_cvs = []
                for sid in wells['sample_id'].dropna().unique():
                    sample_wells = wells[wells['sample_id'] == sid]['od_value'].dropna()
                    if len(sample_wells) >= MIN_FOR_CV:
                        m = sample_wells.mean()
                        if m > NEAR_ZERO_THRESHOLD:
                            cv = (sample_wells.std() / m) * 100
                            replicate_cvs.append(cv)
                cv_percent = max(replicate_cvs) if replicate_cvs else None
                median_cv = np.median(replicate_cvs) if replicate_cvs else None

            else:
                # Controls/Blank: CV across all replicates (with n>=2 check)
                if len(od_values) >= MIN_FOR_CV and mean_od > NEAR_ZERO_THRESHOLD:
                    cv_percent = (std_od / mean_od) * 100
                else:
                    cv_percent = None

            # Thresholds
            threshold = {'CALIBRANT': 15, 'NEGATIVE_CONTROL': 30}.get(well_type, 20)
            high_cv = cv_percent is not None and cv_percent > threshold

            qc[well_type] = {
                'n_wells': len(od_values),
                'mean_od': mean_od,
                'std_od': std_od,
                'cv_percent': cv_percent,
                'median_cv': median_cv,
                'high_cv_warning': high_cv
            }

        return qc

    def _calculate_lod_loq(self, plate_data, curve_result):
        """
        Calculate LOD and LOQ using blank sample method (yet for our case negative because we dont have blank)

        LOD = Mean(blank od) + 3 × SD(blank od)
        LOQ = Mean(blank od) + 9 × SD(blank od)

        Standard requires at least 20 blank samples, but we use minimum of 3.
        Prefers BLANK wells, falls back to NEGATIVE_CONTROL.
        """
        # Get blank samples (prefer BLANK if not available such as for our case fallback to NEGATIVE_CONTROL)
        blanks = plate_data[plate_data['well_type'] == 'BLANK']
        if blanks.empty:
            blanks = plate_data[plate_data['well_type'] == 'NEGATIVE_CONTROL']

        if blanks.empty or len(blanks) < 3:
            self.app.log('Insufficient blank samples for LOD/LOQ per Plate calculation (need at least 3) trying Globaly for all plates')
            return None, None

        # Get blank od (
        blank_od = blanks['od_value'].dropna()
        if len(blank_od) < 3:
            return None, None        

        # Calculate LOD and LOQ using od values
        mean_blank = blank_od.mean()
        std_blank = blank_od.std(ddof=1)  # Sample standard deviation

        lod_od = mean_blank + 3 * std_blank # some use 3 and some 3.3
        loq_od = mean_blank + 10 * std_blank  # some use 9 and some 10

        self.app.log(f'LOD/LOQ calculated per plate from {len(blank_od)} blank samples: '
                     f'mean={mean_blank:.4f}, std={std_blank:.4f}')

        return lod_od, loq_od

    def _calculate_lod_loq_global(self, connected_df):
        """Calculate global LOD/LOQ from all NEGATIVE_CONTROL wells."""
        glob_blanks = connected_df[connected_df['well_type'] == 'BLANK']
        if glob_blanks.empty:
            glob_blanks = connected_df[connected_df['well_type'] == 'NEGATIVE_CONTROL']
        glob_blank_od = glob_blanks['od_value'].dropna()

        if len(glob_blank_od) < 3:
            return None, None

        mean_blank = glob_blank_od.mean()
        std_blank = glob_blank_od.std(ddof=1)

        lod_raw = mean_blank + 3 * std_blank
        loq_raw = mean_blank + 10 * std_blank
        
        self.app.log(f'LOD/LOQ calculated globaly from {len(glob_blank_od)} blank samples: '
                f'mean={mean_blank:.4f}, std={std_blank:.4f}')

        ## If we will subtract baseline later, report thresholds in subtracted space:
        # LOD' = (mean + 3sd) - mean = 3sd
        # LOQ' = 10sd
        if self.apply_blank_subtraction:
            lod_od = 3 * std_blank
            loq_od = 10 * std_blank
            self.app.log(f'GLOBAL LOD/LOQ (corrected space) from {len(glob_blank_od)} wells: sd={std_blank:.4f}')
        else:
            lod_od, loq_od = lod_raw, loq_raw
            self.app.log(f'GLOBAL LOD/LOQ (raw space) from {len(glob_blank_od)} wells: mean={mean_blank:.4f}, sd={std_blank:.4f}')
            
        # For now, use OD Values because concentrations from different plates, they are not comparable because each plate might use a different fit. conversion happens in per-plate processing
        return lod_od, loq_od

    def _classify_results(self, plate_data, lod_od, loq_od):
        """
        Classify results based on OD-space LOD/LOQ thresholds.

        Classification:
            - < LOD: "Negative" or "Below Detection"
            - LOD to LOQ: "Borderline" (LOD to LOQ)"
            - > LOQ: "Quantifiable (above LOQ)"
        """
        statuses = []

        for _, row in plate_data.iterrows():
            well_type = row['well_type']
            od = row.get('od_value')

            # Only classify SAMPLE wells
            if well_type != 'SAMPLE':
                statuses.append('N/A')
                continue

            if od is None or pd.isna(od) or not np.isfinite(od):
                statuses.append('Invalid')
                continue

            if lod_od is None or loq_od is None:
                statuses.append('LOD/LOQ Not Available')
                continue

            if od < lod_od:
                statuses.append('Below detection (LOD)')
            elif lod_od <= od < loq_od:
                statuses.append('Borderline (LOD to LOQ)')
            else:
                statuses.append('Quantifiable (above LOQ)')

        plate_data['detection_status'] = statuses

        return plate_data
