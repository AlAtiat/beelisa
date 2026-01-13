import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import pandas as pd


class AnalysisView:
    """ELISA analysis interface with configuration and results display."""

    def __init__(self, app):
        self.app = app
        self.calibrant_rows = []
        self.results_table = None
        self.qc_summary = None
        self.curve_info = None
        self.current_plots = {}  # Store generated plot paths
        self.current_plot_type = None  # Track which plot type is currently displayed

    def create_layout(self):
        """Create analysis view layout."""
        
        upper_container = toga.Box(style=Pack(direction=COLUMN, flex=1))
        under_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        under_container = toga.ScrollContainer(content=under_box, flex=1)
        container = toga.SplitContainer(content=[upper_container, under_container], style=Pack(direction=COLUMN, flex=1, margin=10))

        # Configuration section
        config = self.create_configuration_section()
        upper_container.add(config)

        # Action buttons
        buttons = self.create_action_buttons()
        upper_container.add(buttons)

        # Results section
        results = self.create_results_section()
        under_box.add(results)

        return container

    def create_configuration_section(self):
        """Create calibrant input, dilution factor, and LOD/LOQ mode."""
        config_box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Header
        header = toga.Label(
            'ANALYSIS CONFIGURATION',
            style=Pack(margin=5, font_weight='bold', font_size=14)
        )
        config_box.add(header)
        config_box.add(toga.Divider())

        # Calibrant concentrations
        calib_label = toga.Label(
            'Calibrant Concentrations:',
            style=Pack(margin=5, font_weight='bold')
        )
        config_box.add(calib_label)

        # Calibrant input container
        self.calibrant_container = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Start with 5 rows 
        calibrants_range = range(5)
        for order in calibrants_range:
            row = self.create_calibrant_row(order)
            self.calibrant_container.add(row)

        config_box.add(self.calibrant_container)

        # Dilution factor
        dilution_box = toga.Box(style=Pack(direction=ROW, margin=5))
        dilution_label = toga.Label(
            'Dilution Factor:',
            style=Pack(margin=5, width=150)
        )
        self.dilution_input = toga.TextInput(
            value='1.0',
            style=Pack(flex=1, margin=5)
        )
        dilution_box.add(dilution_label, self.dilution_input)
        config_box.add(dilution_box)

        # LOD/LOQ mode
        lod_box = toga.Box(style=Pack(direction=ROW, margin=5))
        lod_label = toga.Label(
            'LOD/LOQ Calculation:',
            style=Pack(margin=5, width=150)
        )
        self.lod_mode_select = toga.Selection(
            items=['Per Plate', 'Global'],
            style=Pack(flex=1, margin=5)
        )
        lod_box.add(lod_label, self.lod_mode_select)
        config_box.add(lod_box)

        # Concentration unit
        unit_box = toga.Box(style=Pack(direction=ROW, margin=5))
        unit_label = toga.Label(
            'Concentration Unit:',
            style=Pack(margin=5, width=150)
        )
        self.unit_input = toga.TextInput(
            value='U/mL',
            placeholder='e.g., ng/mL, µg/mL, pM',
            style=Pack(flex=1, margin=5)
        )
        unit_box.add(unit_label, self.unit_input)
        config_box.add(unit_box)

        # PCA grouping column
        pca_box = toga.Box(style=Pack(direction=ROW, margin=5))
        pca_label = toga.Label(
            'PCA Grouping Column:',
            style=Pack(margin=5, width=150)
        )
        self.pca_selection = toga.Selection(
            items=["(None)"],
            style=Pack(flex=1, margin=5)
        )
        pca_box.add(pca_label, self.pca_selection)
        config_box.add(pca_box)

        return config_box

    def update_pca_selection(self):
        if self.pca_selection is None:
            return
        if getattr(self.app, "connected_df", None) is None:
            return
        
        df_headers = list(self.app.connected_df.columns.values)
        self.pca_selection.items = df_headers
            
        
    def rebuild_calibrant_rows (self):
        """ Rebuild count of calibrants"""
        cal_count = int(self.app.calibrant_count or 0)
        self.calibrant_container.clear()
        
        for order in range(cal_count):
            row = self.create_calibrant_row(order)
            self.calibrant_container.add(row)
        
    def create_calibrant_row(self, order):
        """Create a single calibrant input row."""
        row = toga.Box(style=Pack(direction=ROW, margin=2))

        order_label = toga.Label(
            f'CAL {order}:',
            style=Pack(margin=5, width=80)
        )
        conc_input = toga.TextInput(
            placeholder='Concentration',
            style=Pack(flex=1, margin=5)
        )

        row.add(order_label, conc_input)
        self.calibrant_rows.append({'order': order, 'input': conc_input, 'row_widget': row})

        return row


    def create_action_buttons(self):
        """Create Run Analysis, Clear, Export buttons."""
        btn_box = toga.Box(style=Pack(direction=ROW, margin=10))

        run_btn = toga.Button(
            'Run Analysis',
            on_press=self.on_run_analysis,
            style=Pack(margin=5, flex=1)
        )

        clear_btn = toga.Button(
            'Clear Results',
            on_press=self.on_clear_results,
            style=Pack(margin=5, flex=1)
        )

        export_btn = toga.Button(
            'Export to CSV',
            on_press=self.on_export_results,
            style=Pack(margin=5, flex=1)
        )

        btn_box.add(run_btn, clear_btn, export_btn)
        return btn_box

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
            headings=['Sample ID', 'Plate', 'Well', 'OD', 'Concentration', 'Status'],
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
   
        self.plot_pca_btn = toga.Button(
            'PCA Analysis',
            on_press=self.on_show_pca,
            style=Pack(margin=2, flex=1)
        )

        plot_buttons_box.add(
            self.plot_std_curve_btn,
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

        results_box.add(self.results_tabs)

        return results_box

    async def on_run_analysis(self, widget):
        """Trigger analysis workflow."""

        # Collect calibrant concentrations
        calibrant_config = {}
        for row in self.calibrant_rows:
            value = row['input'].value
            if value and value.strip():
                try:
                    calibrant_config[row['order']] = float(value)
                except ValueError:
                    await self.app.main_window.dialog(
                        toga.ErrorDialog(
                            'Invalid Input',
                            f"Invalid concentration for Order {row['order']}: '{value}'"
                        )
                    )

                    return

        # Collect dilution factor
        try:
            dilution_factor = float(self.dilution_input.value)
            if dilution_factor <= 0:
                raise ValueError("Dilution factor must be positive")
        except ValueError as e:
            await self.app.main_window.dialog(
                toga.ErrorDialog('Invalid Input', f'Dilution factor error: {str(e)}')
            )
            self.app.log('Invalid Input: Check Calibrant Concentrations')


            return

        # Get LOD/LOQ mode
        lod_mode = 'per_plate' if self.lod_mode_select.value == 'Per Plate' else 'global'

        # Get concentration unit
        concentration_unit = self.unit_input.value.strip() or 'U/mL'

        # Get PCA grouping column
        pca_grouping_column = self.pca_selection.value.strip()

        # Check if data is loaded
        if self.app.connected_df is None or self.app.connected_df.empty:
            await self.app.main_window.dialog(
                toga.ErrorDialog('No Data', 'Please load and merge plate data first.')
            )
            self.app.log('No Data: Please load and merge plate data first.')

            return

        # Update app config
        self.app.analysis_config = {
            'calibrant_concentrations': calibrant_config,
            'dilution_factor': dilution_factor,
            'lod_loq_mode': lod_mode,
            'concentration_unit': concentration_unit,
            'pca_grouping_column': pca_grouping_column
        }

        # Run analysis
 
 
        self.app.engine.calibrant_concentrations = calibrant_config
        self.app.engine.dilution_factor = dilution_factor
        self.app.engine.lod_loq_mode = lod_mode

        try:
            self.app.log('Starting ELISA analysis...')
            results = self.app.engine.run_analysis(self.app.connected_df)

            if not results['success']:
                error_msg = '\n'.join(results.get('errors', ['Unknown error']))
                await self.app.main_window.dialog(
                    toga.ErrorDialog('Analysis Error', error_msg)
                )
                self.app.log('Analysis Error')

                return

            # Store results
            self.app.analysis_results = results
            self.app.log(f'Analysis completed for {len(results["curve_fits"])} plate(s)')

            # Update display
            self.update_results_display(results)

            await self.app.main_window.dialog(
                toga.InfoDialog('Success', 'Analysis completed successfully!')
            )
            self.app.log('Success: Analysis completed successfully!')

        except Exception as e:
            self.app.log(f'Analysis error: {str(e)}')
            await self.app.main_window.dialog(
                toga.ErrorDialog('Analysis Error', str(e))
            )

    def update_results_display(self, results):
        """Update results table, QC summary, and model comparison."""
        # Get concentration unit from config
        unit = self.app.analysis_config.get('concentration_unit', 'U/mL')

        # Update results table
        data_df = results['data_df']
        table_data = []

        for _, row in data_df.iterrows():
            if row['well_type'] == 'SAMPLE':
                sample_id = str(row.get('sample_id', 'N/A'))
                plate_name = str(row.get('plate_name', 'N/A'))
                well_id = str(row.get('well_id', 'N/A'))
                od_value = row.get('od_value')
                concentration = row.get('concentration_dilution_corrected')
                status = str(row.get('detection_status', 'N/A'))

                od_str = f"{od_value:.3f}" if pd.notna(od_value) else 'N/A'
                conc_str = f"{concentration:.2f} {unit}" if pd.notna(concentration) and concentration is not None else 'N/A'

                table_data.append((
                    sample_id,
                    plate_name,
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
                    qc_text += f" WARNING: High CV% detected!\n"

            # Add LOD/LOQ info
            lod_loq = results.get('lod_loq', {}).get(plate, {})
            lod = lod_loq.get('lod')
            loq = lod_loq.get('loq')

            qc_text += f"\n  Detection Limits:\n"
            if lod is not None:
                qc_text += f"    LOD: {lod:.2f} {unit}\n"
            else:
                qc_text += f"    LOD: Not available\n"

            if loq is not None:
                qc_text += f"    LOQ: {loq:.2f} {unit}\n"
            else:
                qc_text += f"    LOQ: Not available\n"

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
                model_text += f"\n  ✓ Selected Model: {model_name}\n"
                model_text += f"  Selection Method: BIC (Bayesian Information Criterion)\n"

                # Show model parameters
                params = curve.get('params', [])
                param_names = curve.get('param_names', [])
                model_text += f"\n  Model Parameters:\n"
                for name, val in zip(param_names, params):
                    model_text += f"    {name}: {val:.4f}\n"

                # Show goodness of fit
                model_text += f"\n  Goodness of Fit:\n"
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
                model_text += f"    BIC: {bic_str} ★\n"

                # Show comparison table
                comparison_df = curve.get('comparison_df')
                if comparison_df is not None:
                    model_text += f"\n  All Models Comparison:\n"
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
                model_text += f"\n  Model fitting failed\n"
                model_text += f"  Error: {curve.get('error', 'Unknown error')}\n"

            model_text += "\n" + "=" * 60 + "\n\n"

        self.model_comparison.value = model_text

        # Generate plots
        self.current_plots = {}

        from ..analysis.visualization import ELISAVisualizer
        visualizer = ELISAVisualizer(concentration_unit=unit)

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
                                plate_name
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

        # # Generate PCA analysis
        # from ..analysis.pca import ELISAPCAAnalyzer
        # pca_analyzer = ELISAPCAAnalyzer(n_components=2)

        # # Use metadata-based PCA if column specified, otherwise use plate-based
        # pca_column = self.app.analysis_config.get('pca_grouping_column')
        # if pca_column and pca_column in results['data_df'].columns:
        #     # Metadata-based PCA
        #     pca_result = pca_analyzer.analyze_by_metadata(
        #         results['data_df'],
        #         grouping_column=pca_column
        #     )
        #     if pca_result is not None:
        #         pca_path = visualizer.create_pca_plot(
        #             pca_result,
        #             title=f"PCA Analysis - Grouped by {pca_column}"
        #         )
        #         self.current_plots['pca'] = pca_path
        # else:
        #     # Multi-plate batch effect analysis (original)
        #     pca_result = pca_analyzer.analyze_multi_plate_variation(results['data_df'])
        #     if pca_result is not None:
        #         pca_path = visualizer.create_pca_plot(
        #             pca_result,
        #             title="Multi-Plate Batch Effect Analysis"
        #         )
        #         self.current_plots['pca'] = pca_path

        # Update plate selector with available plates
        plate_names = [k for k in self.current_plots.keys() if k != 'pca']
        self.app.log(f'Generated plots for {len(plate_names)} plate(s)')

        if plate_names:
            self.plate_selector.items = plate_names
            self.plate_selector.value = plate_names[0]  # Select first plate by default

    async def on_clear_results(self, widget):
        """Clear all results."""
        self.results_table.data = []
        self.qc_summary.value = ""
        self.model_comparison.value = ""
        self.current_plots = {}
        if hasattr(self, 'plot_imageview'):
            self.plot_imageview.image = None
        self.app.analysis_results = None
        self.app.log('Analysis results cleared')

    async def on_export_results(self, widget):
        """Export results to CSV."""
        if self.app.analysis_results is None:
            await self.app.main_window.dialog(
                toga.ErrorDialog('No Results', 'Run analysis first before exporting.')
            )
            return

        try:
            file_path = await self.app.main_window.dialog(
                toga.SaveFileDialog(
                    title="Export Analysis Results",
                    suggested_filename="elisa_analysis_results.csv",
                    file_types=['csv']
                )
            )

            if file_path:
                # Export full results DataFrame
                self.app.analysis_results['data_df'].to_csv(
                    file_path,
                    index=False,
                    encoding='utf-8-sig'
                )

                await self.app.main_window.dialog(
                    toga.InfoDialog('Success', f'Results exported to {file_path.name}')
                )
                self.app.log(f'Analysis results exported to {file_path.name}')

        except Exception as e:
            await self.app.main_window.dialog(
                toga.ErrorDialog('Export Error', str(e))
            )

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
            self.app.log('Displaying PCA batch effect analysis')
        else:
            await self.app.main_window.dialog(
                toga.InfoDialog('No PCA', 'PCA analysis requires multiple plates.')
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
