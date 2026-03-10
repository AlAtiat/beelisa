import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import pandas as pd
import os
import zipfile
from datetime import datetime


class ResultsView:
    """ELISA resutls interface with results display."""

    def __init__(self, app):
        self.app = app
        self.results_table = None
        self.qc_summary = None
        self.curve_info = None
        self.current_plots = {}  # Store generated plot paths
        self.current_plot_type = None  # Track which plot type is currently displayed
        self.current_gallery = []   # list of (key, path, display_name)
        self.gallery_index = -1

        # Plate grouping elements
        self.plate_switches = {}  # {plate_name: toga.Switch}
        self.plates_container = None
        self.groups_list_container = None
        self.group_name_input = None

        # ROC plot (stored in current_plots['roc'], shown in Plots tab)
        self.plot_roc_btn = None

    def create_layout(self):
        """Create result view layout."""
        results = self.create_results_section()
        return toga.Box(
            children=[results],
            style=Pack(direction=COLUMN, flex=1, margin=10),
        )


    def create_results_section(self):
        """Create tabbed results display."""
        results_box = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=5))

        results_label = toga.Label(
            'ANALYSIS RESULTS',
            style=Pack(margin=5, font_weight='bold', font_size=14)
        )
        results_box.add(results_label)
        results_box.add(toga.Divider())

        # Create tabs
        self.results_tabs = toga.OptionContainer(style=Pack(flex=1, margin=5))

        # Results Table tab
        results_table_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self.results_table = toga.Table(
            headings=['Plate', 'Sample ID', 'Well', 'OD', 'Concentration', 'LOD/LOQ Status'],
            data=[],
            style=Pack(flex=1, margin=5)
        )
        results_table_box.add(self.results_table)

        # QC Summary tab
        qc_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self.qc_summary = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, margin=5)
        )
        qc_box.add(self.qc_summary)

        # Model Comparison tab
        model_comp_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self.model_comparison = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, margin=5)
        )
        model_comp_box.add(self.model_comparison)

        # Plots tab
        self.plot_std_curve_btn = toga.Button(
            'Standard Curve',
            on_press=self.on_show_standard_curve,
            style=Pack(margin=2, flex=1)
        )
        self.plot_heatmap_btn = toga.Button(
            'Plate Heatmap',
            on_press=self.on_show_heatmap,
            style=Pack(margin=2, flex=1)
        )
        self.plot_pca_btn = toga.Button(
            'PCA Analysis',
            on_press=self.on_show_pca,
            style=Pack(margin=2, flex=1)
        )
        self.plot_trend_btn = toga.Button(
            'Pattern Analysis',
            on_press=self.on_show_trend,
            style=Pack(margin=2, flex=1)
        )
        self.plot_correlation_btn = toga.Button(
            'Correlation Heatmap',
            on_press=self.on_show_correlation_heatmap,
            style=Pack(margin=2, flex=1)
        )
        self.plot_violin_btn = toga.Button(
            'Violin Plot',
            on_press=self.on_show_violin,
            style=Pack(margin=2, flex=1)
        )
        self.plot_roc_btn = toga.Button(
            'ROC Analysis',
            on_press=self.on_show_roc,
            style=Pack(margin=2, flex=1)
        )
        plot_buttons_box = toga.Box(
            children=[
                self.plot_std_curve_btn,
                self.plot_heatmap_btn,
                self.plot_pca_btn,
                self.plot_trend_btn,
                self.plot_correlation_btn,
                self.plot_violin_btn,
                self.plot_roc_btn,
            ],
            style=Pack(direction=ROW, margin=5),
        )

        # Navigation arrows (for plot types with multiple images)
        self.prev_plot_btn = toga.Button(
            '◀',
            on_press=self.on_prev_plot,
            style=Pack(margin=2, width=50)
        )
        self.next_plot_btn = toga.Button(
            '▶',
            on_press=self.on_next_plot,
            style=Pack(margin=2, width=50)
        )
        self.plot_nav_label = toga.Label(
            'No plot selected',
            style=Pack(margin=5)
        )

        nav_box = toga.Box(
            children=[self.prev_plot_btn, self.next_plot_btn],
            style=Pack(direction=ROW),
        )
        nav_label_box = toga.Box(
            children=[self.plot_nav_label],
            style=Pack(direction=ROW),
        )
        nav_outer = toga.Box(
            children=[toga.Box(style=Pack(flex=1)), nav_box, toga.Box(style=Pack(flex=1))],
            style=Pack(direction=ROW, margin=5),
        )
        nav_under = toga.Box(
            children=[toga.Box(style=Pack(flex=1)), nav_label_box, toga.Box(style=Pack(flex=1))],
            style=Pack(direction=ROW, margin=5),
        )

        # ImageView for displaying plots
        self.plot_imageview = toga.ImageView(style=Pack(flex=1, margin=5))

        self._plots_box = toga.Box(
            children=[plot_buttons_box, nav_outer, nav_under, self.plot_imageview],
            style=Pack(direction=COLUMN, flex=1),
        )
        self.results_tabs.content.append('Results Table', results_table_box)
        self.results_tabs.content.append('QC Summary', qc_box)
        self.results_tabs.content.append('Model Comparison', model_comp_box)
        self.results_tabs.content.append('Plots', self._plots_box)

        # Export section
        export_box = toga.Box(style=Pack(direction=ROW, margin=5))

        export_all_btn = toga.Button(
            'Export All Results',
            on_press=self.on_export_all_zip,
            style=Pack(margin=5)
        )
        
        clear_btn = toga.Button(
            'Clear Results',
            on_press=self.on_clear_results,
            style=Pack(margin=5)
        )

        export_box.add(export_all_btn, clear_btn)
        results_box.add(export_box)

        results_box.add(self.results_tabs)

        return results_box

    def update_results_display(self, results):
        """Update results table, QC summary, and model comparison."""
        # Get concentration unit from config
        unit = self.app.analysis_config.get('concentration_unit', 'U/mL')
        od_wavelength = self.app.analysis_config.get('od_wavelength', '450/620 nm')
        per_group_plots = self.app.analysis_config.get('per_group_plots', True)

        # plate_group column from plate_groups mapping
        if hasattr(self.app, 'plate_groups') and self.app.plate_groups:
            _name_to_group = {
                pn: gname
                for gname, plist in self.app.plate_groups.items()
                for pn in plist
            }
            results['data_df']['plate_group'] = results['data_df']['plate_name'].map(_name_to_group)
            self.app.analysis_results['data_df'] = results['data_df']

        # Update results table
        data_df = results['data_df']
        table_data = []

        for _, row in data_df.iterrows():
            if row['well_type'] == 'SAMPLE':
                plate_name = str(row.get('plate_name', 'N/A'))
                sample_id = str(row.get('sample_id', 'N/A'))
                well_id = str(row.get('well_id', 'N/A'))
                od_value = row.get('od_value')
                concentration = row.get('concentration_dilution_corrected')
                status = str(row.get('detection_status', 'N/A'))

                od_str = f"{od_value:.3f} {od_wavelength}" if pd.notna(od_value) else 'N/A'
                conc_str = f"{concentration:.2f} {unit}" if pd.notna(concentration) and concentration is not None else 'N/A'

                table_data.append((
                    plate_name,
                    sample_id,
                    well_id,
                    od_str,
                    conc_str,
                    status
                ))

        self.results_table.data = table_data

        # Update QC summary
        qc_text = "QC Summary\n" + "=" * 60 + "\n\n"

        for plate, qc in results.get('qc_summary', {}).items():
            qc_text += f"Plate: {plate}\n"
            qc_text += "-" * 60 + "\n"
            
            qc_text += f"Calibrant Concentration Unit: {unit}\n"
            qc_text += f"Optical density (OD): {od_wavelength}\n"
            
            for well_type, metrics in qc.items():
                qc_text += f"\n  {well_type}:\n"
                qc_text += f"    N wells: {metrics['n_wells']}\n"
                mean_od = metrics.get('mean_od')
                std_od = metrics.get('std_od')
                cv_percent = metrics.get('cv_percent')

                mean_od_str = f"{mean_od:.4f}" if mean_od is not None else 'N/A'
                std_od_str = f"{std_od:.4f}" if std_od is not None else 'N/A'
                cv_percent_str = f"{cv_percent:.2f}" if cv_percent is not None else 'N/A'

                qc_text += f"    Mean OD: {mean_od_str}\n"
                qc_text += f"    Std Dev: {std_od_str}\n"
                qc_text += f"    CV%: {cv_percent_str}%\n"

                if metrics.get('high_cv_warning'):
                    qc_text += "    High CV% detected!\n"

            # Add LOD/LOQ info
            lod_loq = results.get('lod_loq', {}).get(plate, {})
            lod_loq_method = lod_loq.get('lod_loq_method')
            lod = lod_loq.get('lod') # as concentration from each plate standard curve
            loq = lod_loq.get('loq') # as concentration from each plate standard curve
            lod_od = lod_loq.get('lod_od')  # in OD 
            loq_od = lod_loq.get('loq_od')  # in OD 
            
            qc_text += "\n  Detection Limits:\n"
            if lod_loq_method is not None and lod_loq_method == 'per_plate_od':
                qc_text += "    LOD/LOQ Method: Per Plate\n"
            else:
                qc_text += "    LOD/LOQ Method: Globaly\n"
            if lod is not None:
                qc_text += f"    LOD: {lod:.3f} {unit}\n"
                qc_text += f"    LOD: {lod_od:.3f} OD\n"
            else:
                qc_text += "    LOD: Not available\n"

            if loq is not None:
                qc_text += f"    LOQ: {loq:.3f} {unit}\n"
                qc_text += f"    LOQ: {loq_od:.3f} OD\n"
            else:
                qc_text += "    LOQ: Not available\n"

            # Inter-plate correction factor
            pf_dict = results.get('plate_factors', {})
            if pf_dict and plate in pf_dict:
                f = pf_dict[plate]
                direction = '↑ plate scaled up' if f < 1.0 else '↓ plate scaled down'
                qc_text += f"\n  Inter-Plate Correction: F = {f:.4f}"
                if f != 1.0:
                    qc_text += f"  ({direction})"
                qc_text += "\n"

            qc_text += "\n" + "=" * 60 + "\n\n"

        self.qc_summary.value = qc_text

        # Update model comparison
        from ..analysis.models.base import MODEL_INFO, SELECTION_INFO

        model_text = "Model Comparison & Selection\n" + "=" * 60 + "\n\n"

        for plate, curve in results.get('curve_fits', {}).items():
            model_text += f"Plate: {plate}\n"
            model_text += "-" * 60 + "\n"

            if curve['success']:
                # Show selected model
                model_name = curve.get('model_name', 'Unknown')
                selection_method = curve.get('selection_method', 'bic')
                model_info = MODEL_INFO.get(model_name, {})
                selection_info = SELECTION_INFO.get(selection_method, {})

                model_text += f"\n SELECTED: {model_info.get('full_name', model_name)}\n"
                model_text += f" Equation: {model_info.get('equation', 'N/A')}\n"
                model_text += f" {model_info.get('description', '')}\n"
                model_text += f" Reference: {model_info.get('literature', 'N/A')}\n"

                # Selection rationale
                model_text += "\n WHY SELECTED:\n"
                model_text += f" Criterion: {selection_info.get('name', selection_method)}\n"
                model_text += f" {selection_info.get('description', '')}\n"
                model_text += f" {selection_info.get('why', '')}\n"

                # Show model parameters with descriptions
                params = curve.get('params', [])
                param_names = curve.get('param_names', [])
                param_descriptions = model_info.get('params', {})
                model_text += "\n  Model Parameters:\n"
                for name, val in zip(param_names, params):
                    desc = param_descriptions.get(name, '')
                    desc_str = f" ({desc})" if desc else ""
                    model_text += f"    {name}: {val:.4f}{desc_str}\n"

                # Show goodness of fit
                model_text += "\n  Goodness of Fit:\n"
                r2 = curve.get('r_squared')
                adj_r2 = curve.get('adjusted_r_squared')
                rmse = curve.get('rmse')
                aic = curve.get('aic')
                bic = curve.get('bic')

                r2_str = f"{r2:.4f}" if r2 is not None else 'N/A'
                adj_r2_str = f"{adj_r2:.4f}" if adj_r2 is not None else 'N/A  (Must be : n > k + 1)'
                rmse_str = f"{rmse:.4f}" if rmse is not None else 'N/A'
                aic_str = f"{aic:.2f}" if aic is not None else 'N/A'
                bic_str = f"{bic:.2f}" if bic is not None else 'N/A'

                model_text += f"    R²: {r2_str} (variance explained)\n"
                model_text += f"    Adjusted R²: {adj_r2_str} (penalized for parameters)\n"
                model_text += f"    RMSE: {rmse_str} (prediction error)\n"
                model_text += f"    AIC: {aic_str} (lower = better fit)\n"
                model_text += f"    BIC: {bic_str} (lower = better fit, penalizes complexity)\n"

                # Show comparison table
                comparison_df = curve.get('comparison_df')
                if comparison_df is not None:
                    model_text += "\n  All Models Comparison:\n"
                    model_text += f"  {'Model':<20} {'Status':<15} {'BIC':<10} {'AIC':<10} {'R²':<8}\n"
                    model_text += f"  {'-'*70}\n"

                    for _, row in comparison_df.iterrows():
                        model = row['Model']
                        status = row['Status']
                        bic = row.get('BIC', 'N/A')
                        aic = row.get('AIC', 'N/A')
                        r2 = row.get('R²', 'N/A')

                        # Mark selected model
                        marker = '→' if model == model_name else ' '

                        bic_str = f"{bic:.2f}" if isinstance(bic, (int, float)) else str(bic)
                        aic_str = f"{aic:.2f}" if isinstance(aic, (int, float)) else str(aic)
                        r2_str = f"{r2:.4f}" if isinstance(r2, (int, float)) else str(r2)

                        model_text += f"  {marker} {model:<18} {status:<15} {bic_str:<10} {aic_str:<10} {r2_str:<8}\n"
            else:
                model_text += "\n  Model fitting failed\n"
                model_text += f"  Error: {curve.get('error', 'Unknown error')}\n"

            model_text += "\n" + "=" * 60 + "\n\n"

        self.model_comparison.value = model_text

        # Generate plots
        self.current_plots = {}

        from ..analysis.visualization import ELISAVisualizer
        visualizer = ELISAVisualizer(concentration_unit=unit, od_wavelength=od_wavelength)

        # Get colormap from config
        plot_colormap = self.app.analysis_config.get('plots_colormap', 'viridis')
        std_curve_log_x = self.app.analysis_config.get('std_curve_log_x', True)
        std_curve_log_y = self.app.analysis_config.get('std_curve_log_y', False)

        # Generate plots for each plate
        for plate_name, curve_result in results.get('curve_fits', {}).items():
            if curve_result.get('success'):
                # Get calibrant data for this plate
                plate_data = results['data_df'][results['data_df']['plate_name'] == plate_name]
                calibrants = plate_data[plate_data['well_type'] == 'CALIBRANT']

                self.app.log(f'Checking calibrants for {plate_name}: {len(calibrants)} calibrants found')

                if not calibrants.empty and 'concentration' in calibrants.columns:
                    concentrations = calibrants['concentration'].dropna().values
                    od_values = calibrants.loc[calibrants['concentration'].notna(), 'od_value'].values

                    self.app.log(f'Concentrations: {len(concentrations)}, OD values: {len(od_values)}')

                    if len(concentrations) > 0 and len(od_values) > 0:
                        try:
                            # Standard curve plot
                            std_curve_path = visualizer.create_standard_curve_plot(
                                concentrations,
                                od_values,
                                curve_result,
                                plate_name,
                                colormap=plot_colormap,
                                log_x=std_curve_log_x,
                                log_y=std_curve_log_y,
                            )
                            self.app.log(f'Created standard curve plot: {std_curve_path}')



                            # Store paths
                            if plate_name not in self.current_plots:
                                self.current_plots[plate_name] = {}

                            self.current_plots[plate_name]['standard_curve'] = std_curve_path


                        except Exception as e:
                            self.app.log(f'Error creating plots for {plate_name}: {str(e)}')
                    else:
                        self.app.log(f'Skipping plots for {plate_name}: insufficient data')
                else:
                    self.app.log(f'Skipping plots for {plate_name}: no calibrants or concentration column missing')

        # Generate combined standard curves plot 
        all_curve_data = []
        for plate_name, curve_result in results.get('curve_fits', {}).items():
            if curve_result.get('success'):
                plate_data = results['data_df'][results['data_df']['plate_name'] == plate_name]
                calibrants = plate_data[plate_data['well_type'] == 'CALIBRANT']
                if not calibrants.empty and 'concentration' in calibrants.columns:
                    conc = calibrants['concentration'].dropna().values
                    od = calibrants.loc[calibrants['concentration'].notna(), 'od_value'].values
                    if len(conc) > 0 and len(od) > 0:
                        all_curve_data.append({
                            'plate_name': plate_name, 'concentrations': conc,
                            'od_values': od, 'curve_result': curve_result
                        })
        if len(all_curve_data) > 1:
            try:
                combined_path = visualizer.create_all_standard_curves_plot(
                    all_curve_data, colormap=plot_colormap,
                    log_x=std_curve_log_x, log_y=std_curve_log_y)
                self.current_plots['std_curve_all'] = combined_path
                self.app.log('Created combined standard curves plot')
            except Exception as e:
                self.app.log(f'Error creating combined standard curves: {str(e)}')

        # Per-group combined standard curve plots
        if per_group_plots and hasattr(self.app, 'plate_groups') and self.app.plate_groups:
            for group_name, group_plates in self.app.plate_groups.items():
                group_curve_data = [e for e in all_curve_data if e['plate_name'] in group_plates]
                if len(group_curve_data) > 1:
                    try:
                        grp_path = visualizer.create_all_standard_curves_plot(
                            group_curve_data,
                            colormap=plot_colormap,
                            log_x=std_curve_log_x,
                            log_y=std_curve_log_y,
                            title=f'Standard Curves - Group: {group_name}',
                        )
                        self.current_plots[f'std_curve_group_{group_name}'] = grp_path
                        self.app.log(f'Created standard curves plot for group "{group_name}"')
                    except Exception as e:
                        self.app.log(f'Error creating group curves for "{group_name}": {str(e)}')

        # Generate PCA analysis — runs when ≥3 plates are available
        from ..analysis.pca import ELISAPCAAnalyzer
        pca_analyzer = ELISAPCAAnalyzer(n_components=2)
        plate_groups_for_pca = (
            self.app.plate_groups
            if hasattr(self.app, 'plate_groups') and self.app.plate_groups
            else {}
        )
        pca_result = pca_analyzer.analyze_plates(results, plate_groups_for_pca)

        if pca_result is not None:
            # Compute 95% confidence ellipses (skipped silently for groups with <3 plates)
            ellipse_data = pca_analyzer.compute_confidence_ellipses(
                pca_result['scores'],
                pca_result['labels'],
                confidence=0.95
            )

            by_group = len(plate_groups_for_pca) >= 2
            show_plate_names = self.app.analysis_config.get('pca_show_plate_names', False)
            pca_path = visualizer.create_pca_plot(
                pca_result,
                title="Plate QC Metrics - PCA by Group" if by_group else "Plate QC Metrics - PCA by Plate",
                color_labels=pca_result['labels'],
                color_name="Plate Group" if by_group else "Plate",
                colormap=plot_colormap,
                ellipse_data=ellipse_data,
                point_labels=pca_result['plate_names'] if show_plate_names else None
            )
            self.current_plots['pca'] = pca_path
            self.app.log(
                f'Created PCA ({"by group" if by_group else "by plate"}, '
                f'{len(pca_result["plate_names"])} plates)'
            )

        # Generate heatmaps for all plates using config from analysis_view
        heatmap_color_var = self.app.analysis_config.get('heatmap_color_var', 'od_value')
        heatmap_size_var = self.app.analysis_config.get('heatmap_size_var', 'None')
        heatmap_label_var = self.app.analysis_config.get('heatmap_label_var', 'None')
        plots_colormap = self.app.analysis_config.get('plots_colormap', 'viridis')

        all_plate_names = list(results['data_df']['plate_name'].unique())
        for plate_name in all_plate_names:
            try:
                heatmap_path = visualizer.create_plate_heatmap(
                    data_df=results['data_df'],
                    value_column=heatmap_color_var,
                    plate_name=plate_name,
                    colormap=plots_colormap,
                    show_values=True,
                    size_column=heatmap_size_var if heatmap_size_var != 'None' else None,
                    label_column=heatmap_label_var if heatmap_label_var != 'None' else None
                )
                if plate_name not in self.current_plots:
                    self.current_plots[plate_name] = {}
                self.current_plots[plate_name]['heatmap'] = heatmap_path
                self.app.log(f'Created heatmap for {plate_name}')
            except Exception as e:
                self.app.log(f'Error creating heatmap for {plate_name}: {str(e)}')

        # trend plot
        trend_date = self.app.analysis_config.get('trend_date_var')
        trend_value = self.app.analysis_config.get('trend_value_var')
        trend_group = self.app.analysis_config.get('trend_grouping_var')

        if trend_date and trend_date != 'None' and trend_value and trend_value != 'None':
            try:
                from ..analysis.clinical import build_trend_jobs, prepare_trend_df

                plot_df = results['data_df'].copy()
                if 'well_type' in plot_df.columns:
                    plot_df = plot_df[plot_df['well_type'] == 'SAMPLE']

                trend_jobs, y_label = build_trend_jobs(
                    plot_df, trend_date, trend_value, trend_group)

                for job in trend_jobs:
                    job_df = prepare_trend_df(job, trend_value)
                    if job_df is None:
                        continue

                    trend_paths = visualizer.create_trend_plot(
                        job_df, trend_value, job['group'],
                        plate_groups=(self.app.plate_groups if hasattr(self.app, 'plate_groups') else None) if per_group_plots else None,
                        title=job['title'],
                        colormap=plots_colormap,
                        y_label=y_label,
                        x_label=job['x_label']
                    )

                    for key, path in trend_paths.items():
                        if job['prefix']:
                            key = key.replace('trend_', f'trend_tnm_{job["prefix"]}_', 1)
                        self.current_plots[key] = path

                self.app.log(f'Created Pattern plot(s) for {trend_value}')
            except Exception as e:
                self.app.log(f'Error creating Pattern plot: {str(e)}')

        # Clinical Analysis (multi-column: TNM, UICC, staging, age, etc.)
        clinical_columns = self.app.analysis_config.get('tnm_columns', [])
        clinical_biomarker = self.app.analysis_config.get('tnm_biomarker')

        if clinical_columns and clinical_biomarker and clinical_biomarker != 'None':
            try:
                from ..analysis.clinical import process_clinical_columns

                (clinical_df, all_analysis_cols, all_display_mapping,
                 all_column_groups, biomarker_display, violin_info
                 ) = process_clinical_columns(
                    results['data_df'], clinical_columns, clinical_biomarker)

                clinical_plots_created = 0
                plate_groups = self.app.plate_groups if hasattr(self.app, 'plate_groups') else None

                # Violin plots per variable
                for vi in violin_info:
                    col = vi['col']
                    col_display = vi['col_display']
                    col_safe = vi['col_safe']

                    # Unified violin (all plates) — index 0
                    violin_path = visualizer.create_violin_plot(
                        clinical_df, col, clinical_biomarker,
                        title=f'{biomarker_display} by {col_display} \u2014 All Data',
                        colormap=plots_colormap,
                        plate_groups=plate_groups
                    )
                    if violin_path:
                        self.current_plots[f'clinical_violin_{col_safe}_0_all'] = violin_path
                        clinical_plots_created += 1

                    # Per-group violins — index 1, 2, ...
                    if per_group_plots and plate_groups and len(plate_groups) > 1 and 'plate_name' in clinical_df.columns:
                        for g_idx, (group_name, group_plates) in enumerate(plate_groups.items(), 1):
                            group_df = clinical_df[clinical_df['plate_name'].isin(group_plates)]
                            if col in group_df.columns and group_df[col].notna().sum() >= 5:
                                group_violin_path = visualizer.create_violin_plot(
                                    group_df, col, clinical_biomarker,
                                    title=f'{biomarker_display} by {col_display} \u2014 {group_name}',
                                    colormap=plots_colormap,
                                    plate_groups=None
                                )
                                if group_violin_path:
                                    safe_group = group_name.replace(' ', '_')
                                    self.current_plots[f'clinical_violin_{col_safe}_{g_idx}_{safe_group}'] = group_violin_path
                                    clinical_plots_created += 1

                # Update results df with all processed columns
                results['data_df'] = clinical_df
                self.app.analysis_results['data_df'] = clinical_df

                # Correlation heatmaps: unified + per-group
                if all_analysis_cols:
                    # Unified correlation heatmap — index 0
                    corr_path = visualizer.create_correlation_heatmap(
                        clinical_df, all_analysis_cols, clinical_biomarker,
                        title='Clinical Correlation \u2014 All Data',
                        colormap=plots_colormap,
                        display_mapping=all_display_mapping,
                        column_groups=all_column_groups
                    )
                    if corr_path:
                        self.current_plots['correlation_heatmap_0_all'] = corr_path
                        clinical_plots_created += 1

                    # Per-group correlation heatmaps — index 1, 2, ...
                    if per_group_plots and plate_groups and len(plate_groups) > 1 and 'plate_name' in clinical_df.columns:
                        for g_idx, (group_name, group_plates) in enumerate(plate_groups.items(), 1):
                            group_df = clinical_df[clinical_df['plate_name'].isin(group_plates)]
                            n_group = group_df[clinical_biomarker].notna().sum()
                            if n_group >= 2:
                                group_corr_path = visualizer.create_correlation_heatmap(
                                    group_df, all_analysis_cols, clinical_biomarker,
                                    title=f'Clinical Correlation \u2014 {group_name}',
                                    colormap=plots_colormap,
                                    display_mapping=all_display_mapping,
                                    column_groups=all_column_groups
                                )
                                if group_corr_path:
                                    safe_group = group_name.replace(' ', '_')
                                    self.current_plots[f'correlation_heatmap_{g_idx}_{safe_group}'] = group_corr_path
                                    clinical_plots_created += 1

                self.app.log(f'Created {clinical_plots_created} clinical plots ({len(clinical_columns)} variable(s))')

            except Exception as e:
                self.app.log(f'Error creating clinical plots: {str(e)}')

        # ROC Analysis — generate if configured in Analysis tab
        roc_score_col = self.app.analysis_config.get('roc_score_col', 'None')
        roc_label_col = self.app.analysis_config.get('roc_label_col', 'None')
        roc_pos_label = self.app.analysis_config.get('roc_positive_label', '')
        roc_neg_label = self.app.analysis_config.get('roc_negative_label', '')

        if (roc_score_col != 'None' and roc_label_col != 'None'
                and roc_pos_label and roc_neg_label
                and roc_pos_label != roc_neg_label):
            try:
                from ..analysis.statistics import roc_analysis
                plate_groups_roc = self.app.plate_groups if hasattr(self.app, 'plate_groups') else None

                # All data — always generated
                plots_colormap = self.app.analysis_config.get('plots_colormap', 'viridis')
                roc_result = roc_analysis(
                    results['data_df'], roc_score_col, roc_label_col,
                    roc_pos_label, roc_neg_label
                )
                if roc_result['success']:
                    roc_path = visualizer.create_roc_plot(
                        roc_result, colormap=plots_colormap, group_label='All Data'
                    )
                    self.current_plots['roc_0_all'] = roc_path
                    self.app.log(
                        f'ROC (all): AUC={roc_result["auc"]:.3f}, '
                        f'sens={roc_result["sensitivity"]:.3f}, '
                        f'spec={roc_result["specificity"]:.3f}'
                    )
                else:
                    self.app.log(f'ROC skipped: {roc_result["error"]}')

                # Per-group ROC — only when per_group_plots is on and groups exist
                self.app.log(
                    f'ROC per-group check: per_group={per_group_plots}, '
                    f'n_groups={len(plate_groups_roc) if plate_groups_roc else 0}, '
                    f'plate_name_col={"plate_name" in results["data_df"].columns}'
                )
                if (per_group_plots and plate_groups_roc and len(plate_groups_roc) >= 1
                        and 'plate_name' in results['data_df'].columns):
                    for g_idx, (group_name, group_plates) in enumerate(plate_groups_roc.items(), 1):
                        group_df = results['data_df'][results['data_df']['plate_name'].isin(group_plates)]
                        group_roc = roc_analysis(
                            group_df, roc_score_col, roc_label_col,
                            roc_pos_label, roc_neg_label
                        )
                        if group_roc['success']:
                            safe_group = group_name.replace(' ', '_')
                            group_roc_path = visualizer.create_roc_plot(
                                group_roc, colormap=plots_colormap, group_label=group_name
                            )
                            self.current_plots[f'roc_{g_idx}_{safe_group}'] = group_roc_path
                            self.app.log(f'ROC ({group_name}): AUC={group_roc["auc"]:.3f}')
                        else:
                            self.app.log(f'ROC group "{group_name}" skipped: {group_roc["error"]}')

            except Exception as e:
                self.app.log(f'Error generating ROC plot: {str(e)}')

        # Update plate selector with available plates (exclude special plots)
        plate_names = [k for k in self.current_plots.keys()
                       if k not in ('pca', 'std_curve_all')
                       and not k.startswith('correlation_heatmap')
                       and not k.startswith('clinical_violin_')
                       and not k.startswith('trend_')
                       and not k.startswith('roc_')]
        self.app.log(f'Generated plots for {len(plate_names)} plate(s)')

    async def on_clear_results(self, widget=None):
        """Clear all results."""
        self.app.loading.start()
        self.results_table.data = []
        self.qc_summary.value = ""
        self.model_comparison.value = ""
        self.current_plots = {}
        if hasattr(self, 'plot_imageview'):
            self.plot_imageview.image = None
        self.app.analysis_results = None
        self.app.log('Analysis results cleared')
        self.app.loading.stop()

    async def on_show_standard_curve(self, widget):
        gallery = []

        # per-plate curves
        for plate_name in sorted(self.current_plots.keys()):
            plots = self.current_plots.get(plate_name)
            if isinstance(plots, dict) and plots.get('standard_curve'):
                gallery.append((
                    f"std_{plate_name}",
                    plots['standard_curve'],
                    f"Standard Curve • {plate_name}"
                ))

        # combined all plates
        if self.current_plots.get('std_curve_all'):
            gallery.append((
                "std_curve_all",
                self.current_plots['std_curve_all'],
                "Standard Curve \u2022 All Plates"
            ))

        # per-group combined plots
        if hasattr(self.app, 'plate_groups') and self.app.plate_groups:
            for group_name in self.app.plate_groups:
                key = f'std_curve_group_{group_name}'
                if self.current_plots.get(key):
                    gallery.append((
                        key,
                        self.current_plots[key],
                        f"Standard Curve \u2022 Group: {group_name}",
                    ))

        if not gallery:
            await self.app.main_window.dialog(
                toga.InfoDialog('No Plots', 'Run analysis first to generate plots.')
            )
            return

        self._set_gallery(gallery, start_index=0)

        
    async def on_show_heatmap(self, widget):
        gallery = []
        for plate_name in sorted(self.current_plots.keys()):
            plots = self.current_plots.get(plate_name)
            if isinstance(plots, dict) and plots.get('heatmap'):
                gallery.append((
                    f"hm_{plate_name}",
                    plots['heatmap'],
                    f"Heatmap • {plate_name}"
                ))

        if not gallery:
            await self.app.main_window.dialog(
                toga.InfoDialog('No Plots', 'Run analysis first to generate plots.')
            )
            return

        self._set_gallery(gallery, start_index=0)


   
    async def on_show_pca(self, widget):
        if not self.current_plots or not self.current_plots.get('pca'):
            await self.app.main_window.dialog(
                toga.InfoDialog('No PCA', 'PCA analysis requires at least 2 plate groups to be defined.')
            )
            return

        gallery = [("pca", self.current_plots['pca'], "PCA • Plate Groups")]
        self._set_gallery(gallery, start_index=0)


    async def on_show_trend(self, widget):
        keys = sorted([k for k in self.current_plots.keys() if k.startswith('trend_')])
        if not keys:
            await self.app.main_window.dialog(
                toga.InfoDialog(
                    'No Pattern Plot',
                    'Please configure pattern settings in Analysis tab and run analysis.'
                )
            )
            return

        gallery = [(k, self.current_plots[k], f"Pattern • {k.replace('trend_', '').replace('_', ' ')}") for k in keys]
        self._set_gallery(gallery, start_index=0)


    async def on_show_correlation_heatmap(self, widget):
        keys = sorted([k for k in self.current_plots.keys() if k.startswith('correlation_heatmap')])
        if not keys:
            await self.app.main_window.dialog(
                toga.InfoDialog(
                    'No Correlation Plot',
                    'Select grouping column and biomarker in Analysis tab, then run analysis.'
                )
            )
            return

        gallery = [(k, self.current_plots[k], f"Correlation • {k.replace('correlation_heatmap_', '').replace('_', ' ')}") for k in keys]
        self._set_gallery(gallery, start_index=0)


    async def on_show_violin(self, widget):
        keys = sorted([k for k in self.current_plots.keys() if k.startswith('clinical_violin_')])
        if not keys:
            await self.app.main_window.dialog(
                toga.InfoDialog(
                    'No Violin Plots',
                    'Select grouping column and biomarker in Analysis tab, then run analysis.'
                )
            )
            return

        gallery = [(k, self.current_plots[k], f"Violin • {k.replace('clinical_violin_', '').replace('_', ' ')}") for k in keys]
        self._set_gallery(gallery, start_index=0)


    async def on_show_roc(self, widget):
        keys = sorted([k for k in self.current_plots.keys() if k.startswith('roc_')])
        if not keys:
            await self.app.main_window.dialog(
                toga.InfoDialog(
                    'No ROC Plot',
                    'Configure ROC settings (score column, outcome column, classes) '
                    'in the Analysis tab and run analysis.'
                )
            )
            return

        gallery = []
        for k in keys:
            # roc_0_all  → label "All Data"
            # roc_1_Group_A → label "Group A"
            suffix = k[len('roc_'):]                              # "0_all" or "1_Group_A"
            label = suffix.split('_', 1)[1] if '_' in suffix else suffix
            label = label.replace('_', ' ')
            if label.lower() == 'all':
                label = 'All Data'
            gallery.append((k, self.current_plots[k], f'ROC Analysis \u2022 {label}'))

        self._set_gallery(gallery, start_index=0)


    def _set_gallery(self, gallery, start_index=0):
        """
        gallery: list of tuples (key, path, display_name)
        """
        self.current_gallery = gallery or []
        if not self.current_gallery:
            self.gallery_index = -1
            self.plot_imageview.image = None
            self.plot_nav_label.text = "No plots available"
            # disable arrows
            self.prev_plot_btn.enabled = False
            self.next_plot_btn.enabled = False
            return

        self.gallery_index = max(0, min(start_index, len(self.current_gallery) - 1))
        self._show_current_gallery_item()

    def _show_current_gallery_item(self):
        if not self.current_gallery or self.gallery_index < 0:
            return

        key, path, display_name = self.current_gallery[self.gallery_index]
        self.plot_imageview.image = path
        self.current_plot_type = key

        total = len(self.current_gallery)
        self.plot_nav_label.text = f"{self.gallery_index + 1} / {total} • {display_name}"

        # enable arrows only if multiple images
        enable_arrows = total > 1
        self.prev_plot_btn.enabled = enable_arrows
        self.next_plot_btn.enabled = enable_arrows

    async def on_prev_plot(self, widget):
        if not self.current_gallery or len(self.current_gallery) <= 1:
            return
        self.gallery_index = (self.gallery_index - 1) % len(self.current_gallery)
        self._show_current_gallery_item()

    async def on_next_plot(self, widget):
        if not self.current_gallery or len(self.current_gallery) <= 1:
            return
        self.gallery_index = (self.gallery_index + 1) % len(self.current_gallery)
        self._show_current_gallery_item()

    async def on_export_all_zip(self, widget):
        """Export all results as a ZIP archive."""
        if self.app.analysis_results is None:
            await self.app.main_window.dialog(
                toga.ErrorDialog('No Results', 'Run analysis first before exporting.')
            )
            return

        try:
            file_path = await self.app.main_window.dialog(
                toga.SaveFileDialog(
                    title="Export All Results",
                    suggested_filename="elisa_analysis_results.zip",
                    file_types=['zip']
                )
            )

            if file_path:
                with zipfile.ZipFile(str(file_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
                    csv_content = self.app.analysis_results['data_df'].to_csv(index=False)

                    zipf.writestr('results/analysis_results.csv', csv_content)

                    # Plate summary table (all per-plate metrics)
                    plate_summary = self._build_plate_summary_df(self.app.analysis_results)
                    zipf.writestr('results/plate_summary.csv',
                                  plate_summary.to_csv(index=False, float_format='%.6g'))

                    # Group summary table (only when plate groups are defined)
                    group_summary = self._build_group_summary_df(self.app.analysis_results)
                    if group_summary is not None:
                        zipf.writestr('results/group_summary.csv',
                                      group_summary.to_csv(index=False, float_format='%.6g'))

                    # Full model comparison table (all candidate models × all plates)
                    model_comp_df = self._build_model_comparison_df(self.app.analysis_results)
                    if not model_comp_df.empty:
                        zipf.writestr('results/model_comparison.csv',
                                      model_comp_df.to_csv(index=False, float_format='%.6g'))
                        # Cross-plate summary (one row per model, aggregated metrics)
                        mc_summary_df = self._build_model_comparison_summary_df(model_comp_df)
                        if not mc_summary_df.empty:
                            zipf.writestr('results/model_comparison_summary.csv',
                                          mc_summary_df.to_csv(index=False, float_format='%.6g'))

                    # Add QC report
                    report_content = "ELISA Analysis Report\n"
                    report_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    report_content += "=" * 80 + "\n\n"
                    report_content += "QC SUMMARY\n"
                    report_content += "-" * 80 + "\n"
                    report_content += self.qc_summary.value + "\n\n"
                    report_content += "MODEL COMPARISON\n"
                    report_content += "-" * 80 + "\n"
                    report_content += self.model_comparison.value
                    zipf.writestr('reports/qc_report.txt', report_content)

                    # Add plots
                    for plate_name, plots in self.current_plots.items():
                        if plate_name == 'pca':
                            continue
                        if isinstance(plots, dict) and 'standard_curve' in plots:
                            plot_path = plots['standard_curve']
                            if os.path.exists(plot_path):
                                zipf.write(plot_path, f'plots/standard_curve_{plate_name}.png')

                    # Add combined standard curves plot
                    if 'std_curve_all' in self.current_plots:
                        path = self.current_plots['std_curve_all']
                        if os.path.exists(path):
                            zipf.write(path, 'plots/standard_curves_all.png')

                    # Add PCA plot
                    if 'pca' in self.current_plots:
                        pca_path = self.current_plots['pca']
                        if os.path.exists(pca_path):
                            zipf.write(pca_path, 'plots/pca_analysis.png')
                            
                    for plot_key in sorted(self.current_plots.keys()):
                        if plot_key.startswith('trend_'):
                            trend_path = self.current_plots[plot_key]
                            if os.path.exists(trend_path):
                                zipf.write(trend_path, f'plots/{plot_key}.png')

                    for plot_key in sorted(self.current_plots.keys()):
                        if plot_key.startswith('correlation_heatmap'):
                            corr_path = self.current_plots[plot_key]
                            if os.path.exists(corr_path):
                                zipf.write(corr_path, f'plots/{plot_key}.png')

                    # Add TNM clinical staging plots
                    for plot_key in self.current_plots.keys():
                        if plot_key.startswith('clinical_violin_'):
                            violin_path = self.current_plots[plot_key]
                            if os.path.exists(violin_path):
                                zipf.write(violin_path, f'plots/{plot_key}.png')

                    # Add ROC plots (all data + per group)
                    for plot_key in sorted(self.current_plots.keys()):
                        if plot_key.startswith('roc_'):
                            roc_exp_path = self.current_plots[plot_key]
                            if os.path.exists(roc_exp_path):
                                zipf.write(roc_exp_path, f'plots/{plot_key}.png')

                    # Add all heatmaps
                    for plate_name, plots in self.current_plots.items():
                        if plate_name == 'pca':
                            continue
                        if isinstance(plots, dict) and 'heatmap' in plots:
                            heatmap_path = plots['heatmap']
                            if os.path.exists(heatmap_path):
                                zipf.write(heatmap_path, f'plots/heatmap_{plate_name}.png')

                await self.app.main_window.dialog(
                    toga.InfoDialog('Success', f'All results exported to {file_path.name}')
                )
                self.app.log(f'All results exported to ZIP: {file_path.name}')

        except Exception as e:
            await self.app.main_window.dialog(
                toga.ErrorDialog('Export Error', str(e))
            )

    # Export helper: structured summary tables
    def _build_plate_summary_df(self, results):
        """Build a per-plate summary DataFrame covering all computed metrics."""
        import pandas as pd

        plate_groups = getattr(self.app, 'plate_groups', None) or {}
        plate_to_group = {p: g for g, plates in plate_groups.items() for p in plates}

        data_df     = results.get('data_df', pd.DataFrame())
        curve_fits  = results.get('curve_fits', {})
        qc_summary  = results.get('qc_summary', {})
        lod_loq     = results.get('lod_loq', {})
        plate_factors = results.get('plate_factors', {})

        WTY_MAP = {
            'CALIBRANT':        'calibrant',
            'SAMPLE':           'sample',
            'BLANK':            'blank',
            'POSITIVE_CONTROL': 'pos_ctrl',
            'NEGATIVE_CONTROL': 'neg_ctrl',
        }
        S_QUANT   = 'Quantifiable (above LOQ)'
        S_BORDER  = 'Borderline (LOD to LOQ)'
        S_BELOW   = 'Below detection (LOD)'
        S_INVALID = 'Invalid'

        rows = []
        for plate in sorted(curve_fits.keys()):
            cf = curve_fits[plate]
            ll = lod_loq.get(plate, {})
            qc = qc_summary.get(plate, {})
            pf = plate_factors.get(plate, float('nan'))

            row = {
                'plate_name':     plate,
                'group':          plate_to_group.get(plate, ''),
                'model':          cf.get('model_name', '') if cf.get('success') else 'FAILED',
                'r2':             cf.get('r_squared'),
                'adj_r2':         cf.get('adjusted_r_squared'),
                'rmse':           cf.get('rmse'),
                'aic':            cf.get('aic'),
                'bic':            cf.get('bic'),
                'lod_conc':       ll.get('lod'),
                'loq_conc':       ll.get('loq'),
                'lod_od':         ll.get('lod_od'),
                'loq_od':         ll.get('loq_od'),
                'lod_loq_method': ll.get('lod_loq_method', ''),
                'plate_factor':   pf,
            }

            for wt, suffix in WTY_MAP.items():
                wq = qc.get(wt, {})
                row[f'n_{suffix}']       = wq.get('n_wells')
                row[f'mean_od_{suffix}'] = wq.get('mean_od')
                row[f'cv_pct_{suffix}']  = wq.get('cv_percent')

            if not data_df.empty and 'plate_name' in data_df.columns:
                sdf = data_df[
                    (data_df['plate_name'] == plate) &
                    (data_df['well_type'] == 'SAMPLE')
                ]
                ds = sdf['detection_status'] if 'detection_status' in sdf.columns else pd.Series(dtype=str)
                row['n_quantifiable'] = int((ds == S_QUANT).sum())
                row['n_borderline']   = int((ds == S_BORDER).sum())
                row['n_below_lod']    = int((ds == S_BELOW).sum())
                row['n_invalid']      = int((ds == S_INVALID).sum())
            else:
                row.update({'n_quantifiable': None, 'n_borderline': None,
                            'n_below_lod': None, 'n_invalid': None})

            # Selected model fitted parameters (one column per parameter name)
            params      = cf.get('params')
            param_names = cf.get('param_names')
            if params is not None and param_names is not None:
                for pname, pval in zip(param_names, params):
                    row[f'param_{pname}'] = float(pval)

            rows.append(row)

        return pd.DataFrame(rows)

    def _build_group_summary_df(self, results):
        """Build a per-group concentration summary. Returns None if no groups defined."""
        import pandas as pd

        plate_groups = getattr(self.app, 'plate_groups', None)
        if not plate_groups:
            return None

        data_df = results.get('data_df', pd.DataFrame())
        if data_df.empty or 'plate_name' not in data_df.columns:
            return None

        plate_to_group = {p: g for g, plates in plate_groups.items() for p in plates}

        sdf = data_df[data_df['well_type'] == 'SAMPLE'].copy()
        sdf['_group'] = sdf['plate_name'].map(plate_to_group)

        conc_col = ('concentration_dilution_corrected'
                    if 'concentration_dilution_corrected' in sdf.columns else 'concentration')

        S_QUANT   = 'Quantifiable (above LOQ)'
        S_BORDER  = 'Borderline (LOD to LOQ)'
        S_BELOW   = 'Below detection (LOD)'
        S_INVALID = 'Invalid'

        rows = []
        for gname in plate_groups.keys():
            gdf  = sdf[sdf['_group'] == gname]
            conc = gdf[conc_col].dropna() if conc_col in gdf.columns else pd.Series(dtype=float)
            ds   = gdf['detection_status'] if 'detection_status' in gdf.columns else pd.Series(dtype=str)
            n    = len(conc)
            rows.append({
                'group':          gname,
                'n_plates':       len(plate_groups[gname]),
                'n_samples':      len(gdf),
                'n_quantifiable': int((ds == S_QUANT).sum()),
                'n_borderline':   int((ds == S_BORDER).sum()),
                'n_below_lod':    int((ds == S_BELOW).sum()),
                'n_invalid':      int((ds == S_INVALID).sum()),
                'mean_conc':      conc.mean()             if n else None,
                'median_conc':    conc.median()           if n else None,
                'sd_conc':        conc.std(ddof=1)        if n >= 2 else None,
                'cv_pct_conc':    (conc.std(ddof=1) / conc.mean() * 100
                                   if n >= 2 and conc.mean() != 0 else None),
                'q25_conc':       conc.quantile(0.25)     if n else None,
                'q75_conc':       conc.quantile(0.75)     if n else None,
            })

        return pd.DataFrame(rows)

    def _build_model_comparison_summary_df(self, comp_df):
        """Aggregate per-plate model comparison into a cross-plate summary.

        Columns: Model, n_params, plates_estimable, mean_r2, sd_r2,
                 mean_rmse, mean_aic, mean_bic, selection_frequency
        """
        import pandas as pd

        if comp_df.empty:
            return pd.DataFrame()

        n_total = comp_df['plate_name'].nunique()

        def _count_params(s):
            return s.count('=') if isinstance(s, str) and s != 'N/A' else None

        work = comp_df.copy()
        work['_pc'] = work['Parameters'].apply(_count_params)

        rows = []
        model_order = work.drop_duplicates('Model')['Model'].tolist()
        for model_name in model_order:
            grp  = work[work['Model'] == model_name]
            ok   = grp[grp['Status'] == 'Success']
            n_ok  = len(ok)
            n_sel = int(grp['selected'].sum())

            pc = ok['_pc'].dropna()
            rows.append({
                'Model':               model_name,
                'n_params':            int(pc.iloc[0]) if len(pc) else None,
                'plates_estimable':    f'{n_ok} / {n_total}',
                'mean_r2':             ok['R\u00b2'].mean()      if n_ok else None,
                'sd_r2':               ok['R\u00b2'].std(ddof=1) if n_ok >= 2 else None,
                'mean_rmse':           ok['RMSE'].mean()         if n_ok else None,
                'mean_aic':            ok['AIC'].mean()          if n_ok else None,
                'mean_bic':            ok['BIC'].mean()          if n_ok else None,
                'selection_frequency': f'{n_sel} / {n_total}',
            })

        return pd.DataFrame(rows)

    def _build_model_comparison_df(self, results):
        """Concatenate per-plate model comparison tables into one DataFrame.

        Columns: plate_name, Model, Parameters, R², Adj R², RMSE, AIC, BIC, Status, selected
        """
        import pandas as pd
        curve_fits = results.get('curve_fits', {})
        frames = []
        for plate in sorted(curve_fits.keys()):
            cf  = curve_fits[plate]
            cdf = cf.get('comparison_df')
            if cdf is not None and not cdf.empty:
                chunk = cdf.copy()
                chunk.insert(0, 'plate_name', plate)
                selected_model = cf.get('model_name', '')
                chunk['selected'] = chunk['Model'] == selected_model
                frames.append(chunk)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
