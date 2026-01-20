import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class DataView:
    """Data viewing and management interface"""

    def __init__(self, app):
        self.app = app
        self.data_table = None
        self.plate_checkboxes = {}
        self.well_type_checkboxes = {}
        
    def create_layout(self):
        """Create data view layout"""
        box = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=1))
        container = toga.ScrollContainer(content=box,  style=Pack(flex=1))
        # Controls section
        controls = self.create_controls()
        box.add(controls)

        # Filter section
        filters = self.create_filter_section()
        box.add(filters)

        # Data table
        self.table_holder = toga.Box(style=Pack(direction=COLUMN, flex=1, margin_top=10))
        box.add(self.table_holder)

        # initial empty table (placeholder headings)
        self.data_table = toga.Table(
            headings=["Please load Data first"],
            data=[],
            style=Pack(flex=1, margin=5)
        )
        self.table_holder.add(self.data_table)
        
    
        
        # Summary section
        summary = self.create_summary()
        box.add(summary)
        self.container = container
        
        return container
    
    def create_controls(self):
        """Create control buttons"""
        controls = toga.Box(style=Pack(direction=ROW, margin=5))
        
        
        export_btn = toga.Button(
            'Export',
            on_press=self.app.viewer.export_data,
            style=Pack(margin=5)
        )
        refresh_btn = toga.Button(
            'Refresh Data',
            on_press=self.app.refresh_data,
            style=Pack(margin=5)
        )
        
        controls.add(export_btn, refresh_btn)
        return controls
    
    def create_summary(self):
        """summary statistics display"""
        summary_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        self.summary_label = toga.Label(
            'No data loaded',
            style=Pack(margin=5)
        )

        summary_box.add(self.summary_label)
        return summary_box

    def create_filter_section(self):
        """filter controls with checkboxes"""
        filter_box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Header
        header = toga.Label(
            'FILTERS',
            style=Pack(margin=5, font_weight='bold', font_size=12)
        )
        filter_box.add(header)
        filter_box.add(toga.Divider())

        # Two-column layout
        filters_row = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Plate filters
        plate_filter_box = toga.Box(style=Pack(direction=ROW, margin=5, flex=1))
        plate_label = toga.Label('Plates:', style=Pack(margin=3, font_weight='bold'))
        plate_filter_box.add(plate_label)

        self.plate_checkboxes_container = toga.Box(style=Pack(direction=ROW, margin=3, flex=1))
        plate_filter_box.add(self.plate_checkboxes_container)

        # Well type filters
        well_type_filter_box = toga.Box(style=Pack(direction=ROW, margin=5, flex=1))
        well_type_label = toga.Label('Well Types:', style=Pack(margin=3, font_weight='bold'))
        well_type_filter_box.add(well_type_label)

        self.well_type_checkboxes_container = toga.Box(style=Pack(direction=ROW, margin=3, flex=1))
        well_types = ['SAMPLE', 'BLANK', 'CALIBRANT', 'POSITIVE_CONTROL', 'NEGATIVE_CONTROL', 'EMPTY']

        for wtype in well_types:
            cb = toga.Switch(wtype, style=Pack(margin=2))
            self.well_type_checkboxes[wtype] = cb
            self.well_type_checkboxes_container.add(cb)

        well_type_filter_box.add(self.well_type_checkboxes_container)

        filters_row.add(plate_filter_box, well_type_filter_box)
        filter_box.add(filters_row)

        # Action buttons
        button_row = toga.Box(style=Pack(direction=ROW, margin=5))

        apply_btn = toga.Button('Apply Filters', on_press=self.on_apply_filters, style=Pack(margin=5))
        clear_btn = toga.Button('Clear Filters', on_press=self.on_clear_filters, style=Pack(margin=5))

        button_row.add(apply_btn, clear_btn)
        filter_box.add(button_row)

        return filter_box

    def populate_plate_filters(self):
        """Populate plate checkboxes from loaded data"""
        self.plate_checkboxes_container.clear()
        self.plate_checkboxes = {}

        data_df = self.app.connected_df
        if data_df is None or data_df.empty:
            return

        if 'plate_name' in data_df.columns:
            unique_plates = sorted(data_df['plate_name'].unique())

            for plate_name in unique_plates:
                checkbox = toga.Switch(str(plate_name), style=Pack(margin=2))
                self.plate_checkboxes[plate_name] = checkbox
                self.plate_checkboxes_container.add(checkbox)

    async def on_apply_filters(self, widget):
        """Apply selected filters"""
        selected_plates = [
            plate_name
            for plate_name, checkbox in self.plate_checkboxes.items()
            if checkbox.value
        ]

        selected_well_types = [
            wtype
            for wtype, checkbox in self.well_type_checkboxes.items()
            if checkbox.value
        ]

        self.app.viewer.update_table_with_filters(selected_plates, selected_well_types)

    async def on_clear_filters(self, widget):
        """Clear all filters"""
        for checkbox in self.plate_checkboxes.values():
            checkbox.value = False

        for checkbox in self.well_type_checkboxes.values():
            checkbox.value = False

        self.app.viewer.clear_filters()

