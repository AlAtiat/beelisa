"""TNM Clinical Staging Processor

"""

import pandas as pd
from .parsers.tnm_parser import TNMParser
from .parsers.uicc_parser import UICCParser
from .parsers.registry import ParserRegistry

# Direct alias: TNMProcessor
TNMProcessor = TNMParser


class ClinicalDataProcessor:
    """Process any categorical/ordinal column for clinical analysis.

    """

    def __init__(self):
        self.column_type = None  # 'numeric', 'categorical', 'tnm'
        self.analysis_columns = []
        self.violin_columns = []
        self.category_mapping = {}
        self.display_mapping = {}
        self._tnm_parser = TNMParser()
        self._uicc_parser = UICCParser()

    def detect_column_type(self, series) -> str:
        """Detect if column is numeric, categorical, or TNM-formatted."""
        if self._tnm_parser.can_parse(series):
            return 'tnm'
        if pd.api.types.is_numeric_dtype(series):
            if series.nunique() <= 15:
                return 'numeric'
        return 'categorical'

    def _is_uicc_like(self, series) -> bool:
        """Detect UICC-like values (delegates to UICCParser)."""
        return self._uicc_parser.can_parse(series)

    def _clean_uicc_value(self, value):
        """Clean a UICC value (delegates to UICCParser)."""
        return self._uicc_parser._clean_value(value)

    def process(self, df, column):
        """Process column based on detected type.

        Delegates to the appropriate parser via ParserRegistry and
        stores results in instance variables for getter access.
        """
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")

        series = df[column]
        self.column_type = self.detect_column_type(series)

        if self.column_type == 'tnm':
            result = ParserRegistry.parse_column(df, column)
        elif self.column_type == 'categorical' and self._is_uicc_like(series):
            result = self._uicc_parser.parse(df, column)
        else:
            from .parsers.ordinal_parser import OrdinalParser
            result = OrdinalParser().parse(df, column)

        # Store results for getter methods
        self.analysis_columns = result.analysis_columns
        self.violin_columns = result.violin_columns
        self.display_mapping.update(result.display_mapping)
        self.category_mapping = result.category_mapping

        return result.processed_df

    def get_analysis_columns(self) -> list:
        return self.analysis_columns

    def get_violin_columns(self) -> list:
        return self.violin_columns

    def get_column_type(self) -> str:
        return self.column_type

    def get_display_mapping(self) -> dict:
        return self.display_mapping

    def get_column_groups(self) -> dict:
        return {col: col for col in self.analysis_columns}

    def get_category_mapping(self) -> dict:
        return self.category_mapping
