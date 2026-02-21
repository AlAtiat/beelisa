"""Generic ordinal parser for numeric and categorical clinical columns.

Fallback parser when no specialized parser (TNM, UICC) matches.
"""

import pandas as pd
from .base import ClinicalParser, ParseResult, sort_key


class OrdinalParser(ClinicalParser):
    """Fallback parser for numeric ordinal or categorical string columns."""

    @property
    def name(self) -> str:
        return "Ordinal"

    def can_parse(self, series: pd.Series) -> bool:
        """Always True -- lowest priority fallback."""
        return True

    def parse(self, df: pd.DataFrame, column: str) -> ParseResult:
        """Ordinal-encode the column (numeric pass-through or categorical ranking)."""
        result = df.copy()
        series = result[column]
        display_label = column.replace('_', ' ').title()

        # Numeric with few unique values: use directly as float
        if pd.api.types.is_numeric_dtype(series) and series.nunique() <= 15:
            col_name = f'{column}_ordinal'
            result[col_name] = series.astype(float)
            return ParseResult(
                processed_df=result,
                analysis_columns=[col_name],
                violin_columns=[column],
                display_mapping={col_name: display_label},
                column_groups={col_name: col_name},
            )

        # Categorical: sort unique values and assign integer ranks
        sorted_cats = sorted(series.dropna().unique(), key=sort_key)
        ordinal_map = {cat: float(i + 1) for i, cat in enumerate(sorted_cats)}
        col_name = f'{column}_ordinal'
        result[col_name] = series.map(ordinal_map)

        return ParseResult(
            processed_df=result,
            analysis_columns=[col_name],
            violin_columns=[column],
            display_mapping={col_name: display_label},
            column_groups={col_name: col_name},
            category_mapping=ordinal_map,
        )
