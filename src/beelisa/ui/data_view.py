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
        container = toga.Box(style=Pack(direction=COLUMN, margin=10))
        
        # Controls section
        controls = self.create_controls()
        container.add(controls)
        
        # Data table
        self.data_table = toga.Table(
            headings=['Column1', 'Column2', 'Column3'],
            data=[],
            style=Pack(flex=1, margin_top=10)
        )
        container.add(self.data_table)
        
        # Summary section
        summary = self.create_summary()
        container.add(summary)
        
        return container
    
    def create_controls(self):
        """Create control buttons"""
        controls = toga.Box(style=Pack(direction=ROW, margin=5))
        
        load_btn = toga.Button(
            'Load CSV',
            on_press=self.load_csv,
            style=Pack(margin=5)
        )
        
        load_excel_btn = toga.Button(
            'Load Excel',
            on_press=self.load_excel,
            style=Pack(margin=5)
        )
        
        export_btn = toga.Button(
            'Export',
            on_press=self.export_data,
            style=Pack(margin=5)
        )
        
        controls.add(load_btn, load_excel_btn, export_btn)
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
    
    async def load_csv(self, widget):
        """Handle CSV file loading"""
        try:
            file_path = await self.app.main_window.dialog(
                toga.OpenFileDialog(
                    title="Open CSV File",
                    file_types=['csv']
                )
            )

            if file_path:
                # Load data using DataLoader
                from ..data.loader import DataLoader
                loader = DataLoader()
                success, message = loader.load_csv(file_path)

                if success:
                    self.update_table(loader.data)
                    self.update_summary(loader.get_summary())
                    self.app.data_loader = loader
                    await self.app.main_window.dialog(toga.InfoDialog('Success', message))
                else:
                    await self.app.main_window.dialog(toga.ErrorDialog('Error', message))

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', str(e)))
    
    async def load_excel(self, widget):
        """Handle Excel file loading"""
        try:
            file_path = await self.app.main_window.dialog(
                toga.OpenFileDialog(
                    title="Open Excel File",
                    file_types=['xlsx', 'xls']
                )
            )

            if file_path:
                # Load data using DataLoader
                from ..data.loader import DataLoader
                loader = DataLoader()
                success, message = loader.load_excel(file_path)

                if success:
                    self.update_table(loader.data)
                    self.update_summary(loader.get_summary())
                    self.app.data_loader = loader
                    await self.app.main_window.dialog(toga.InfoDialog('Success', message))
                else:
                    await self.app.main_window.dialog(toga.ErrorDialog('Error', message))

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', str(e)))

    async def export_data(self, widget):
        """Export current data"""
        try:
            if not hasattr(self.app, 'data_loader') or self.app.data_loader is None or self.app.data_loader.data is None:
                await self.app.main_window.dialog(
                    toga.ErrorDialog('Error', 'No data to export. Please load data first.')
                )
                return

            file_path = await self.app.main_window.dialog(
                toga.SaveFileDialog(
                    title="Export Data",
                    suggested_filename="data_export.csv",
                    file_types=['csv']
                )
            )

            if file_path:
                self.app.data_loader.data.to_csv(file_path, index=False)
                await self.app.main_window.dialog(
                    toga.InfoDialog('Success', f'Data exported to {file_path.name}')
                )

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', f'Export failed: {str(e)}'))
    
    def update_table(self, data):
        """Update table with new data"""
        # Convert DataFrame to Toga table format
        self.data_table.data = [
            tuple(row) for row in data.head(100).values
        ]
        self.data_table.headings = list(data.columns)
    
    def update_summary(self, summary):
        """Update summary statistics"""
        text = f"Samples: {summary['n_samples']}\n"
        text += f"Features: {summary['n_features']}\n"
        text += f"Numeric: {len(summary['numeric_cols'])}"
        self.summary_label.text = text