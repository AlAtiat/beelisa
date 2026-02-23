import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class DataViewer:
    """Data viewing and management interface"""

    def __init__(self, app):
        self.app = app
        self.original_df = None
        self.active_filters = {'plates': [], 'well_types': []}


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
            

    def update_table(self):
        """Update table with new data"""

        # Convert DataFrame to Toga table format
        data_table_df = getattr(self.app, "connected_df", None)
        data_view = getattr(self.app, "data_view", None)
        if data_table_df is None or data_table_df.empty:
            self.app.log("Please Import Data")
            self.app.loading.stop()

            return

        if data_view is None or getattr(data_view, "data_table", None) is None:
            self.app.log("DataView not created yet (open Data View tab once).")
            self.app.loading.stop()
            return

        # Populate filter checkboxes when data loads
        if hasattr(data_view, 'populate_plate_filters'):
            data_view.populate_plate_filters()

        headings = [str(c) for c in data_table_df.columns]
        rows = [tuple(r) for r in data_table_df.to_numpy()]
        # remove old table
        if getattr(data_view, "data_table", None) is not None:
            try:
                data_view.table_holder.remove(data_view.data_table)
            except Exception:
                # sometimes already removed; ignore
                pass

        # create new table with correct data
        data_view.data_table = toga.Table(
            headings=headings,
            data=rows,
            style=Pack(flex=1, margin=5)
        )
        data_view.table_holder.add(data_view.data_table)

    def update_summary(self):
        """Update summary statistics"""

        data_table_df = getattr(self.app, "connected_df", None)
        data_view = getattr(self.app, "data_view", None)

        if data_table_df is None or data_table_df.empty or data_view is None or getattr(data_view, "summary_label", None) is None:
            return

        n_rows = len(data_table_df)
        n_cols = data_table_df.shape[1]
        n_samples = data_table_df[data_table_df["well_type"] == "SAMPLE"]["sample_id"].nunique() if "well_type" in data_table_df.columns else 0
        n_missing_meta = (
            data_table_df[(data_table_df["well_type"] == "SAMPLE") & (data_table_df["_merge"] != "both")].shape[0]
            if "well_type" in data_table_df.columns and "_merge" in data_table_df.columns else 0
        )

        data_view.summary_label.text = (
            f"Rows: {n_rows} | Cols: {n_cols}\n"
            f"Number of samples (SAMPLE): {n_samples}\n"
            f"SAMPLE wells missing from metadata: {n_missing_meta}"
        )

    def apply_filters(self, selected_plates, selected_well_types):
        """Apply filters"""
        data_df = self.original_df if self.original_df is not None else self.app.connected_df

        if data_df is None or data_df.empty:
            return data_df

        filtered_df = data_df.copy()

        # Apply plate filter (if any selected)
        if selected_plates:
            filtered_df = filtered_df[filtered_df['plate_name'].isin(selected_plates)]

        # Apply well type filter (as and with the plate filter aswell)
        if selected_well_types:
            filtered_df = filtered_df[filtered_df['well_type'].isin(selected_well_types)]

        return filtered_df

    def update_table_with_filters(self, selected_plates, selected_well_types):
        """Update table with filtered data"""

        # Store original if not already stored
        self.original_df = self.app.connected_df.copy() if self.app.connected_df is not None else None

        # Apply filters
        filtered_df = self.apply_filters(selected_plates, selected_well_types)

        # Temporarily replace connected_df with filtered version, we might need to change it so we dont missout on anything when analysis starts
        temp_original = self.app.connected_df
        self.app.connected_df = filtered_df

        # Update display
        self.update_table()
        self.update_summary()

        # Restore original
        self.app.connected_df = temp_original


    def clear_filters(self):
        """Clear all filters and show original data"""
        if self.original_df is not None:
            self.app.connected_df = self.original_df.copy()
            self.update_table()
            self.update_summary()
            self.original_df = None
        else:
            self.update_table()
            self.update_summary()
            self.app.log('Filters cleared (view reset to current data)')
            return


