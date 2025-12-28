import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class DataView:
    """Data viewing and management interface"""
    
    def __init__(self, app):
        self.app = app
        self.data_table = None
        
    def create_layout(self):
        """Create data view layout"""
        container = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=1))
        
        # Controls section
        controls = self.create_controls()
        container.add(controls)
        
        # Data table
        self.table_holder = toga.Box(style=Pack(direction=COLUMN, flex=1, margin_top=10))
        container.add(self.table_holder)

        # initial empty table (placeholder headings)
        self.data_table = toga.Table(
            headings=["Please load Data first"],
            data=[],
            style=Pack(flex=1, margin=5)
        )
        self.table_holder.add(self.data_table)
        
    
        
        # Summary section
        summary = self.create_summary()
        container.add(summary)
        
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
            on_press=self.app.viewer.refresh_data,
            style=Pack(margin=5)
        )
        
        controls.add(export_btn, refresh_btn)
        return controls
    
    def create_summary(self):
        """Create summary statistics display"""
        summary_box = toga.Box(style=Pack(direction=COLUMN, margin=10))
        
        self.summary_label = toga.Label(
            'No data loaded',
            style=Pack(margin=5)
        )
        
        summary_box.add(self.summary_label)
        return summary_box
    
