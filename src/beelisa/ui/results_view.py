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
        self.plate_selector = None

        # Plate grouping elements
        self.plate_switches = {}  # {plate_name: toga.Switch}
        self.plates_container = None
        self.groups_list_container = None
        self.group_name_input = None

    def create_layout(self):
        """Create analysis view layout with config (left) and plate grouping (right)."""

        # Main container
        main_container = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=10))


        # Results section (bottom)
        results_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        results = self.create_results_section()
        results_box.add(results)
        results_scroll = toga.ScrollContainer(content=results_box, style=Pack(flex=1))

        main_container.add(results_scroll)

        return main_container


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
        plots_box = toga.Box(style=Pack(direction=COLUMN, flex=1))

        # Plot navigation buttons
        plot_buttons_box = toga.Box(style=Pack(direction=ROW, margin=5))

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

        plot_buttons_box.add(
            self.plot_std_curve_btn,
            self.plot_heatmap_btn,
            self.plot_pca_btn
        )

        plots_box.add(plot_buttons_box)

        # Add plate selector dropdown
        plate_selector_box = toga.Box(style=Pack(direction=ROW, margin=5))
        plate_selector_label = toga.Label('Select Plate:', style=Pack(margin=5, width=100))
        self.plate_selector = toga.Selection(items=[], style=Pack(flex=1, margin=5))
        self.plate_selector.on_change = self.on_plate_selection_changed
        plate_selector_box.add(plate_selector_label, self.plate_selector)
        plots_box.add(plate_selector_box)

        # ImageView for displaying plots
        self.plot_imageview = toga.ImageView(style=Pack(flex=1, margin=5))
        plots_box.add(self.plot_imageview)

        self.results_tabs.content.append('Results Table', results_table_box)
        self.results_tabs.content.append('QC Summary', qc_box)
        self.results_tabs.content.append('Model Comparison', model_comp_box)
        self.results_tabs.content.append('Plots', plots_box)

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

                od_str = f"{od_value:.3f}" if pd.notna(od_value) else 'N/A'
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

            qc_text += "\n" + "=" * 60 + "\n\n"

        self.qc_summary.value = qc_text

        # Update model comparison
        model_text = "Model Comparison & Selection\n" + "=" * 60 + "\n\n"

        for plate, curve in results.get('curve_fits', {}).items():
            model_text += f"Plate: {plate}\n"
            model_text += "-" * 60 + "\n"

            if curve['success']:
                # Show selected model
                model_name = curve.get('model_name', 'Unknown')
                selection_method = curve.get('selection_method')
                model_text += f"\n Selected Model: {model_name}\n"
                model_text += f" Selection Method: {selection_method}\n"

                # Show model parameters
                params = curve.get('params', [])
                param_names = curve.get('param_names', [])
                model_text += "\n  Model Parameters:\n"
                for name, val in zip(param_names, params):
                    model_text += f"    {name}: {val:.4f}\n"

                # Show goodness of fit
                model_text += "\n  Goodness of Fit:\n"
                r2 = curve.get('r_squared')
                adj_r2 = curve.get('adjusted_r_squared')
                rmse = curve.get('rmse')
                aic = curve.get('aic')
                bic = curve.get('bic')

                r2_str = f"{r2:.4f}" if r2 is not None else 'N/A'
                adj_r2_str = f"{adj_r2:.4f}" if adj_r2 is not None else 'N/A'
                rmse_str = f"{rmse:.4f}" if rmse is not None else 'N/A'
                aic_str = f"{aic:.2f}" if aic is not None else 'N/A'
                bic_str = f"{bic:.2f}" if bic is not None else 'N/A'

                model_text += f"    R²: {r2_str}\n"
                model_text += f"    Adjusted R²: {adj_r2_str}\n"
                model_text += f"    RMSE: {rmse_str}\n"
                model_text += f"    AIC: {aic_str}\n"
                model_text += f"    BIC: {bic_str}\n"

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
        visualizer = ELISAVisualizer(concentration_unit=unit)

        # Get colormap from config
        plot_colormap = self.app.analysis_config.get('heatmap_colormap', 'viridis')

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
                                colormap=plot_colormap
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

        # Generate PCA analysis - only if plate groups are defined
        if hasattr(self.app, 'plate_groups') and self.app.plate_groups:
            from ..analysis.pca import ELISAPCAAnalyzer
            pca_analyzer = ELISAPCAAnalyzer(n_components=2)

            # Plate-level PCA using QC metrics (LOD, LOQ, R², RMSE, BIC, CV, curve params)
            pca_result = pca_analyzer.analyze_plates(results, self.app.plate_groups)

            if pca_result is not None:
                # Compute 95% confidence ellipses
                ellipse_data = pca_analyzer.compute_confidence_ellipses(
                    pca_result['scores'],
                    pca_result['labels'],
                    confidence=0.95
                )

                pca_path = visualizer.create_pca_plot(
                    pca_result,
                    title="Plate QC Metrics - PCA by Group",
                    color_labels=pca_result['labels'],
                    color_name="Plate Group",
                    colormap=plot_colormap,
                    ellipse_data=ellipse_data
                )
                self.current_plots['pca'] = pca_path
                self.app.log(f'Created plate-level PCA with {len(self.app.plate_groups)} groups')

        # Generate heatmaps for all plates using config from analysis_view
        heatmap_color_var = self.app.analysis_config.get('heatmap_color_var', 'od_value')
        heatmap_size_var = self.app.analysis_config.get('heatmap_size_var', 'None')
        heatmap_colormap = self.app.analysis_config.get('heatmap_colormap', 'viridis')

        all_plate_names = list(results['data_df']['plate_name'].unique())
        for plate_name in all_plate_names:
            try:
                heatmap_path = visualizer.create_plate_heatmap(
                    data_df=results['data_df'],
                    value_column=heatmap_color_var,
                    plate_name=plate_name,
                    colormap=heatmap_colormap,
                    show_values=True,
                    size_column=heatmap_size_var if heatmap_size_var != 'None' else None
                )
                if plate_name not in self.current_plots:
                    self.current_plots[plate_name] = {}
                self.current_plots[plate_name]['heatmap'] = heatmap_path
                self.app.log(f'Created heatmap for {plate_name}')
            except Exception as e:
                self.app.log(f'Error creating heatmap for {plate_name}: {str(e)}')

        # Update plate selector with available plates
        plate_names = [k for k in self.current_plots.keys() if k != 'pca']
        self.app.log(f'Generated plots for {len(plate_names)} plate(s)')

        if plate_names:
            self.plate_selector.items = plate_names
            self.plate_selector.value = plate_names[0]  # Select first plate by default

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
        """Display standard curve plot."""
        if not self.current_plots:
            await self.app.main_window.dialog(
                toga.InfoDialog('No Plots', 'Run analysis first to generate plots.')
            )
            return

        # Get selected plate
        selected_plate = self.plate_selector.value
        if selected_plate and selected_plate in self.current_plots:
            plots = self.current_plots[selected_plate]
            if 'standard_curve' in plots:
                path = plots['standard_curve']
                self.plot_imageview.image = path
                self.current_plot_type = 'standard_curve'
                self.app.log(f'Displaying standard curve for {selected_plate}')
                return

        await self.app.main_window.dialog(
            toga.InfoDialog('No Plot', 'Standard curve plot not available for selected plate.')
        )
        
    async def on_show_heatmap(self, widget):
        """Display Heatmap plot."""
        if not self.current_plots:
            await self.app.main_window.dialog(
                toga.InfoDialog('No Plots', 'Run analysis first to generate plots.')
            )
            return

        # Get selected plate
        selected_plate = self.plate_selector.value
        if selected_plate and selected_plate in self.current_plots:
            plots = self.current_plots[selected_plate]
            if 'heatmap' in plots:
                path = plots['heatmap']
                self.plot_imageview.image = path
                self.current_plot_type = 'heatmap'
                self.app.log(f'Displaying Heatmap plate for {selected_plate}')
                return

        await self.app.main_window.dialog(
            toga.InfoDialog('No Plot', 'Heatmap plate not available for selected plate.')
        )

   
    async def on_show_pca(self, widget):
        """Display PCA analysis plot."""
        if not self.current_plots:
            await self.app.main_window.dialog(
                toga.InfoDialog('No Plots', 'Run analysis first to generate plots.')
            )
            return

        if 'pca' in self.current_plots:
            path = self.current_plots['pca']
            self.plot_imageview.image = path
            self.current_plot_type = 'pca'
            self.app.log('Displaying PCA analysis by plate groups')
        else:
            await self.app.main_window.dialog(
                toga.InfoDialog('No PCA', 'PCA analysis requires at least 2 plate groups to be defined.')
            )

    async def on_plate_selection_changed(self, widget):
        """Update displayed plot when plate selection changes."""
        if not self.current_plot_type or self.current_plot_type == 'pca':
            # Don't refresh if no plot is shown or if PCA is shown (PCA is not plate-specific)
            return

        selected_plate = self.plate_selector.value
        if not selected_plate or selected_plate not in self.current_plots:
            return

        # Re-display the current plot type for the newly selected plate
        plots = self.current_plots[selected_plate]
        if self.current_plot_type in plots and plots[self.current_plot_type]:
            path = plots[self.current_plot_type]
            self.plot_imageview.image = path
            self.app.log(f'Switched to {self.current_plot_type} plot for {selected_plate}')

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
                    # Add results CSV
                    csv_content = self.app.analysis_results['data_df'].to_csv(index=False)
                    zipf.writestr('results/analysis_results.csv', csv_content)

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

                    # Add PCA plot
                    if 'pca' in self.current_plots:
                        pca_path = self.current_plots['pca']
                        if os.path.exists(pca_path):
                            zipf.write(pca_path, 'plots/pca_analysis.png')

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
