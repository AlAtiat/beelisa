import asyncio

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class BeELISA(toga.App):
    def startup(self):
        """
        Construct and show the Toga application.
        """
        # toga.Widget.DEBUG_LAYOUT_ENABLED = True
        
        self.status_label = None
        self.log_window = None
        self.log_textbox = None
        
        self.metadata_df = None
        self.plates = []  # List of plate dictionaries: {"name": str, "raw_df": DataFrame, "id_df": DataFrame}
        self.plate_design_df = None
        self.connected_df = None
        self.calibrant_count = None

        # Plate grouping for inter-group analysis
        self.plate_groups = {}  # {"Group Name": ["Plate_001", "Plate_002", ...]}

        # Analysis state
        self.analysis_config = {
            'calibrant_concentrations': {},
            'dilution_factor': 1.0,
            'lod_loq_mode': 'per_plate',
        }
        self.analysis_results = None
        self._data_dirty = False  # True when connected_df needs recomputing

        # Placeholders filled by on_running()
        self.view = None
        self.parser = None
        self.viewer = None
        self.engine = None
        self.data_view = None
        self.analysis_view = None
        self.results_view = None
        self.loading = None
        self.content_tabs = None

        # Menu commands
        log_cmd = toga.Command(
            self.show_logs,
            text='Open Logs',
            tooltip='Open Log Panel in an Extra Window',
            group=toga.Group.FILE,
            shortcut=toga.Key.MOD_1 + 'l',
            order=1,
        )
        refresh_cmd = toga.Command(
            self.refresh_data,
            text='Refresh',
            tooltip='Refresh all Tabs',
            group=toga.Group.FILE,
            shortcut=toga.Key.MOD_1 + 'r',
            order=2,
        )
        save_cmd = toga.Command(
            self.save_session,
            text='Save Session',
            tooltip='Export current session files to a .beelisa file',
            group=toga.Group.FILE,
            shortcut=toga.Key.MOD_1 + 's',
            order=3,
        )
        load_cmd = toga.Command(
            self.load_session,
            text='Load Session',
            tooltip='Import a session files from a .beelisa file',
            group=toga.Group.FILE,
            shortcut=toga.Key.MOD_1 + 'o',
            order=4,
        )
        self.commands.add(log_cmd, refresh_cmd, save_cmd, load_cmd)


        # Set app icon 
        try:
            self.icon = toga.Icon(str(self.paths.app / 'resources' / 'icons' / 'beelisa'))
        except Exception:
            pass


        # start window
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = self._build_loading_window()
        self.main_window.show()


    def _build_loading_window(self):
        """loading_window shown at application start"""
        box = toga.Box(
            style=Pack(
                direction=COLUMN,
                flex=1,
                align_items='center',
                justify_content='center',
            )
        )

        try:
            logo_path = self.paths.app / 'resources' / 'icons' / 'beelisa.ico'
            img = toga.ImageView(
                toga.Image(str(logo_path)),
                style=Pack(width=100, height=100, margin=20),
            )
            box.add(img)
        except Exception:
            pass
        
        version = self.app.version
        author = self.app.author
        box.add(toga.Label('BeELISA', style=Pack(font_size=24, font_weight='bold', margin=10)))
        box.add(toga.Label(f'v{version}  •  {author}', style=Pack(font_size=10, color='#666666', margin=(0,10,10,10))))
        box.add(toga.Label('Initializing\u2026', style=Pack(font_size=12, margin=5)))
        box.add(toga.ActivityIndicator(running=True, style=Pack(margin=10)))
        return box

    # run application modules and build the UI

    async def on_running(self):
        """Import modules and build the UI after loading_window is visible."""

        # Yield so the OS can paint the loading_window frame
        await asyncio.sleep(0.01)

        #  imports
        from .ui.elisa_view import Mainboard
        from .ui.data_view import DataView
        from .ui.analysis_view import AnalysisView
        from .ui.results_view import ResultsView
        from .data import ELISAParser, DataViewer
        from .analysis import AnalysisEngine

        # Instantiate subsystems
        self.view = Mainboard(self)
        self.parser = ELISAParser(self)
        self.viewer = DataViewer(self)
        self.engine = AnalysisEngine(self)
        self.data_view = DataView(self)
        self.analysis_view = AnalysisView(self)
        self.results_view = ResultsView(self)

        self.loading = toga.ActivityIndicator(style=Pack(width=10, height=10))
        loading_box = toga.Box(
            children=[self.loading],
            style=Pack(align_items='center', justify_content='center'),
        )
        self.status_label = toga.Label('Ready', style=Pack(margin=2))

        # Phase 3a: attach OptionContainer with NO tabs so Cocoa's
        # tabView_didSelectTabViewItem_ has nothing to cascade into.
        self.content_tabs = toga.OptionContainer(style=Pack(flex=2))
        main_box = toga.Box(
            children=[self.content_tabs, loading_box, self.status_label],
            style=Pack(direction=COLUMN, flex=1),
        )
        self.main_window.content = main_box   # no tabs → delegate is a no-op
        await asyncio.sleep(0)                # window refs now propagated

        # Phase 3b: add tabs now that the OptionContainer has a window
        self.content_tabs.content.append('DATA IMPORT', self.create_elisa_view())
        self.content_tabs.content.append('DATA VIEW', self.create_data_view())
        self.content_tabs.content.append('ANALYSIS', self.create_analysis_view())
        self.content_tabs.content.append('RESULTS', self.create_results_view())
        self.content_tabs.on_select = self._on_tab_select
        await asyncio.sleep(0)                # let tab-selection delegate settle

        # Phase 3c: now safe to assign ScrollContainer contents
        self.view.apply_scroll_contents()
        self.data_view.apply_scroll_contents()
        self.analysis_view.apply_scroll_contents()
        self.results_view.apply_scroll_contents()

    # Plate management methods
    def add_plate(self, name, raw_df, id_df, raw_filename=None, plate_id_filename=None):
        """Add a new plate to the collection."""
        self.plates.append({
            'name': name,
            'raw_df': raw_df,
            'id_df': id_df,
            'raw_filename': raw_filename,
            'plate_id_filename': plate_id_filename,
        })
        self._data_dirty = True

    def remove_plate(self, index):
        """Remove plate at index."""
        if 0 <= index < len(self.plates):
            del self.plates[index]
            self._data_dirty = True

    def update_plate_name(self, index, new_name):
        """Update plate name."""
        if 0 <= index < len(self.plates):
            self.plates[index]['name'] = new_name
            self._data_dirty = True

    # View creation methods
    def create_elisa_view(self):
        """Create ELISA analysis interface"""
        return self.view.create_layout()

    # View migrated data
    def create_data_view(self):
        """Create data viewing interface"""
        return self.data_view.create_layout()

    # Analysis view
    def create_analysis_view(self):
        """Create analysis interface"""
        return self.analysis_view.create_layout()

    # Results view
    def create_results_view(self):
        """Create results interface"""
        return self.results_view.create_layout()

    # Menu actions
    def refresh_data(self, widget=None):
        """Start refreshing data in a background task from toga"""
        if self.loading is not None:
            self.loading.start()
        asyncio.create_task(self.perform_refresh())

    async def perform_refresh(self, widget=None):
        """Refresh current data."""
        try:
            self.parser.try_merge()
            # Update viewer if available
            if hasattr(self, 'viewer') and self.viewer is not None:
                self.viewer.update_table()
                self.viewer.update_summary()

            if hasattr(self, 'data_view') and self.viewer is not None:
                self.data_view.populate_plate_filters()

            if hasattr(self, 'analysis_view') and self.analysis_view is not None:
                self.analysis_view.update_variable_selection()
                self.analysis_view.rebuild_calibrant_rows()
                self.analysis_view.refresh_plate_checkboxes()
                self.analysis_view.refresh_groups_display()
                
        except Exception as e:
            await self.main_window.dialog(toga.ErrorDialog('Error', f'Refresh failed: {str(e)}'))


        finally:
            if self.loading is not None:
                self.loading.stop()
            self._data_dirty = False

    def _on_tab_select(self, widget):
        """Auto-refresh data-dependent tabs when data has changed."""
        if not self._data_dirty:
            return
        try:
            tab_text = widget.current_tab.text
        except Exception:
            return
        if tab_text in ('DATA VIEW', 'ANALYSIS'):
            self.refresh_data()

    async def save_session(self, widget=None):
        """Export all current app state to a .beelisa session file."""
        from .data.session_io import SessionIO

        try:
            if self.loading is not None:
                await asyncio.sleep(0.01)
                self.loading.start()
            path = await self.main_window.dialog(
                toga.SaveFileDialog(
                    title='Save Session',
                    suggested_filename='session.beelisa',
                    file_types=['beelisa'],
                )
            )
            if path:
                SessionIO.save(self, str(path))
                self.log(f'Session saved: {path}')
                await self.main_window.dialog(
                    toga.InfoDialog('Session Saved', f'Session saved to:\n{path}')
                )
            self.loading.stop()

        except Exception as e:
            if self.loading is not None:
                self.loading.stop()
            await self.main_window.dialog(toga.ErrorDialog('Save Failed', str(e)))

    async def load_session(self, widget=None):
        """Import app state from a .beelisa session file."""
        from .data.session_io import SessionIO

        try:
            if self.loading is not None:
                await asyncio.sleep(0.01)
                self.loading.start()
            path = await self.main_window.dialog(
                toga.OpenFileDialog(
                    title='Load Session',
                    file_types=['beelisa'],
                )
            )
            if not path:
                self.loading.stop()
                return


            session = SessionIO.load(str(path))
            data = session['session_data']

            # 1. Restore DataFrames and simple state
            self.metadata_df = session['metadata_df']
            self.plates = session['plates']
            self.plate_design_df = session['plate_design_df']
            self.calibrant_count = data.get('calibrant_count')
            self.plate_groups = data.get('plate_groups', {})

            # 2. Restore analysis_config — JSON stores int keys as strings
            config = data.get('analysis_config', {})
            cal = config.get('calibrant_concentrations', {})
            config['calibrant_concentrations'] = {int(k): float(v) for k, v in cal.items()}
            self.analysis_config = config

            # 3. Restore PlateModel state
            plate_model = self.view.plate_widget.model
            state = data.get('plate_model_state', {})
            SessionIO.restore_plate_model(plate_model, state)

            # 4. Update UI widgets
            self.view.sample_id_md.value = data.get('metadata_sample_id_column', 'TM')
            if self.metadata_df is not None:
                self.view.meta_status.text = f'Loaded: {len(self.metadata_df)} records'
            self.view.refresh_plates_list()
            self.view.plate_widget.refresh_visualization()

            # 5. Full refresh — merges data, rebuilds analysis view, etc.
            await self.perform_refresh()

            self.log(f'Session loaded: {path}')
            await self.main_window.dialog(
                toga.InfoDialog('Session Loaded', 'Session loaded successfully!')
            )
            self.loading.stop()

        except Exception as e:
            if self.loading is not None:
                self.loading.stop()
            await self.main_window.dialog(toga.ErrorDialog('Load Failed', str(e)))

    def show_logs(self, widget=None):
        """ Open Logs Window """
        def build():
            self.log_window = toga.Window(title='BeELISA Logging Window')
            self.log_textbox = toga.MultilineTextInput(
                value='',
                readonly=True,
                style=Pack(flex=1, font_size=10, margin=1, background_color='transparent'),
            )
            box = toga.Box(style=Pack(direction=COLUMN, flex=1))
            box.add(self.log_textbox)
            self.log_window.content = box

        if self.log_window is None:
            build()
        try:
            self.log_window.show()
        except Exception:
            build()
            self.log_window.show()

    def log(self, message: str):
        status = getattr(self, 'status_label', None)
        if status is not None:
            status.text = message

        textbox = getattr(self, 'log_textbox', None)
        if textbox is not None:
            textbox.value = (textbox.value or '') + message + '\n'


def main():
    return BeELISA()
