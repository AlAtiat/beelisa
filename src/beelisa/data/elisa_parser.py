"""Parser for raw ELISA plate reader data."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class ELISAParser:
    """Parse raw ELISA plate reader data in various formats."""

    def __init__(self, app):
        self.app = app
        self.plate_raw_df = None
        self.plate_id_df = None
        self.metadata = None
        self.well_mapping = None

    def parse_raw_csv(self, file_path: str) -> Dict:
        """
        Parse ELISA CSV file from plate reader.

        Args:
            file_path: Path to ELISA CSV file

        Returns:
            Dictionary with parsed data:
                - 'parse_raw_csv': List of 96 well plate
        """
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))  # 1-12

        # Read the CSV file
        df = pd.read_csv(file_path, header=None)
        
        if df.shape == (8,12):
            plate_raw_df = pd.DataFrame(df.values, index=rows, columns=cols)
                
        elif df.shape[0] >= 9 and df.shape[1] >= 13:
            plate_block = df.iloc[1:9, 1:13]
            plate_raw_df = pd.DataFrame(plate_block.values, index=rows, columns=cols)
            

        else:
            self.app.log("Please make sure the data is formed as a 96 well plate")
            raise ValueError("Unsupported ELISA plate format")


        plate_df_log = plate_raw_df.to_string()

        self.app.log(plate_df_log)

        return plate_raw_df
        

    def parse_raw_excel(self, file_path: str, sheet_name: str = 'Sheet1') -> Dict:
        """
        Parse raw ELISA Excel file from plate reader.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read

        Returns:
            Dictionary with parsed data
        """
        
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))  # 1-12
        
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        if df.shape == (8,12):
            plate_raw_df = pd.DataFrame(df.values, index=rows, columns=cols)
                
        elif df.shape[0] >= 9 and df.shape[1] >= 13:
            plate_block = df.iloc[1:9, 1:13]
            plate_raw_df = pd.DataFrame(plate_block.values, index=rows, columns=cols)
            

        else:
            self.app.log("Please make sure the data is formed as a 96 well plate")
            raise ValueError("Unsupported ELISA plate format")


        plate_df_log = plate_raw_df.to_string()

        self.app.log(plate_df_log)

        return plate_raw_df

    def parse_id_csv(self, file_path: str) -> Dict:
        """
        Parse ELISA CSV file from plate reader.

        Args:
            file_path: Path to ELISA CSV file

        Returns:
            Dictionary with parsed data:
                - 'plate_df': List of 96 well plate
        """
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))  # 1-12

        # Read the CSV file
        df = pd.read_csv(file_path, header=None)
        
        if df.shape == (8,12):
            plate_id_df = pd.DataFrame(df.values, index=rows, columns=cols)
                
        elif df.shape[0] >= 9 and df.shape[1] >= 13:
            plate_block = df.iloc[1:9, 1:13]
            plate_id_df = pd.DataFrame(plate_block.values, index=rows, columns=cols)

        else:
            self.app.log("Please make sure the data is formed as a 96 well plate")
            raise ValueError("Unsupported ELISA plate format")

        plate_df_log = plate_id_df.to_string()

        self.app.log(plate_df_log)

        return plate_id_df
        

    def parse_id_excel(self, file_path: str, sheet_name: str = 'Sheet1') -> Dict:
        """
        Parse raw ELISA Excel file from plate reader.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read

        Returns:
            Dictionary with parsed data
        """
        
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))  # 1-12
        
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        if df.shape == (8,12):
            plate_id_df = pd.DataFrame(df.values, index=rows, columns=cols)
                
        elif df.shape[0] >= 9 and df.shape[1] >= 13:
            plate_block = df.iloc[1:9, 1:13]
            plate_id_df = pd.DataFrame(plate_block.values, index=rows, columns=cols)
            
        else:
            self.app.log("Please make sure the data is formed as a 96 well plate")
            raise ValueError("Unsupported ELISA plate format")

        plate_df_log = plate_id_df.to_string()

        self.app.log(plate_df_log)

        return plate_id_df


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
                well_ids.append(f"{row}{col:02d}")

        return well_ids
    
    # this is only custome to our use shouldnt be removed before deployment
    def _base_sample_id(self, value):
        if value is None or pd.isna(value):
            return None
        s = str(value).strip()
        if s == "" or s.lower() == "nan":
            return None
        return s.split("/")[0]   # 201/1 → 201

    def _sample_id_aliases(self, df: pd.DataFrame) -> str:
        aliases = [
            "sample_id", "sampleid", "sample id",
            "patient_id", "patientid", "patient id",
            "id", "tm", "TM"
        ]
        
        sample_id = {str(c).strip().lower(): c for c in df.columns}
        
        for a in aliases:
            key = a.strip().lower()
            if key in sample_id:
                return sample_id[key]
        
        raise ValueError(f"Metadata must contain a sample id column. Tried: {aliases}")
        
    def _parse_sample_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        sample_id_df = df.copy()

        # drop fully empty rows
        sample_id_df = sample_id_df.dropna(how="all")

        # checl for sample id aliases
        sid_col = self._sample_id_aliases(sample_id_df)

        # clean
        sample_id_df[sid_col] = sample_id_df[sid_col].astype(str).str.strip()
        sample_id_df[sid_col] = sample_id_df[sid_col].str.replace(r"\.0$", "", regex=True)
        sample_id_df[sid_col] = sample_id_df[sid_col].replace({"": np.nan, "nan": np.nan, "None": np.nan})

        # rename to guaranteed name
        sample_id_df = sample_id_df.rename(columns={sid_col: "sample_id"})

        # now this works
        sample_id_df["sample_id"] = sample_id_df["sample_id"].apply(self._base_sample_id)
        self.app.log(f"Cleaned Metadata {sample_id_df.head(5).to_string()}")

        return sample_id_df

    def try_merge(self):
        """ Tries to merge and connect all data when loaded to run the mapping"""
        
        if self.app.plate_raw_df is None:
            self.app.log("Please Load Raw Data")
            return None
        if self.app.plate_id_df is None:
            self.app.log("Please Load Plate Sample ID")
            return None
        if self.app.metadata_df is None:
            self.app.log("Please Load your Metadata")
            return None
        connected_df = self.map_wells_to_samples(self.app.metadata_df, self.app.plate_raw_df, self.app.plate_id_df)
        return connected_df
    
    def map_wells_to_samples(self, metadata_df,
                            plate_raw_df: List[float],
                            plate_id_df: List[str]) -> pd.DataFrame:
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

        for row in plate_raw_df.index:
            for col in plate_raw_df.columns:
                od_value = plate_raw_df.loc[row, col]
                sample_id = plate_id_df.loc[row, col]
                
                
                if pd.isna(sample_id):
                    sample_id = None
                else:
                    sample_id = str(sample_id).strip()
                    sample_id = sample_id.replace(".0", "") 
                    
                    
                well_id= f"{row}{int(col):02d}"
                
                data.append({
                    "well_id": well_id,
                    "sample_id": sample_id,
                    "od_value": od_value
                })
        mapped_df = pd.DataFrame(data)
        
        plate_design = self.app.plate_design_df
        mapped_df = mapped_df.merge(
            plate_design,
            on="well_id",
            how="left"
        )
        self.app.log(mapped_df.to_string())


        self.app.connected_df = mapped_df.merge(
            metadata_df,
            on="sample_id",
            how="left",
            indicator=False,
        )
        self.app.log(self.app.plate_design_df.head().to_string(index=False))
        self.app.log(self.app.connected_df.head(10).to_string(index=False))
        return self.app.connected_df

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
