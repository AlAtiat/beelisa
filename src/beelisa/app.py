import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class BeELISA(toga.App):
    def startup(self):
        """
        Construct and show the Toga application.
        """
        # Main window title
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Create main container
        main_box = toga.Box(style=Pack(direction=COLUMN))
        

        # Create tab container for different views
        self.content_tabs = toga.OptionContainer(
            style=Pack(flex=2) 
        )
        
        #  tabs using the content.append() method
        self.content_tabs.content.append("ELISA Analysis", self.create_elisa_view())
        self.content_tabs.content.append("Data View", self.create_data_view())
        
        main_box.add(self.content_tabs)
        
        # Status bar
        self.status_label = toga.Label(
            "Ready",
            style=Pack(margin=2)  # padding is OK for Label
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

    


def main():
    return BeELISA()