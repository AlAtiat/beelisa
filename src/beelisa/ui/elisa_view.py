import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from pathlib import Path


class Mainboard:
    """ELISA data analysis interface with standard curve and concentration calculations."""

    def __init__(self, app):
        self.app = app
        self.raw_data = None
        self.metadata = None
        self.results = None
        self.plate_image = None
        self.curve_image = None
        self.plate_widget = None

    def create_layout(self):
        """Create ELISA analysis view layout."""
        
        left_container = toga.Box(style=Pack(direction=COLUMN, flex=1))
        right_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        right_container = toga.ScrollContainer(content=right_box, flex=1)
        container = toga.SplitContainer(content=[left_container, right_container], style=Pack(flex=1, margin=10))
        
        # Plate configuration section
        plate_section = self.create_plate_section()
        left_container.add(plate_section)

        # File loading section
        load_section = self.create_load_section()
        right_box.add(load_section)

        # Results display
        # results_section = self.create_results_section()
        # container.add(results_section)

        return container

    def create_plate_section(self):
        """Create plate configuration section."""
        from .widgets.plate_widget import PlateWidget

        section_box = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=1))

        # Section title
        title = toga.Label(
            'Well Plate Configuration',
            style=Pack(margin=5, font_size=14, font_weight='bold')
        )
        section_box.add(title)

        # Create plate widget
        self.plate_widget = PlateWidget(self.app)
        plate_layout = self.plate_widget.create_layout()
        section_box.add(plate_layout)

        return section_box

    def create_load_section(self):
        """Create file loading controls."""
        load_box = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=0))

        # Title
        title = toga.Label(
            'ELISA Data Analysis',
            style=Pack(margin=5, font_size=16, font_weight='bold')
        )
        load_box.add(title)

        # Raw data button
        raw_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        raw_btn = toga.Button(
            'Load Raw ELISA Data',
            on_press=self.load_raw_data,
            style=Pack(margin=5, flex=1)
        )
        self.raw_status = toga.Label(
            'No raw data loaded',
            style=Pack(margin=5, flex=2)
        )
        raw_btn_box.add(raw_btn, self.raw_status)
        load_box.add(raw_btn_box)

        # Metadata button
        meta_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        meta_btn = toga.Button(
            'Load Metadata',
            on_press=self.load_metadata,
            style=Pack(margin=5, flex=2)
        )
        self.meta_status = toga.Label(
            'No metadata loaded',
            style=Pack(margin=5, flex=2)
        )
        meta_btn_box.add(meta_btn, self.meta_status)
        load_box.add(meta_btn_box)

        # # Process button
        # process_btn = toga.Button(
        #     'Process ELISA Data',
        #     on_press=self.process_elisa,
        #     style=Pack(margin=10)
        # )
        # load_box.add(process_btn)

        # Export button
        export_btn = toga.Button(
            'Export Results',
            on_press=self.export_results,
            style=Pack(margin=5, flex=2)
        )
        load_box.add(export_btn)

        return load_box

    def create_results_section(self):
        """Create results display section."""
        results_box = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=10))

        # Images container for plate and curve
        images_box = toga.Box(style=Pack(direction=ROW, flex=1, margin=5))

        # Plate heatmap
        plate_container = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=5))
        plate_label = toga.Label('Plate Layout:', style=Pack(margin=5))
        self.plate_image = toga.ImageView(style=Pack(flex=1, margin=5))
        plate_container.add(plate_label, self.plate_image)

        # Standard curve
        curve_container = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=5))
        curve_label = toga.Label('Standard Curve:', style=Pack(margin=5))
        self.curve_image = toga.ImageView(style=Pack(flex=1, margin=5))
        curve_container.add(curve_label, self.curve_image)

        images_box.add(plate_container, curve_container)
        results_box.add(images_box)

        # Results text
        self.results_text = toga.MultilineTextInput(
            readonly=True,
            style=Pack(height=200, margin=10)
        )
        results_box.add(self.results_text)

        return results_box

    async def load_raw_data(self, widget):
        """Load raw ELISA plate reader data."""
        try:
            file_path = await self.app.main_window.dialog(
                toga.OpenFileDialog(
                    title="Open Raw ELISA Data",
                    file_types=['csv', 'xlsx', 'xls']
                )
            )

            if file_path:
                from ..data.loader import DataLoader

                loader = DataLoader()
                success, message, parsed_data = loader.load_elisa_raw(file_path)

                if success:
                    self.raw_data = parsed_data
                    self.raw_status.text = f"Loaded: {file_path.name}"
                    await self.app.main_window.dialog(toga.InfoDialog('Success', message))
                else:
                    await self.app.main_window.dialog(toga.ErrorDialog('Error', message))

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', str(e)))

    async def load_metadata(self, widget):
        """Load patient metadata file."""
        try:
            file_path = await self.app.main_window.dialog(
                toga.OpenFileDialog(
                    title="Open Metadata File",
                    file_types=['csv', 'xlsx', 'xls']
                )
            )

            if file_path:
                from ..data.loader import DataLoader

                loader = DataLoader()
                success, message = loader.load_metadata(file_path)

                if success:
                    self.metadata = loader.metadata
                    self.meta_status.text = f"Loaded: {len(self.metadata)} records"
                    await self.app.main_window.dialog(toga.InfoDialog('Success', message))
                else:
                    await self.app.main_window.dialog(toga.ErrorDialog('Error', message))

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', str(e)))

    # async def process_elisa(self, widget):
    #     """Process ELISA data with standard curve fitting."""
    #     try:
    #         if self.raw_data is None:
    #             await self.app.main_window.dialog(
    #                 toga.ErrorDialog(
    #                     'Error',
    #                     'Please load raw ELISA data first'
    #                 )
    #             )
    #             return

    #         # Import required modules
    #         from ..data.elisa_parser import ELISAParser
    #         from ..calculations.elisa_calculations import ELISACalculator
    #         from ..visualization.plots import PlotGenerator
    #         import pandas as pd
    #         import numpy as np

    #         # Get well assignments from plate widget
    #         if self.plate_widget:
    #             well_config = self.plate_widget.get_well_assignments()
    #             # well_config contains: 'blanks', 'calibrants', 'samples' (well names like A01, B12)
    #             # and 'blank_indexes', 'calibrant_indexes', 'sample_indexes' (1-based row-major indexes)

    #         # For demonstration, use mock data
    #         # TODO: Use well_config to identify which wells are standards, blanks, and samples
    #         # from the loaded raw_data instead of using fixed indexes
    #         # Here we'll create a simple demo calculation

    #         od_values = np.array(self.raw_data['od_values'])

    #         # Mock: Assume first 8 wells are standards with known concentrations
    #         # User would normally specify this via UI
    #         standard_conc = np.array([1000, 500, 250, 125, 62.5, 31.25, 15.625, 7.8125])  # ng/mL
    #         standard_od = od_values[:8]

    #         # Mock: Assume next wells are samples
    #         sample_od = od_values[8:96]

    #         # Initialize calculator
    #         calc = ELISACalculator()

    #         # Blank subtraction (assume last well is blank)
    #         blank_od = od_values[-1]
    #         std_od_corrected = calc.blank_subtraction(standard_od, blank_od)

    #         # Fit standard curve
    #         curve_fit = calc.fit_standard_curve(standard_conc, std_od_corrected)

    #         # Calculate sample concentrations
    #         sample_od_corrected = calc.blank_subtraction(sample_od, blank_od)
    #         concentrations = calc.od_to_concentration(sample_od_corrected, dilution_factor=1.0)

    #         # Generate visualizations
    #         plot_gen = PlotGenerator()

    #         # Generate standard curve plot
    #         curve_data = calc.generate_standard_curve_points((standard_conc.min(), standard_conc.max()))
    #         curve_path = plot_gen.generate_standard_curve_plot(
    #             standard_conc,
    #             std_od_corrected,
    #             curve_data,
    #             curve_fit['r_squared']
    #         )

    #         # Display curve
    #         self.curve_image.image = toga.Image(Path(curve_path))

    #         # Generate plate heatmap
    #         parser = ELISAParser()
    #         plate_df = parser.create_plate_dataframe(od_values)
    #         plate_path = plot_gen.generate_plate_heatmap(plate_df)

    #         # Display plate
    #         self.plate_image.image = toga.Image(Path(plate_path))

    #         # Display results
    #         results_text = "=== ELISA Analysis Results ===\n\n"
    #         results_text += f"Standard Curve R² = {curve_fit['r_squared']:.4f}\n"
    #         results_text += f"RMSE = {curve_fit['rmse']:.4f}\n\n"

    #         results_text += "4PL Parameters:\n"
    #         for key, value in curve_fit['params_dict'].items():
    #             results_text += f"  {key}: {value:.4f}\n"

    #         results_text += "\nSample Concentrations (first 12):\n"
    #         for i, conc in enumerate(concentrations, start=1):
    #             results_text += f"  Sample {i}: {conc:.2f} ng/mL\n"

    #         self.results_text.value = results_text

    #         # Store results
    #         self.results = {
    #             'concentrations': concentrations,
    #             'r_squared': curve_fit['r_squared'],
    #             'curve_params': curve_fit['params_dict']
    #         }

    #         await self.app.main_window.dialog(
    #             toga.InfoDialog(
    #                 'Success',
    #                 'ELISA data processed successfully!'
    #             )
    #         )

    #     except Exception as e:
    #         await self.app.main_window.dialog(toga.ErrorDialog('Error', f"Processing failed: {str(e)}"))

    async def export_results(self, widget):
        """Export results to CSV file."""
        try:
            if self.results is None:
                await self.app.main_window.dialog(
                    toga.ErrorDialog(
                        'Error',
                        'No results to export. Please process data first.'
                    )
                )
                return

            # Create results DataFrame
            import pandas as pd
            df = pd.DataFrame({
                'sample_id': [f'Sample_{i+1}' for i in range(len(self.results['concentrations']))],
                'concentration_ng_ml': self.results['concentrations'],
                'r_squared': self.results['r_squared']
            })

            # Save file dialog
            file_path = await self.app.main_window.dialog(
                toga.SaveFileDialog(
                    title="Save Results",
                    suggested_filename="elisa_results.csv",
                    file_types=['csv']
                )
            )

            if file_path:
                df.to_csv(file_path, index=False)
                await self.app.main_window.dialog(
                    toga.InfoDialog(
                        'Success',
                        f'Results exported to {file_path.name}'
                    )
                )

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', f"Export failed: {str(e)}"))
