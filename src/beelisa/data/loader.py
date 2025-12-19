import pandas as pd
from pathlib import Path

class DataLoader:
    """Handle loading and validating biomarker data"""
    
    def __init__(self):
        self.data = None
        self.file_path = None
    
    def load_csv(self, file_path):
        """Load data from CSV file"""
        try:
            self.data = pd.read_csv(file_path)
            self.file_path = file_path
            self._validate_data()
            return True, f"Loaded {len(self.data)} samples"
        except Exception as e:
            return False, f"Error loading file: {str(e)}"
    
    def load_excel(self, file_path):
        """Load data from Excel file"""
        try:
            self.data = pd.read_excel(file_path)
            self.file_path = file_path
            self._validate_data()
            return True, f"Loaded {len(self.data)} samples"
        except Exception as e:
            return False, f"Error loading file: {str(e)}"
    
    def _validate_data(self):
        """Validate required columns and data types"""
        # Check minimum data requirements
        if len(self.data.columns) == 0:
            raise ValueError("File contains no columns")
        if len(self.data) == 0:
            raise ValueError("File contains no data rows")

        # Basic data cleaning
        self.data = self.data.dropna(how='all')
        
    def get_summary(self):
        """Get data summary statistics"""
        if self.data is None:
            return None
        
        return {
            'n_samples': len(self.data),
            'n_features': len(self.data.columns),
            'numeric_cols': self.data.select_dtypes(include=['number']).columns.tolist(),
            'missing_data': self.data.isnull().sum().to_dict()
        }
    
    def get_numeric_data(self):
        """Get only numeric columns for analysis"""
        if self.data is None:
            return None
        return self.data.select_dtypes(include=['number'])

    def load_metadata(self, file_path):
        """
        Load metadata file (patient demographics, diagnosis, etc.).

        Args:
            file_path: Path to metadata CSV file

        Returns:
            Tuple of (success, message)
        """
        try:
            # Determine file type and load
            file_path = Path(file_path)
            if file_path.suffix == '.csv':
                metadata = pd.read_csv(file_path)
            elif file_path.suffix in ['.xlsx', '.xls']:
                metadata = pd.read_excel(file_path)
            else:
                return False, "Unsupported file format"

            # Store as separate metadata attribute
            if not hasattr(self, 'metadata'):
                self.metadata = metadata
            else:
                self.metadata = metadata

            return True, f"Loaded metadata: {len(metadata)} records"
        except Exception as e:
            return False, f"Error loading metadata: {str(e)}"

    def merge_with_metadata(self, elisa_data: pd.DataFrame,
                           sample_id_col: str = 'TM',
                           elisa_id_col: str = 'sample_id'):
        """
        Merge ELISA results with metadata based on sample ID.

        Args:
            elisa_data: DataFrame with ELISA results (must have sample_id column)
            sample_id_col: Column name in metadata for sample IDs
            elisa_id_col: Column name in elisa_data for sample IDs

        Returns:
            Merged DataFrame with both ELISA results and metadata
        """
        if not hasattr(self, 'metadata') or self.metadata is None:
            raise ValueError("Metadata must be loaded first using load_metadata()")

        # Merge on sample ID
        merged = pd.merge(
            elisa_data,
            self.metadata,
            left_on=elisa_id_col,
            right_on=sample_id_col,
            how='left'
        )

        # Store merged data
        self.data = merged

        return merged

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
                parser = ELISAParser()

            file_path = Path(file_path)

            # Parse based on file type
            if file_path.suffix == '.csv':
                parsed_data = parser.parse_csv(str(file_path))
            elif file_path.suffix in ['.xlsx', '.xls']:
                parsed_data = parser.parse_excel(str(file_path))
            else:
                return False, "Unsupported file format", None

            return True, "Raw ELISA data loaded successfully", parsed_data

        except Exception as e:
            return False, f"Error loading ELISA data: {str(e)}", None