import pandas as pd
from pathlib import Path

class DataLoader:
    """Handle loading and validating data"""
    
    def __init__(self, app):
        self.app = app
        self.data = None
        self.file_path = None
    
        self.metadata_df = None
        self.plate_raw_df = None
        self.plate_id_df = None
        
    def load_metadata(self, file_path, parser=None):
        """
        Load metadata file (patient demographics, diagnosis, etc.).

        Args:
            file_path: Path to metadata CSV file

        Returns:
            Tuple of (success, message)
        """
        try:
            if parser is None:
                from .elisa_parser import ELISAParser
                parser = ELISAParser(self.app)
                
            # Determine file type and load
            file_path = Path(file_path)
            self.app.log(f'Loaded Meta Data: {file_path}')  

            if file_path.suffix == '.csv':
                metadata = pd.read_csv(file_path)
                metadata = parser._parse_sample_metadata(metadata)
            elif file_path.suffix in ['.xlsx', '.xls']:
                metadata = pd.read_excel(file_path)
                metadata = parser._parse_sample_metadata(metadata)
            else:
                self.app.log("Unsupported file format")
                return False, "Unsupported file format"

            self.app.metadata_df = metadata

            self.app.refresh_data()
            
            # Store as separate metadata attribute
            if not hasattr(self, 'metadata'):
                self.metadata = metadata
            else:
                self.metadata = metadata
            self.app.log(f"Loaded metadata: {len(metadata)} records as {file_path.suffix.lstrip('.')} format")
            return True, f"Loaded metadata: {len(metadata)} records"
        except Exception as e:
            self.app.log(f"Error loading metadata: {str(e)}")
            return False, f"Error loading metadata: {str(e)}"

    def load_plate_id(self, file_path, parser=None):
        """
        Load Plate ID file reader.
        Expected format: 8 rows (A-H) x 12 columns (1-12) with sample IDs.
        
        Returns:
            Tuple of (success, message, parsed_data_dict)
        """
        try:
            if parser is None:
                from .elisa_parser import ELISAParser
                parser = ELISAParser(self.app)

            file_path = Path(file_path)
            self.app.log(f"Loaded Plate ID file: {file_path}")
            
            # Parse based on file type
            if file_path.suffix == '.csv':
                parsed_data = parser.parse_id_csv(str(file_path))
            elif file_path.suffix in ['.xlsx', '.xls']:
                parsed_data = parser.parse_id_excel(str(file_path))
            else:
                return False, "Unsupported file format", None
            self.app.refresh_data()

            self.app.log(f"Plate ID file loaded successfully as {file_path.suffix.lstrip('.')} format")
            return True, "Plate ID file loaded successfully", parsed_data

        except Exception as e:
            err = f"Error loading Plate ID: {str(e)}"
            self.app.log(err)
            return False, err, None
        
    def load_elisa_raw(self, file_path, parser=None):
        """
        Load raw ELISA plate reader data.

        Args:
            file_path: Path to raw ELISA file
            parser: Optional ELISAParser instance (will create if not provided)

        Returns:
            Tuple of (success, message, parsed_data_dict)
        """
        try:
            if parser is None:
                from .elisa_parser import ELISAParser
                parser = ELISAParser(self.app)

            file_path = Path(file_path)
            self.app.log(f"Loaded Raw Data file: {file_path}")
            
            # Parse based on file type
            if file_path.suffix == '.csv':
                parsed_data = parser.parse_raw_csv(str(file_path))
            elif file_path.suffix in ['.xlsx', '.xls']:
                parsed_data = parser.parse_raw_excel(str(file_path))
            else:
                return False, "Unsupported file format", None
            self.app.refresh_data()

            self.app.log(f"Raw ELISA data loaded successfully as {file_path.suffix.lstrip('.')} format")
            return True, "Raw ELISA data loaded successfully", parsed_data

        except Exception as e:
            err = f"Error loading ELISA data: {str(e)}"
            self.app.log(err)
            return False, err, None