import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class BeELISA(toga.App):
    def startup(self):
        """
        Construct and show the Toga application.
        """
        self.status_label = None
        self.log_window = None
        self.log_textbox = None
        
        # Main window title
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Create main container
        main_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        

        # Create tab container for different views
        self.content_tabs = toga.OptionContainer(
            style=Pack(flex=2) 
        )
        
        #  tabs using the content.append() method
        self.content_tabs.content.append("ELISA Analysis", self.create_elisa_view())
        self.content_tabs.content.append("Data View", self.create_data_view())
        
        main_box.add(self.content_tabs)
        
        # Logs seperate window
        open_logs_btn = toga.Button("Open Logs", on_press=self.show_logs, style=Pack(margin=5))
        main_box.add(open_logs_btn)


        # Status bar
        self.status_label = toga.Label(
            "Ready",
            style=Pack(margin=2)  
        )
        main_box.add(self.status_label)
        
        self.main_window.content = main_box
        self.main_window.show()
        
        
    
    # View creation methods
    def create_elisa_view(self):
        """Create ELISA analysis interface"""
        from .ui.elisa_view import Mainboard
        view = Mainboard(self)
        return view.create_layout()

    def create_data_view(self):
        """Create data viewing interface"""
        from .ui.data_view import DataView
        view = DataView(self)
        return view.create_layout()

    
    
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