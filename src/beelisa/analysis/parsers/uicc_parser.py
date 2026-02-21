"""UICC staging parser (Roman numeral stages like I, IIA, IIIB, IVA)."""

import re
import numpy as np
import pandas as pd
from .base import ClinicalParser, ParseResult, ROMAN_NUMERALS, sort_key


class UICCParser(ClinicalParser):
    """Parse UICC staging columns (Roman numerals with optional suffix)."""

    @property
    def name(self) -> str:
        return "UICC"

    def can_parse(self, series: pd.Series) -> bool:
        """Detect UICC-like values (>50% Roman numerals with optional suffix)."""
        sample = series.dropna().astype(str).str.strip().str.upper()
        if len(sample) < 3:
            return False
        count = 0
        for v in sample:
            v_clean = v.replace(' ', '')
            if v_clean in ROMAN_NUMERALS:
                count += 1
                continue
            m = re.match(r'^([IVXLCDM]+)[A-Z]$', v_clean)
            if m and m.group(1) in ROMAN_NUMERALS:
                count += 1
        return count > len(sample) * 0.5

    def _clean_value(self, value):
        """Clean a UICC value: valid Roman numeral (+suffix) -> keep, else NaN."""
        if pd.isna(value):
            return np.nan
        s = str(value).strip()
        upper = s.upper().replace(' ', '')
        if upper in ('', 'INOP', 'INOP.', 'NA', 'N/A', 'UNKNOWN'):
            return np.nan
        if upper in ROMAN_NUMERALS:
            return upper
        m = re.match(r'^([IVXLCDM]+)([A-Z])$', upper)
        if m and m.group(1) in ROMAN_NUMERALS:
            return upper
        return np.nan

    def parse(self, df: pd.DataFrame, column: str) -> ParseResult:
        """Parse UICC column: clean, rank-encode, create display column."""
        result = df.copy()
        series = result[column]
        clean_col = f'{column}_clean'
        ord_col = f'{column}_ordinal'

        result[clean_col] = series.apply(self._clean_value)

        sorted_cats = sorted(result[clean_col].dropna().unique(), key=sort_key)
        rank_map = {cat: float(i + 1) for i, cat in enumerate(sorted_cats)}
        result[ord_col] = result[clean_col].map(rank_map)

        display_label = column.replace('_', ' ').title()

        return ParseResult(
            processed_df=result,
            analysis_columns=[ord_col],
            violin_columns=[clean_col],
            display_mapping={ord_col: display_label},
            column_groups={ord_col: ord_col},
            category_mapping=rank_map,
        )
