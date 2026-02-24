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
        self.pending_raw_data = None
        self.pending_raw_filename = None
        self.pending_id_data = None
        self.pending_id_filename = None
        self.pending_plate_id_filename = None
        self.plates_container = None
        self.sample_id_md = None
        
    def create_layout(self):
        """Create ELISA analysis view layout."""
        # Phase 2: build all content; ScrollContainers created without content
        plate_section = self.create_plate_section()
        load_section = self.create_load_section()

        self._left_box = toga.Box(
            children=[plate_section],
            style=Pack(direction=COLUMN, flex=1),
        )
        self._right_box = toga.Box(
            children=[load_section],
            style=Pack(direction=COLUMN, flex=1),
        )
        # No content= here — assigned in apply_scroll_contents() after window attachment
        self._left_container  = toga.ScrollContainer(style=Pack(flex=1))
        self._right_container = toga.ScrollContainer(style=Pack(flex=1))
        container = toga.SplitContainer(
            content=[self._left_container, self._right_container],
            style=Pack(flex=1, margin=10),
        )
        self.app.log("Loaded Main View")
        return container

    def apply_scroll_contents(self):
        """Phase 3: assign ScrollContainer content after window attachment.
        Return False if not ready yet so caller can retry.
        """
        if getattr(self, "_scroll_applied", False):
            return True

        if self._left_container is None or self._right_container is None:
            return False
        if self._left_box is None or self._right_box is None:
            return False

        # Critical macOS guard: only attach once both containers have a window
        if self._left_container.window is None or self._right_container.window is None:
            return False

        self._left_container.content = self._left_box
        self._right_container.content = self._right_box
        self._scroll_applied = True
        return True

    def create_plate_section(self):
        """Create plate configuration section."""
        from .widgets.plate_widget import PlateWidget

        section_box = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=0))

        seperation_headline = toga.Box(
            children=[
                toga.Label(
                    'WELL PLATE DESIGN',
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
                    'ELISA DATA IMPORTING',
                    style=Pack(margin=1, font_size=16, font_weight='bold')
                ),
                toga.Divider(),
            ],
            direction=COLUMN,
            flex=0.1,
            margin=1
        )
        load_box.add(seperation_headline)
        
        
        
        # Metadata button
        meta_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        meta_btn = toga.Button(
            'Load Metadata',
            on_press=self.load_metadata,
            style=Pack(margin=5, flex=1)
        )
        self.meta_status = toga.Label(
            '',
            style=Pack(margin=5, flex=1)
        )
        meta_btn_box.add(meta_btn, self.meta_status)
        meta_data_load_button = meta_btn_box
        
        
        # sample id column
        sample_id_md_box = toga.Box(style=Pack(direction=ROW, margin=5))
        sample_id_md_label = toga.Label(
            'Sample ID Column:',
            style=Pack(margin=5)
        )
        self.sample_id_md = toga.TextInput(
            placeholder='e.g., Sample_id, TM, Sample, ID, sample id',
            style=Pack(margin=5, flex=1)
        )
        sample_id_md_box.add(sample_id_md_label, self.sample_id_md)
        
        
        metadata_block = toga.Box(
            children=[
                toga.Label(
                    'LOAD METADATA: ',
                    style=Pack(margin=5, font_weight='bold', background_color="#DBC5C5D1")
                ),
                toga.Divider(style=Pack(width=350, flex=1, margin=5)),
                sample_id_md_box,
                meta_data_load_button,
                toga.Divider(),

                
            ],
            direction=COLUMN,
            flex=1,
            margin=5
        )
        load_box.add(metadata_block)


        # Raw data and plate id data importing section
        plates_data_content = toga.Box(style=Pack(direction=COLUMN, margin=5, flex=1))

        # Raw data button
        raw_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        raw_btn = toga.Button(
            'Load Raw ELISA Data',
            on_press=self.load_raw_data,
            style=Pack(margin=5, flex=1)
        )
        self.raw_status = toga.Label(
            '',
            style=Pack(margin=5, flex=1)
        )
        raw_btn_box.add(raw_btn, self.raw_status)
        plates_data_content.add(raw_btn_box)

        # Plate ID button
        plate_id_btn_box = toga.Box(style=Pack(direction=ROW, margin=5))
        plate_id_btn = toga.Button(
            'Load Plate Sample ID',
            on_press=self.load_plate_id,
            style=Pack(margin=5, flex=1)
        )
        self.plate_id_status = toga.Label(
        '',
        style=Pack(margin=5, flex=1)
        )
        plate_id_btn_box.add(plate_id_btn, self.plate_id_status)
        plates_data_content.add(plate_id_btn_box)
        
        
        # Loaded Plates section
        plates_data_content_uploaded = toga.Box(style=Pack(direction=COLUMN, margin=5, flex=1))

        plates_section_box = toga.Box(style=Pack(direction=COLUMN, margin=5))
        plates_header = toga.Label('Uploaded Data (RAW +  PLATE SAMPLE ID MERGED)', style=Pack(margin=5, font_weight='bold', background_color="#DBC5C5D1"))

        # ScrollContainer to hold plate entries
        self.plates_container = toga.Box(style=Pack(direction=COLUMN))
        plates_scroll = toga.ScrollContainer(
            content=self.plates_container,
            style=Pack(height=150, margin=5, flex=0.1)
        )
        plates_section_box.add(plates_scroll)
        plates_data_content_uploaded.add(plates_section_box)
        
        
        
        plates_data_block = toga.Box(
            children=[
                toga.Label(
                    'LOAD (RAW/PLATE SAMPLE ID) DATA: ',
                    style=Pack(margin=5, font_weight='bold' , background_color="#DBC5C5D1")
                ),
                toga.Divider(style=Pack(width=350, flex=1, margin=5)),
                plates_data_content,
                toga.Divider(),
                plates_header,
                toga.Divider(style=Pack(width=350, flex=1, margin=5)),
                plates_data_content_uploaded

                
            ],
            direction=COLUMN,
            flex=1,
            margin=5
        )
        load_box.add(plates_data_block)

        # # Process button
        # process_btn = toga.Button(
        #     'Process ELISA Data',
        #     on_press=self.process_elisa,
        #     style=Pack(margin=10)
        # )
        # load_box.add(process_btn)


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
                    # Store as pending
                    self.pending_raw_data = parsed_data
                    self.pending_raw_filename = Path(file_path).name
                    self.raw_status.text = f"Pending: {Path(file_path).name}"

                    if self.pending_id_data is not None:
                        # Plate ID loaded first
                        await self._create_plate_pair()
                    else:
                        await self.app.main_window.dialog(toga.InfoDialog('Success',
                            "Raw data loaded. Now load the corresponding Plate ID file."))
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
                success, message, plate_id_df = loader.load_plate_id(file_path)

                if success:
                    self.pending_id_data = plate_id_df
                    self.pending_id_filename = Path(file_path).name
                    self.plate_id_status.text = f"Pending: {Path(file_path).name}"

                    if self.pending_raw_data is not None:
                        # Raw loaded first
                        await self._create_plate_pair()
                    else:
                        await self.app.main_window.dialog(toga.InfoDialog('Success',
                            "Plate ID loaded. Now load the corresponding Raw ELISA data file."))
                else:
                    await self.app.main_window.dialog(toga.ErrorDialog('Error', message))

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', str(e)))

    async def _create_plate_pair(self):
        """Create a plate entry from pending raw + ID data and clear all pending state."""
        plate_name = self.pending_raw_filename or f"Plate_{len(self.app.plates)+1}"
        self.app.add_plate(
            plate_name,
            self.pending_raw_data,
            self.pending_id_data,
            raw_filename=self.pending_raw_filename,
            plate_id_filename=self.pending_id_filename,
        )
        # Clear all pending state
        self.pending_raw_data = None
        self.pending_raw_filename = None
        self.pending_id_data = None
        self.pending_id_filename = None
        # Update UI
        self.raw_status.text = "No raw data loaded"
        self.plate_id_status.text = "No Plate Sample ID loaded"
        self.refresh_plates_list()
        await self.app.main_window.dialog(toga.InfoDialog('Success',
            f"Plate pair added: {plate_name}\nTotal plates: {len(self.app.plates)}"))

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

    def refresh_plates_list(self):
        """Refresh the plates list UI"""
        self.plates_container.clear()

        for i, plate in enumerate(self.app.plates):
            row = self.create_plate_row(i, plate)
            self.plates_container.add(row)

    def create_plate_row(self, index, plate):
        """Create a UI row for a single plate"""

        row_box = toga.Box(style=Pack(direction=ROW, margin=2, flex=1, width=350))

        # Editable plate name
        name_input = toga.TextInput(
            value=plate["name"],
            on_change=lambda widget, idx=index: self.on_plate_name_change(widget, idx),
            style=Pack(flex=1, margin=2)
        )

        # Display filenames (read-only)
        raw_file_name = plate.get("raw_filename", "N/A")
        plate_id_file_name = plate.get("plate_id_filename", "N/A")
        filename_display = f"{raw_file_name} + {plate_id_file_name}"

        filename_label = toga.Label(
            filename_display,
            style=Pack(margin=2, font_size=8)
        )

        # Remove button
        remove_btn = toga.Button(
            "Remove",
            on_press=lambda widget, idx=index: self.on_remove_plate(widget, idx),
            style=Pack(margin=2, width=80, flex=1)
        )

        row_box.add(name_input)
        row_box.add(remove_btn)

        # # Seperated uploaded files
        # uploaded_plates_block = toga.Box(
        #     children=[
        #         name_input,
        #         remove_btn,
        #         toga.Divider(),

                
        #     ],
        #     direction=ROW,
        #     flex=0.1,
        #     margin=5
        # )
        # row_box.add(uploaded_plates_block)
        
        card = toga.Box(style=Pack(direction=COLUMN, margin=5))
        card.add(row_box, filename_label)
        card.add(toga.Divider())
        return card
    
    
    def on_plate_name_change(self, widget, index):
        """edit merged plate name"""
        self.app.update_plate_name(index, widget.value)

    def on_remove_plate(self, widget, index):
        """remove merged plates"""
        self.app.remove_plate(index)
        self.refresh_plates_list()

