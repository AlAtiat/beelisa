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
        self.app.loading.start()
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
    
        # Calculate global LOD/LOQ
        global_lod = None
        global_loq = None

        
        # calculate them always as fallback if per plate has less than 3 negatives/blanks
        global_lod, global_loq = self._calculate_lod_loq_global(connected_df)

        # Process each plate separately
        plate_names = connected_df['plate_name'].unique()

        for plate_name in plate_names:
            lod_loq_method = None  # "per_plate_od" or "global_od" or None
            lod_od = loq_od = None
            lod = loq = None
            plate_data = connected_df[connected_df['plate_name'] == plate_name].copy()

            # Fit standard curve
            curve_result = self._fit_standard_curve(plate_data)
            curve_fits[plate_name] = curve_result

            # Calculate concentrations if curve fitting succeeded
            if curve_result['success']:
                plate_data = self._calculate_concentrations(plate_data, curve_result)
            else:
                # Mark all concentrations as None if curve fitting failed
                plate_data['concentration'] = None
                plate_data['concentration_dilution_corrected'] = None

            # Calculate QC metrics
            qc = self._compute_qc_metrics(plate_data)
            qc_summary[plate_name] = qc

            # Calculate LOD/LOQ
            if self.lod_loq_mode == "per_plate":
                lod_od, loq_od = self._calculate_lod_loq(plate_data, curve_result)
                if lod_od is not None and loq_od is not None:
                    lod_loq_method = "per_plate_od"
                else:
                    lod_od, loq_od = global_lod, global_loq
                    lod_loq_method = "global_od"
                    self.app.log(f"[{plate_name}] Per plate unavailable -> using GLOBAL fallback.")
            else:
                lod_od, loq_od = global_lod, global_loq
                lod_loq_method = "global_od"
                self.app.log(f"[{plate_name}] Using GLOBAL OD LOD/LOQ (mode=global).")

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
            plate_data = self._classify_results(plate_data, lod, loq)

            all_plate_results.append(plate_data)

        # Concatenate all plate results
        results_df = pd.concat(all_plate_results, ignore_index=True)
        
        # self.app.log(results_df.to_string())
        self.app.loading.stop()
        return {
            'success': True,
            'data_df': results_df,
            'qc_summary': qc_summary,
            'curve_fits': curve_fits,
            'lod_loq': lod_loq_values,
            'glob_lod_loq': glob_lod_loq_values,

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

        # Check for negative controls 
        if 'well_type' in connected_df.columns:
            has_negatives = (connected_df['well_type'] == 'NEGATIVE_CONTROL').any()
            if not has_negatives:
                errors.append("WARNING: No NEGATIVE_CONTROL wells found. LOD/LOQ cannot be calculated.")
                self.app.log("WARNING: No NEGATIVE_CONTROL wells found. LOD/LOQ cannot be calculated.")

        return errors

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

        lod_od = mean_blank + 3 * std_blank
        loq_od = mean_blank + 10 * std_blank
        
        self.app.log(f'LOD/LOQ calculated globaly from {len(glob_blank_od)} blank samples: '
                f'mean={mean_blank:.4f}, std={std_blank:.4f}')

        # For now, use OD Values because concentrations from different plates, they are not comparable because each plate might use a different fit. conversion happens in per-plate processing
        return lod_od, loq_od

    def _classify_results(self, plate_data, lod, loq):
        """
        Classify results based on LOD/LOQ thresholds.

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

            if lod is None or loq is None:
                statuses.append('LOD/LOQ Not Available')
                continue

            if od < lod:
                statuses.append('Below detection (LOD)')
            elif lod <= od < loq:
                statuses.append('Borderline (LOD to LOQ)')
            else:
                statuses.append('Quantifiable (above LOQ)')

        plate_data['detection_status'] = statuses

        return plate_data
