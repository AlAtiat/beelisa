"""TNM Clinical Staging Processor for correlating staging with biomarkers."""
import re
import numpy as np
import pandas as pd

# Roman numeral mapping for ordinal encoding
_ROMAN = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
    'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20,
}


def _sort_key(value):
    """Sort key handling numeric, Roman numeral (with substages), and natural sort."""
    s = str(value).strip()
    # 1. Pure numeric
    try:
        return (0, float(s), '', s)
    except ValueError:
        pass
    upper = s.upper()
    # 2. Pure Roman numeral
    if upper in _ROMAN:
        return (0, _ROMAN[upper], '', s)
    # 3. Roman numeral + letter suffix (IVa, IIIb, IIA)
    m = re.match(r'^([IVXLCDM]+)([A-Za-z])$', upper)
    if m and m.group(1) in _ROMAN:
        return (0, _ROMAN[m.group(1)], m.group(2), s)
    # 4. Number + letter suffix (4a, 3b)
    m = re.match(r'^(\d+)([A-Za-z])$', s)
    if m:
        return (0, float(m.group(1)), m.group(2).upper(), s)
    # 5. Natural sort: extract leading number
    m = re.match(r'(\d+)', s)
    if m:
        return (1, int(m.group(1)), '', s.lower())
    # 6. Fallback: alphabetical
    return (2, 0, '', s.lower())


class TNMProcessor:
    """Parse TNM staging strings and prepare for correlation analysis.

    Handles various TNM formats:
    - Full: pT3 N1 M0 G2
    - Partial: G2, pT2, pT3 N1
    - Prefixes: p (pathological), y (post-treatment), c (clinical), u (ultrasound)
    - Suffixes: a, b, c after T stage (e.g., pT2a)
    - Unknown: x (e.g., Mx, Nx)
    - Ranges: G1-2, pT2-3 (takes higher value for clinical safety)
    """

    # Regex patterns for extraction (captures optional substage letter a-c and ranges)
    PATTERNS = {
        'T_Stage': r'[pyuc]*T(\d+[a-c]?(?:-\d+[a-c]?)?|x)',
        'N_Stage': r'N(\d+[a-c]?(?:-\d+[a-c]?)?|x)',
        'M_Stage': r'M(\d+[a-c]?(?:-\d+[a-c]?)?|x|hep)',
        'Grade': r'G(\d+(?:-\d+)?)',
    }

    _PREFIXES = {'T_Stage': 'T', 'N_Stage': 'N', 'M_Stage': 'M', 'Grade': 'G'}

    def _substage_value(self, s):
        """Numeric value of a stage token for comparison: '3B' -> 3.2, '2' -> 2.0."""
        s = s.upper()
        m = re.match(r'^(\d+)([A-C])?$', s)
        if m:
            base = float(m.group(1))
            if m.group(2):
                base += (ord(m.group(2)) - ord('A') + 1) * 0.1
            return base
        return 0.0

    def _extract_component(self, text: str, pattern: str) -> str:
        """Extract single component using regex pattern.

        Args:
            text: TNM string to parse
            pattern: Regex pattern with capture group

        Returns:
            Extracted value (digit+optional suffix or 'X') or None if not found
        """
        if pd.isna(text) or not isinstance(text, str):
            return None

        text = text.strip()
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = match.group(1).upper()
            # Handle ranges like "2A-3B" -> take higher endpoint
            if '-' in value:
                parts = value.split('-')
                value = max(parts, key=lambda p: self._substage_value(p))
            return value

        return None

    def parse_tnm_column(self, df: pd.DataFrame, tnm_column: str) -> pd.DataFrame:
        """Extract T, N, M, G components from TNM strings.

        Args:
            df: DataFrame containing TNM data
            tnm_column: Column name with TNM strings

        Returns:
            DataFrame with new columns: T_Stage, N_Stage, M_Stage, Grade (string values)
        """
        if tnm_column not in df.columns:
            raise ValueError(f"TNM column '{tnm_column}' not found in DataFrame")

        result = df.copy()

        for stage, pattern in self.PATTERNS.items():
            result[stage] = result[tnm_column].apply(
                lambda x: self._extract_component(x, pattern)
            )

        # Create display columns with clinical prefix (T3, N1, M0, G2)
        for stage, prefix in self._PREFIXES.items():
            if stage in result.columns:
                result[f'{stage}_display'] = result[stage].apply(
                    lambda x, p=prefix: self._display_value(x, p)
                )

        return result

    def _clean_stage_value(self, value):
        """Clean a stage string for ranking. Returns NaN for unknowns.

        - None/NaN -> NaN
        - X, Z, '' -> NaN
        - HEP -> '1' (hepatic metastasis = M1)
        - Otherwise -> keep uppercase string
        """
        if pd.isna(value) or value is None:
            return np.nan
        s = str(value).upper().strip()
        if s in ('X', 'Z', ''):
            return np.nan
        if s == 'HEP':
            return '1'
        return s

    def _display_value(self, value, prefix):
        """Create clinical display label: prefix + value, NaN for unknowns."""
        if pd.isna(value) or value is None:
            return np.nan
        s = str(value).upper().strip()
        if s in ('X', 'Z', ''):
            return np.nan
        if s == 'HEP':
            return f'{prefix}1'
        return f'{prefix}{value}'

    def convert_to_ordinal(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert extracted stage strings to integer ranks.

        Sorts unique cleaned values per column using _sort_key, then assigns
        sequential integer ranks (1, 2, 3, ...). Unknowns (X, Z) become NaN.

        Args:
            df: DataFrame with T_Stage, N_Stage, M_Stage, Grade columns

        Returns:
            DataFrame with numeric columns: T_Stage_num, N_Stage_num, M_Stage_num, Grade_num
        """
        result = df.copy()

        for stage in ['T_Stage', 'N_Stage', 'M_Stage', 'Grade']:
            if stage not in result.columns:
                continue
            cleaned = result[stage].apply(self._clean_stage_value)
            unique_valid = sorted(cleaned.dropna().unique(), key=_sort_key)
            rank_map = {val: float(i + 1) for i, val in enumerate(unique_valid)}
            result[f'{stage}_num'] = cleaned.map(rank_map)

        return result

    def get_numeric_columns(self) -> list:
        """Return list of numeric stage column names for correlation.

        Returns:
            List of column names: ['T_Stage_num', 'N_Stage_num', 'M_Stage_num', 'Grade_num']
        """
        return ['T_Stage_num', 'N_Stage_num', 'M_Stage_num', 'Grade_num']

    def get_stage_columns(self) -> list:
        """Return list of string stage column names.

        Returns:
            List of column names: ['T_Stage', 'N_Stage', 'M_Stage', 'Grade']
        """
        return ['T_Stage', 'N_Stage', 'M_Stage', 'Grade']

    def get_display_columns(self) -> list:
        """Return list of display column names (with clinical prefix).

        Returns:
            List: ['T_Stage_display', 'N_Stage_display', 'M_Stage_display', 'Grade_display']
        """
        return ['T_Stage_display', 'N_Stage_display', 'M_Stage_display', 'Grade_display']

    def process(self, df: pd.DataFrame, tnm_column: str) -> pd.DataFrame:
        """Convenience method to parse and convert in one step.

        Args:
            df: DataFrame containing TNM data
            tnm_column: Column name with TNM strings

        Returns:
            DataFrame with both string and numeric stage columns
        """
        parsed = self.parse_tnm_column(df, tnm_column)
        return self.convert_to_ordinal(parsed)


class ClinicalDataProcessor:
    """Process any categorical/ordinal column for clinical analysis.

    Supports:
    - Direct numeric columns (1, 2, 3, 4) → use directly
    - Categorical strings ("Low", "Medium", "High") → auto-encoded to numeric
    - TNM staging strings (pT3 N1 M0 G2) → parsed via TNMProcessor
    """

    def __init__(self):
        self.tnm_processor = TNMProcessor()
        self.column_type = None  # 'numeric', 'categorical', 'tnm'
        self.analysis_columns = []  # _num columns for correlation (numeric)
        self.violin_columns = []  # Original columns for violin x-axis (shows actual values)
        self.category_mapping = {}  # For categorical: {original_value: numeric}
        self.display_mapping = {}  # {column_name: display_label} for correlation axes

    def detect_column_type(self, series: pd.Series) -> str:
        """Detect if column is numeric, categorical, or TNM-formatted.

        Args:
            series: Pandas Series to analyze

        Returns:
            'tnm', 'numeric', or 'categorical'
        """
        # Check for TNM patterns in string data
        sample = series.dropna().head(50).astype(str)
        if len(sample) == 0:
            return 'categorical'

        tnm_pattern = r'[pyuc]*T\d|N\d|M\d|G\d'
        tnm_matches = sample.str.contains(tnm_pattern, case=False, regex=True).sum()
        if tnm_matches > len(sample) * 0.3:  # >30% have TNM patterns
            return 'tnm'

        # Check if numeric with few unique values (ordinal)
        if pd.api.types.is_numeric_dtype(series):
            n_unique = series.nunique()
            if n_unique <= 15:  # Reasonable number of categories
                return 'numeric'

        # Otherwise treat as categorical strings
        return 'categorical'

    def _is_uicc_like(self, series: pd.Series) -> bool:
        """Detect if column values are UICC-like (Roman numerals with optional suffix)."""
        sample = series.dropna().astype(str).str.strip().str.upper()
        if len(sample) < 3:
            return False
        count = 0
        for v in sample:
            v_clean = v.replace(' ', '')
            if v_clean in _ROMAN:
                count += 1
                continue
            m = re.match(r'^([IVXLCDM]+)[A-Z]$', v_clean)
            if m and m.group(1) in _ROMAN:
                count += 1
        return count > len(sample) * 0.5

    def _clean_uicc_value(self, value):
        """Clean a UICC value: valid Roman numeral (+suffix) -> keep, else NaN."""
        if pd.isna(value):
            return np.nan
        s = str(value).strip()
        upper = s.upper().replace(' ', '')
        if upper in ('', 'INOP', 'INOP.', 'NA', 'N/A', 'UNKNOWN'):
            return np.nan
        if upper in _ROMAN:
            return upper
        m = re.match(r'^([IVXLCDM]+)([A-Z])$', upper)
        if m and m.group(1) in _ROMAN:
            return upper
        return np.nan

    def _process_uicc(self, result, column, series):
        """Process UICC column: clean, rank-encode, create display column."""
        clean_col = f'{column}_clean'
        ord_col = f'{column}_ordinal'

        result[clean_col] = series.apply(self._clean_uicc_value)

        sorted_cats = sorted(result[clean_col].dropna().unique(), key=_sort_key)
        rank_map = {cat: float(i + 1) for i, cat in enumerate(sorted_cats)}
        result[ord_col] = result[clean_col].map(rank_map)

        self.analysis_columns = [ord_col]
        self.violin_columns = [clean_col]
        self.category_mapping = rank_map
        self.display_mapping[ord_col] = column.replace('_', ' ').title()
        return result

    def process(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Process column based on detected type.

        Args:
            df: DataFrame containing the data
            column: Column name to process

        Returns:
            DataFrame with numeric column(s) for analysis
        """
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")

        result = df.copy()
        series = result[column]
        self.column_type = self.detect_column_type(series)

        if self.column_type == 'tnm':
            # Use existing TNMProcessor for TNM strings
            result = self.tnm_processor.process(result, column)
            self.analysis_columns = self.tnm_processor.get_numeric_columns()
            self.violin_columns = self.tnm_processor.get_display_columns()
            # Display mapping: 'T_Stage_num' -> 'T Stage', etc.
            for col in self.analysis_columns:
                self.display_mapping[col] = col.replace('_num', '').replace('_', ' ')

        elif self.column_type == 'numeric':
            # Use column directly as ordinal (already numeric)
            col_name = f'{column}_ordinal'
            result[col_name] = series.astype(float)
            self.analysis_columns = [col_name]
            self.violin_columns = [column]
            self.display_mapping[col_name] = column.replace('_', ' ').title()

        else:  # categorical
            # Check if UICC-like (Roman numeral staging)
            if self._is_uicc_like(series):
                return self._process_uicc(result, column, series)

            # Ordinal encoding: sort categories, assign positional ranks
            sorted_cats = sorted(series.dropna().unique(), key=_sort_key)
            ordinal_map = {cat: float(i + 1) for i, cat in enumerate(sorted_cats)}
            col_name = f'{column}_ordinal'
            result[col_name] = series.map(ordinal_map)
            self.analysis_columns = [col_name]
            self.violin_columns = [column]  # Keep original labels for violin x-axis
            self.category_mapping = ordinal_map
            self.display_mapping[col_name] = column.replace('_', ' ').title()

        return result

    def get_analysis_columns(self) -> list:
        """Return list of numeric columns for correlation (Spearman needs numeric).

        Returns:
            List of _num column names (1 for numeric/categorical, 4 for TNM)
        """
        return self.analysis_columns

    def get_violin_columns(self) -> list:
        """Return columns for violin plot x-axis (shows clinical labels).

        For categorical/numeric: returns original column (shows "Low", "Med", "High" or 1, 2, 3).
        For TNM: returns display columns (T3, T2A, N1, M0, G2).
        For UICC: returns cleaned column (I, IIA, III, IVA).

        Returns:
            List of column names for violin grouping
        """
        return self.violin_columns

    def get_column_type(self) -> str:
        """Return detected column type.

        Returns:
            'tnm', 'numeric', or 'categorical'
        """
        return self.column_type

    def get_display_mapping(self) -> dict:
        """Return column name to display label mapping for correlation axes.

        Returns:
            Dict mapping internal column names to human-readable labels
        """
        return self.display_mapping

    def get_column_groups(self) -> dict:
        """Return {col: source_group} for cross-correlation detection.

        Each column is its own independent group (ordinal encoding produces
        one column per variable, so no one-hot cross-correlation to skip).

        Returns:
            Dict mapping column names to their source group identifier
        """
        return {col: col for col in self.analysis_columns}

    def get_category_mapping(self) -> dict:
        """Return category to numeric mapping (for categorical type).

        Returns:
            Dict mapping original values to numeric codes
        """
        return self.category_mapping
