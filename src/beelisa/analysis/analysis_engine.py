import pandas as pd
import numpy as np
from .selection import ModelSelector
from .models.registry import ModelRegistry
import asyncio


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

        # Calculate global LOD/LOQ if needed
        global_lod = None
        global_loq = None
        if self.lod_loq_mode == "global":
            global_lod, global_loq = self._calculate_lod_loq_global(connected_df)

        # Process each plate separately
        plate_names = connected_df['plate_name'].unique()

        for plate_name in plate_names:
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
                self.app.loading.stop()

            # Calculate QC metrics
            qc = self._compute_qc_metrics(plate_data)
            qc_summary[plate_name] = qc

            # Calculate LOD/LOQ
            if self.lod_loq_mode == "per_plate":
                lod, loq = self._calculate_lod_loq(plate_data, curve_result)
            else:
                lod, loq = global_lod, global_loq
                self.app.loading.stop()

            lod_loq_values[plate_name] = {'lod': lod, 'loq': loq}

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
            'lod_loq': lod_loq_values
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

        # Check for negative controls (optional warning, not error)
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
            'model_name': best_fit.model_name,
            'model': best_model,  # Store model instance
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

            if pd.isna(od_value):
                concentrations.append(None)
                concentrations_corrected.append(None)
                continue

            # Predict concentration from OD using model's inverse method
            conc = model.inverse(od_value, params)

            # Apply dilution factor
            conc_corrected = conc * self.dilution_factor if conc is not None and np.isfinite(conc) else None

            concentrations.append(conc)
            concentrations_corrected.append(conc_corrected)

        plate_data['concentration'] = concentrations
        plate_data['concentration_dilution_corrected'] = concentrations_corrected

        return plate_data

    def _compute_qc_metrics(self, plate_data):
        """Compute QC metrics per well type."""
        qc = {}

        for well_type in ['NEGATIVE_CONTROL', 'CALIBRANT', 'SAMPLE', 'BLANK', 'POSITIVE_CONTROL']:
            wells = plate_data[plate_data['well_type'] == well_type]
            od_values = wells['od_value'].dropna()

            if len(od_values) == 0:
                continue

            mean_od = od_values.mean()
            std_od = od_values.std()
            cv_percent = (std_od / mean_od * 100) if mean_od > 0 else np.inf

            # Define CV% thresholds
            if well_type == 'CALIBRANT':
                threshold = 15
            elif well_type == 'NEGATIVE_CONTROL':
                threshold = 30
            else:
                threshold = 20

            qc[well_type] = {
                'n_wells': len(od_values),
                'mean_od': mean_od,
                'std_od': std_od,
                'cv_percent': cv_percent,
                'high_cv_warning': cv_percent > threshold
            }

        return qc

    def _calculate_lod_loq(self, plate_data, curve_result):
        """
        Calculate LOD and LOQ using blank sample method (yet for our case negative because we dont have blank)

        LOD = Mean(blank concentrations) + 3 × SD(blank concentrations)
        LOQ = Mean(blank concentrations) + 9 × SD(blank concentrations)

        Standard requires at least 20 blank samples, but we use minimum of 3.
        Prefers BLANK wells, falls back to NEGATIVE_CONTROL.
        """
        # Get blank samples (prefer BLANK if not available such as for our case fallback to NEGATIVE_CONTROL)
        blanks = plate_data[plate_data['well_type'] == 'BLANK']
        if blanks.empty:
            blanks = plate_data[plate_data['well_type'] == 'NEGATIVE_CONTROL']

        if blanks.empty or len(blanks) < 3:
            self.app.log('Insufficient blank samples for LOD/LOQ calculation (need at least 3)')
            return None, None

        # Get blank concentrations (already calculated by _calculate_concentrations)
        blank_concentrations = blanks['concentration_dilution_corrected'].dropna()
        
        # if len(blank_concentrations) < 3:
        #     # If concentrations not available, convert OD values
        #     blank_od = blanks['od_value'].dropna()
        #     if len(blank_od) < 3:
        #         return None, None

        #     # Convert OD to concentration using inverse
        #     model = curve_result.get('model')
        #     params = curve_result.get('params')

        #     if model and params is not None:
        #         blank_concs = []
        #         for od in blank_od:
        #             conc = model.inverse(od, params)
        #             if conc is not None and np.isfinite(conc):
        #                 # Apply dilution factor
        #                 conc_corrected = conc * self.dilution_factor
        #                 blank_concs.append(conc_corrected)
        #         blank_concentrations = pd.Series(blank_concs)

        if len(blank_concentrations) < 3:
            self.app.log("Blank/Negative Concentrations less than 3")
            return None, None

        # Calculate LOD and LOQ using concentration values
        mean_blank = blank_concentrations.mean()
        std_blank = blank_concentrations.std(ddof=1)  # Sample standard deviation

        lod = mean_blank + 3 * std_blank
        loq = mean_blank + 9 * std_blank  # Changed from 10 to 9 per standard

        self.app.log(f'LOD/LOQ calculated from {len(blank_concentrations)} blank samples: '
                     f'mean={mean_blank:.4f}, std={std_blank:.4f}')

        return lod, loq

    def _calculate_lod_loq_global(self, connected_df):
        """Calculate global LOD/LOQ from all NEGATIVE_CONTROL wells."""
        neg_controls = connected_df[connected_df['well_type'] == 'NEGATIVE_CONTROL']
        neg_od = neg_controls['od_value'].dropna()

        if len(neg_od) < 3:
            return None, None

        mean_blank = neg_od.mean()
        std_blank = neg_od.std()

        lod_od = mean_blank + 3 * std_blank
        loq_od = mean_blank + 10 * std_blank

        # Note: For global LOD/LOQ, we'll need to convert using each plate's curve
        # For now, return OD values - conversion happens in per-plate processing
        return lod_od, loq_od

    def _classify_results(self, plate_data, lod, loq):
        """
        Classify results based on LOD/LOQ thresholds.

        Classification:
            - < LOD: "Negative" or "Below Detection"
            - LOD to LOQ: "Detected, Not Quantifiable"
            - > LOQ: "Quantifiable"
        """
        statuses = []

        for _, row in plate_data.iterrows():
            well_type = row['well_type']
            conc = row.get('concentration_dilution_corrected')

            # Only classify SAMPLE wells
            if well_type != 'SAMPLE':
                statuses.append('N/A')
                continue

            if conc is None or pd.isna(conc) or not np.isfinite(conc):
                statuses.append('Invalid')
                continue

            if lod is None or loq is None:
                statuses.append('LOD/LOQ Not Available')
                continue

            if conc < lod:
                statuses.append('Below Detection')
            elif conc < loq:
                statuses.append('Detected, Not Quantifiable')
            else:
                statuses.append('Quantifiable')

        plate_data['detection_status'] = statuses

        return plate_data
