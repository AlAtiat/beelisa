"""TNM staging parser for clinical correlation analysis.

Handles TNM formats: pT3 N1 M0 G2, partial (G2, pT2),
prefixes (p, y, c, u), substages (a, b, c), unknowns (x),
ranges (G1-2, pT2a-3b), and special cases (Mhep -> M1).
"""

import re
import numpy as np
import pandas as pd
from .base import ClinicalParser, ParseResult, sort_key


class TNMParser(ClinicalParser):
    """Parse TNM staging strings into ordinal columns."""

    # Regex patterns for extraction (captures substage letter a-c and ranges)
    PATTERNS = {
        'T_Stage': r'[pyuc]*T(\d+[a-c]?(?:-\d+[a-c]?)?|x)',
        'N_Stage': r'N(\d+[a-c]?(?:-\d+[a-c]?)?|x)',
        'M_Stage': r'M(\d+[a-c]?(?:-\d+[a-c]?)?|x|hep)',
        'Grade': r'G(\d+(?:-\d+)?)',
    }

    _PREFIXES = {'T_Stage': 'T', 'N_Stage': 'N', 'M_Stage': 'M', 'Grade': 'G'}

    @property
    def name(self) -> str:
        return "TNM"

    def can_parse(self, series: pd.Series) -> bool:
        """Detect TNM patterns (>30% of first 50 values match)."""
        sample = series.dropna().head(50).astype(str)
        if len(sample) == 0:
            return False
        tnm_pattern = r'[pyuc]*T\d|N\d|M\d|G\d'
        tnm_matches = sample.str.contains(tnm_pattern, case=False, regex=True).sum()
        return tnm_matches > len(sample) * 0.3

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

    def _clean_stage_value(self, value):
        """Clean a stage string for ranking. Returns NaN for unknowns."""
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

    def parse_tnm_column(self, df: pd.DataFrame, tnm_column: str) -> pd.DataFrame:
        """Extract T, N, M, G components from TNM strings.

        Returns:
            DataFrame with T_Stage, N_Stage, M_Stage, Grade + display columns
        """
        if tnm_column not in df.columns:
            raise ValueError(f"TNM column '{tnm_column}' not found in DataFrame")

        result = df.copy()

        for stage, pattern in self.PATTERNS.items():
            result[stage] = result[tnm_column].apply(
                lambda x: self._extract_component(x, pattern)
            )

        for stage, prefix in self._PREFIXES.items():
            if stage in result.columns:
                result[f'{stage}_display'] = result[stage].apply(
                    lambda x, p=prefix: self._display_value(x, p)
                )

        return result

    def convert_to_ordinal(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert extracted stage strings to integer ranks.

        Sorts unique cleaned values, assigns sequential ranks (1, 2, 3, ...).
        Unknowns (X, Z) become NaN.
        """
        result = df.copy()

        for stage in ['T_Stage', 'N_Stage', 'M_Stage', 'Grade']:
            if stage not in result.columns:
                continue
            cleaned = result[stage].apply(self._clean_stage_value)
            unique_valid = sorted(cleaned.dropna().unique(), key=sort_key)
            rank_map = {val: float(i + 1) for i, val in enumerate(unique_valid)}
            result[f'{stage}_num'] = cleaned.map(rank_map)

        return result

    def process(self, df: pd.DataFrame, tnm_column: str) -> pd.DataFrame:
        """Convenience method to parse and convert in one step."""
        parsed = self.parse_tnm_column(df, tnm_column)
        return self.convert_to_ordinal(parsed)

    def parse(self, df: pd.DataFrame, column: str) -> ParseResult:
        """ClinicalParser interface implementation."""
        result = self.process(df, column)

        num_cols = [c for c in self.get_numeric_columns() if c in result.columns]
        display_cols = [c for c in self.get_display_columns() if c in result.columns]

        display_mapping = {}
        for col in num_cols:
            display_mapping[col] = col.replace('_num', '').replace('_', ' ')

        return ParseResult(
            processed_df=result,
            analysis_columns=num_cols,
            violin_columns=display_cols,
            display_mapping=display_mapping,
            column_groups={col: col for col in num_cols},
        )

    def get_numeric_columns(self) -> list:
        return ['T_Stage_num', 'N_Stage_num', 'M_Stage_num', 'Grade_num']

    def get_stage_columns(self) -> list:
        return ['T_Stage', 'N_Stage', 'M_Stage', 'Grade']

    def get_display_columns(self) -> list:
        return ['T_Stage_display', 'N_Stage_display', 'M_Stage_display', 'Grade_display']
