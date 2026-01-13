import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from .data import ELISAParser
from .data import DataViewer
from .analysis import AnalysisEngine


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

        # Analysis state
        self.analysis_config = {
            'calibrant_concentrations': {},
            'dilution_factor': 1.0,
            'lod_loq_mode': 'per_plate'
        }
        self.analysis_results = None

        self.parser = ELISAParser(self)
        self.viewer = DataViewer(self)
        self.engine = AnalysisEngine(self)
        

        log = toga.Command(
            self.show_logs,
            text="Open Logs",
            tooltip="Open Log Panal in an Extra Window",
            group=toga.Group.FILE,
            shortcut=toga.Key.MOD_1 + 'l', # shortcut for open logs is ctrl/Cmd (MOD_1) plus the added letter 
            order=1
        )
            
        # all File Commands
        refresh = toga.Command(
            self.viewer.refresh_data,
            text="Refresh",
            tooltip="Refresh all Taps",
            group=toga.Group.FILE,
            shortcut=toga.Key.MOD_1 + 'r', # shortcut for open logs is ctrl/Cmd (MOD_1) plus the added letter 
            order=2
        )
        # all File Commands
        self.commands.add(log, refresh)
        
        
        
        # Main window title
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Create main container
        main_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        



        # Create tab container for different views
        self.content_tabs = toga.OptionContainer(
            style=Pack(flex=2) 
        )
        
        #  tabs using the content.append() method
        self.content_tabs.content.append("DATA IMPORT", self.create_elisa_view())
        self.content_tabs.content.append("DATA VIEW", self.create_data_view())
        self.content_tabs.content.append("ANALYSIS", self.create_analysis_view())
        
        main_box.add(self.content_tabs)
        
        

        # start_analysis_btn = toga.Button("Start Analysis", on_press=self.start_analysis, style=Pack(margin=5))
        # main_box.add(start_analysis_btn)
        self.loading = toga.ActivityIndicator(style=Pack(width=5, height=5))
        loading_box = toga.Box(children=[self.loading], style=Pack(align_items="center", justify_content="center"))

        main_box.add(loading_box)

        # Status bar
        self.status_label = toga.Label(
            "Ready",
            style=Pack(margin=2)  
        )
        main_box.add(self.status_label)
        
        self.main_window.content = main_box
        self.main_window.show()

    # Plate management methods
    def add_plate(self, name, raw_df, id_df, raw_filename=None, plate_id_filename=None):
        """Add a new plate to the collection"""
        self.plates.append({
            "name": name,
            "raw_df": raw_df,
            "id_df": id_df,
            "raw_filename": raw_filename,
            "plate_id_filename": plate_id_filename
        })

    def remove_plate(self, index):
        """Remove plate at index"""
        if 0 <= index < len(self.plates):
            del self.plates[index]

    def update_plate_name(self, index, new_name):
        """Update plate name"""
        if 0 <= index < len(self.plates):
            self.plates[index]["name"] = new_name

    # View creation methods
    def create_elisa_view(self):
        """Create ELISA analysis interface"""
        from .ui.elisa_view import Mainboard
        view = Mainboard(self)
        return view.create_layout()

    # View migrated data
    def create_data_view(self):
        """Create data viewing interface"""
        from .ui.data_view import DataView
        self.view = DataView(self)
        return self.view.create_layout()

    # Analysis view
    def create_analysis_view(self):
        """Create analysis interface"""
        from .ui.analysis_view import AnalysisView
        self.analysis_view = AnalysisView(self)
        return self.analysis_view.create_layout()


    # def start_analysis(self, widget=None):
    #     self.log('started analysis')
    
    def show_logs(self, widget=None):
        """ Open Logs Window """
        def build():
            self.log_window = toga.Window(title="BeELISA Logging Window")
            self.log_textbox = toga.MultilineTextInput(
                value = '',
                readonly = True,
                style=Pack(flex=1, font_size=10, margin=1, background_color='transparent')
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
    
        status = getattr(self, "status_label", None)
        if status is not None:
            status.text = message

        textbox = getattr(self, "log_textbox", None)
        if textbox is not None:
            textbox.value = (textbox.value or "") + message + "\n"


def main():
    return BeELISA()
