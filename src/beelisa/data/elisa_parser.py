"""Parser for raw ELISA plate reader data."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class ELISAParser:
    """Parse raw ELISA plate reader data in various formats."""

    def __init__(self):
        self.plate_data = None
        self.metadata = None
        self.well_mapping = None

    def parse_csv(self, file_path: str) -> Dict:
        """
        Parse raw ELISA CSV file from plate reader.

        Expects format:
        - Row 1-3: Headers
        - Row 4: OD measurements (96 wells in order)
        - Additional rows: Metadata

        Args:
            file_path: Path to raw ELISA CSV file

        Returns:
            Dictionary with parsed data:
                - 'od_values': List of 96 OD measurements
                - 'metadata': Instrument metadata
                - 'well_ids': Well identifiers (A1-H12)
        """
        # Read the CSV file
        df = pd.read_csv(file_path, header=None)

        # Extract OD measurements from row 4 (index 3)
        # First two columns are usually time/temp, skip them
        od_row = df.iloc[3, 2:].values  # Skip first 2 columns
        od_values = self._clean_od_values(od_row)

        # Generate well IDs (A1-H12 for 96-well plate)
        well_ids = self._generate_well_ids()

        # Extract metadata from remaining rows
        metadata = self._extract_metadata(df)

        # Create well-to-value mapping
        self.well_mapping = dict(zip(well_ids, od_values))

        return {
            'od_values': od_values,
            'well_ids': well_ids,
            'metadata': metadata,
            'well_mapping': self.well_mapping
        }

    def parse_excel(self, file_path: str, sheet_name: str = 'Sheet1') -> Dict:
        """
        Parse raw ELISA Excel file from plate reader.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read

        Returns:
            Dictionary with parsed data
        """
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

        # Similar logic as CSV parsing
        od_row = df.iloc[3, 2:].values
        od_values = self._clean_od_values(od_row)
        well_ids = self._generate_well_ids()
        metadata = self._extract_metadata(df)

        self.well_mapping = dict(zip(well_ids, od_values))

        return {
            'od_values': od_values,
            'well_ids': well_ids,
            'metadata': metadata,
            'well_mapping': self.well_mapping
        }

    def _clean_od_values(self, od_row: np.ndarray) -> List[float]:
        """
        Clean and convert OD values to float.

        Args:
            od_row: Raw OD values from file

        Returns:
            List of cleaned float values
        """
        od_values = []
        for val in od_row[:96]:  # Take first 96 values
            try:
                # Convert to float, handle various formats
                if pd.isna(val):
                    od_values.append(np.nan)
                else:
                    od_values.append(float(val))
            except (ValueError, TypeError):
                od_values.append(np.nan)

        return od_values

    def _generate_well_ids(self) -> List[str]:
        """
        Generate well IDs for 96-well plate (A1-H12).

        Returns:
            List of well IDs in row-major order
        """
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))  # 1-12

        well_ids = []
        for row in rows:
            for col in cols:
                well_ids.append(f"{row}{col}")

        return well_ids

    def _extract_metadata(self, df: pd.DataFrame) -> Dict:
        """
        Extract instrument metadata from file.

        Args:
            df: DataFrame containing raw file data

        Returns:
            Dictionary of metadata
        """
        metadata = {}

        # Try to extract common metadata fields
        # This depends on the specific file format
        try:
            # Look for date/time
            for idx, row in df.iterrows():
                if idx < 20:  # Check first 20 rows for metadata
                    for col_idx, val in enumerate(row):
                        if pd.notna(val):
                            val_str = str(val)
                            # Check for date patterns
                            if '/' in val_str and len(val_str.split('/')) == 3:
                                metadata['date'] = val_str
                            # Check for wavelength
                            elif 'nm' in val_str.lower():
                                if 'wavelength' not in metadata:
                                    metadata['wavelength'] = val_str
                                else:
                                    metadata['reference_wavelength'] = val_str
                            # Check for serial number
                            elif 'serial' in val_str.lower():
                                metadata['serial_number'] = val_str
        except Exception:
            pass

        return metadata

    def create_plate_dataframe(self, od_values: List[float],
                               sample_mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Create DataFrame with plate layout (8 rows x 12 columns).

        Args:
            od_values: List of 96 OD measurements
            sample_mapping: Optional dict mapping well IDs to sample IDs

        Returns:
            DataFrame with plate layout
        """
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))

        # Reshape OD values into 8x12 grid
        od_array = np.array(od_values).reshape(8, 12)

        # Create DataFrame
        plate_df = pd.DataFrame(od_array, index=rows, columns=cols)

        return plate_df

    def map_wells_to_samples(self, well_sample_mapping: Dict[str, str],
                            od_values: List[float],
                            well_ids: List[str]) -> pd.DataFrame:
        """
        Map well positions to sample IDs and create sample-level DataFrame.

        Args:
            well_sample_mapping: Dict mapping well IDs to sample IDs (e.g., {'A1': '202/1', 'A2': '202/1'})
            od_values: List of OD measurements
            well_ids: List of well IDs

        Returns:
            DataFrame with columns: sample_id, well_id, od_value
        """
        data = []

        for well_id, od_value in zip(well_ids, od_values):
            sample_id = well_sample_mapping.get(well_id, 'Unknown')
            data.append({
                'sample_id': sample_id,
                'well_id': well_id,
                'od_value': od_value
            })

        return pd.DataFrame(data)

    def identify_replicates(self, sample_df: pd.DataFrame) -> pd.DataFrame:
        """
        Group replicate wells and calculate statistics.

        Args:
            sample_df: DataFrame with sample_id, well_id, od_value

        Returns:
            DataFrame with: sample_id, mean_od, std_od, cv_percent, n_replicates
        """
        grouped = sample_df.groupby('sample_id')['od_value'].agg([
            ('mean_od', 'mean'),
            ('std_od', 'std'),
            ('n_replicates', 'count')
        ]).reset_index()

        # Calculate coefficient of variation (CV%)
        grouped['cv_percent'] = (grouped['std_od'] / grouped['mean_od']) * 100

        # Flag high CV samples (>20% is typically concerning)
        grouped['high_cv'] = grouped['cv_percent'] > 20

        return grouped

    def identify_blanks(self, sample_df: pd.DataFrame,
                       blank_identifier: str = 'Blank') -> Tuple[float, int]:
        """
        Identify and calculate mean blank OD.

        Args:
            sample_df: DataFrame with sample_id and od_value
            blank_identifier: String to identify blank wells

        Returns:
            Tuple of (mean_blank_od, n_blanks)
        """
        blanks = sample_df[sample_df['sample_id'].str.contains(
            blank_identifier, case=False, na=False
        )]

        if len(blanks) > 0:
            mean_blank = blanks['od_value'].mean()
            n_blanks = len(blanks)
            return mean_blank, n_blanks
        else:
            return 0.0, 0
