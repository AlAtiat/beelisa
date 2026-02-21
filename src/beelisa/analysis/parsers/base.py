"""Base classes and shared utilities for clinical data parsers."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List
import pandas as pd


# Roman numeral mapping
ROMAN_NUMERALS: Dict[str, int] = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
    'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20,
}


def sort_key(value):
    """Unified sort key for clinical values.

    Handles: pure numeric, Roman numerals (with substages like IVA),
    number+suffix (4a, 3b), letter-prefix+number (T3, N2a, G2),
    and natural sort fallback.

    Merges _sort_key (tnm.py) and _smart_sort_key (visualization.py).
    """
    s = str(value).strip()
    # 1. Pure numeric
    try:
        return (0, float(s), '', s)
    except ValueError:
        pass
    upper = s.upper()
    # 2. Pure Roman numeral
    if upper in ROMAN_NUMERALS:
        return (0, ROMAN_NUMERALS[upper], '', s)
    # 3. Roman numeral + letter suffix (IVa, IIIb, IIA)
    m = re.match(r'^([IVXLCDM]+)([A-Za-z])$', upper)
    if m and m.group(1) in ROMAN_NUMERALS:
        return (0, ROMAN_NUMERALS[m.group(1)], m.group(2), s)
    # 4. Number + letter suffix (4a, 3b)
    m = re.match(r'^(\d+)([A-Za-z])$', s)
    if m:
        return (0, float(m.group(1)), m.group(2).upper(), s)
    # 4.5. Letter prefix + number + optional suffix (T3, N2a, M1, G2)
    m = re.match(r'^([A-Za-z]+)(\d+)([A-Za-z]?)$', s)
    if m:
        suffix = m.group(3).upper() if m.group(3) else ''
        return (0.5, m.group(1).lower(), float(m.group(2)), suffix)
    # 5. Natural sort: extract leading number
    m = re.match(r'(\d+)', s)
    if m:
        return (1, int(m.group(1)), '', s.lower())
    # 6. Fallback: alphabetical
    return (2, 0, '', s.lower())


@dataclass
class ParseResult:
    """Result of parsing a clinical column.

    Returned by every ClinicalParser.parse() call.
    Analogous to FitResult from models/base.py.
    """
    processed_df: pd.DataFrame
    analysis_columns: List[str]       # _num / _ordinal columns for Spearman
    violin_columns: List[str]         # display / clean columns for violin x-axis
    display_mapping: Dict[str, str]   # {internal_col: human_label}
    column_groups: Dict[str, str]     # {col: source_group} for cross-corr detection
    category_mapping: Dict = field(default_factory=dict)


class ClinicalParser(ABC):
    """Abstract base class for clinical data parsers.

    Mirrors the CurveModel ABC pattern from models/base.py.
    Each parser handles one type of clinical data format.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Parser identifier (e.g., 'TNM', 'UICC', 'Ordinal')."""
        ...

    @abstractmethod
    def can_parse(self, series: pd.Series) -> bool:
        """Detect whether this parser can handle the given column.

        Args:
            series: Pandas Series to inspect

        Returns:
            True if this parser should handle this data
        """
        ...

    @abstractmethod
    def parse(self, df: pd.DataFrame, column: str) -> ParseResult:
        """Parse the column and produce analysis-ready columns.

        Args:
            df: DataFrame containing the data
            column: Column name to process

        Returns:
            ParseResult with processed data and metadata
        """
        ...
