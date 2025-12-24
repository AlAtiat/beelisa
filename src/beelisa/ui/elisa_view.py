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
        self.app.log("Loaded Main View")

        return container

    def create_plate_section(self):
        """Create plate configuration section."""
        from .widgets.plate_widget import PlateWidget

        section_box = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=0))

        seperation_headline = toga.Box(
            children=[
                toga.Label(
                    'Well Plate Design',
                    style=Pack(margin=1, font_size=16, font_weight='bold')
                ),
                toga.Divider(),

            
            ],
            direction=COLUMN,
            flex=0.1,
            margin=1
        )
        section_box.add(seperation_headline)

        # Create plate widget
        self.plate_widget = PlateWidget(self.app)
        plate_layout = self.plate_widget.create_layout()
        section_box.add(plate_layout)

        return section_box

    def create_load_section(self):
        """Create file loading controls."""
        load_box = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=0))

        
        seperation_headline = toga.Box(
            children=[
                toga.Label(
                    'ELISA Data Analysis',
                    style=Pack(margin=1, font_size=16, font_weight='bold')
                ),
                toga.Divider(),            
            ],
            direction=COLUMN,
            flex=0.1,
            margin=1
        )
        load_box.add(seperation_headline)

        # Raw data button
        raw_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        raw_btn = toga.Button(
            'Load Raw ELISA Data',
            on_press=self.load_raw_data,
            style=Pack(margin=5, flex=1)
        )
        self.raw_status = toga.Label(
            'No raw data loaded',
            style=Pack(margin=5, flex=1)
        )
        raw_btn_box.add(raw_btn, self.raw_status)
        load_box.add(raw_btn_box)

        # Plate ID button
        plate_id_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        plate_id_btn = toga.Button(
            'Load Plate ID',
            on_press=self.load_plate_id,
            style=Pack(margin=5, flex=1)
        )
        self.plate_id_status = toga.Label(
        'No Plate Sample ID loaded',
        style=Pack(margin=5, flex=1)
        )
        plate_id_btn_box.add(plate_id_btn, self.plate_id_status)
        load_box.add(plate_id_btn_box)
        
        # Metadata button
        meta_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        meta_btn = toga.Button(
            'Load Metadata',
            on_press=self.load_metadata,
            style=Pack(margin=5, flex=1)
        )
        self.meta_status = toga.Label(
            'No metadata loaded',
            style=Pack(margin=5, flex=1)
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
        # export_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        # export_btn = toga.Button(
        #     'Export Results',
        #     on_press=self.export_results,
        #     style=Pack(margin=5, flex=1)
        # )
        # self.export_status = toga.Label(
        #     'No Data to export',
        #     style=Pack(margin=5, flex=1)
        # )
        # export_btn_box.add(export_btn, self.export_status)
        # load_box.add(export_btn_box)

        return load_box

 

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

                loader = DataLoader(self.app)
                success, message, parsed_data = loader.load_elisa_raw(file_path)

                if success:
                    self.raw_data = parsed_data
                    self.raw_status.text = f"Loaded: {file_path.name}"
                    await self.app.main_window.dialog(toga.InfoDialog('Success', message))
                else:
                    await self.app.main_window.dialog(toga.ErrorDialog('Error', message))

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', str(e)))
        
    async def load_plate_id(self, widget):
        """ Load Plate ID for each plate to match the same Raw ELISA Data."""
        try:
            file_path = await self.app.main_window.dialog(
                toga.OpenFileDialog(
                    title="Open Plate ID File",
                    file_types=['csv', 'xlsx', 'xls']
                )
            )
        
            if file_path:
                from ..data.loader import DataLoader
                
                loader = DataLoader(self.app)
                success, message, plate_loaded_ids = loader.load_plate_id(file_path)

                if success:
                    self.plate_loaded_ids_data = plate_loaded_ids
                    self.plate_id_status.text = f"Loaded: {file_path.name}"
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

                loader = DataLoader(self.app)
                success, message = loader.load_metadata(file_path)

                if success:
                    self.metadata = loader.metadata
                    self.meta_status.text = f"Loaded: {len(self.metadata)} records"
                    await self.app.main_window.dialog(toga.InfoDialog('Success', message))
                else:
                    await self.app.main_window.dialog(toga.ErrorDialog('Error', message))

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', str(e)))

 