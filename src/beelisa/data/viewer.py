import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class DataViewer:
    """Data viewing and management interface"""
    
    def __init__(self, app):
        self.app = app


    async def export_data(self, widget):
        """Export current data"""
        
        try:
            data_table_df = getattr(self.app, "connected_df", None)
            if data_table_df is None or data_table_df.empty:
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
                data_table_df.to_csv(file_path, index=False, encoding="utf-8-sig")
                await self.app.main_window.dialog(
                    toga.InfoDialog('Success', f'Data exported to {file_path.name}')
                )

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', f'Export failed: {str(e)}'))
            
    async def refresh_data(self, widget):
        """Refresh current data"""
        
        try:

            
            self.app.parser.try_merge()

        except Exception as e:
            await self.app.main_window.dialog(toga.ErrorDialog('Error', f'Refresh failed: {str(e)}'))
    
    def update_table(self):
        """Update table with new data"""
        # Convert DataFrame to Toga table format
        data_table_df = getattr(self.app, "connected_df", None)
        view = getattr(self.app, "view", None)
        if data_table_df is None or data_table_df.empty:
            self.app.log("No data available for DataView")
            return
        
        if view is None or getattr(view, "data_table", None) is None:
            self.app.log("DataView not created yet (open Data View tab once).")
            return
        
        
        headings = [str(c) for c in data_table_df.columns]
        rows = [tuple(r) for r in data_table_df.to_numpy()]
        # remove old table
        if getattr(view, "data_table", None) is not None:
            try:
                view.table_holder.remove(view.data_table)
            except Exception:
                # sometimes already removed; ignore
                pass

        # create new table with correct data
        view.data_table = toga.Table(
            headings=headings,
            data=rows,
            style=Pack(flex=1, margin=5)
        )
        view.table_holder.add(view.data_table)
    
    def update_summary(self):
        """Update summary statistics"""

        data_table_df = getattr(self.app, "connected_df", None)
        view = getattr(self.app, "view", None)

        if data_table_df is None or data_table_df.empty or view is None or getattr(view, "summary_label", None) is None:
            return

        n_rows = len(data_table_df)
        n_cols = data_table_df.shape[1]
        n_samples = data_table_df[data_table_df["well_type"] == "SAMPLE"]["sample_id"].nunique() if "well_type" in data_table_df.columns else 0
        n_missing_meta = (
            data_table_df[(data_table_df["well_type"] == "SAMPLE") & (data_table_df["_merge"] != "both")].shape[0]
            if "well_type" in data_table_df.columns and "_merge" in data_table_df.columns else 0
        )

        view.summary_label.text = (
            f"Rows: {n_rows} | Cols: {n_cols}\n"
            f"Number of samples (SAMPLE): {n_samples}\n"
            f"SAMPLE wells missing from metadata: {n_missing_meta}"
        )
