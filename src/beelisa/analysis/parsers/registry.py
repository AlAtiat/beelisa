"""Parser registry -- factory pattern for clinical data parsers.

"""

from typing import Dict, Type, List
import pandas as pd
from .base import ClinicalParser, ParseResult
from .tnm_parser import TNMParser
from .uicc_parser import UICCParser
from .ordinal_parser import OrdinalParser


class ParserRegistry:
    """Factory and registry for clinical data parsers."""

    _parsers: Dict[str, Type[ClinicalParser]] = {}
    _priority: List[str] = []  # ordered by detection priority

    @classmethod
    def register(cls, parser_class: Type[ClinicalParser]):
        """Register a parser class."""
        instance = parser_class()
        cls._parsers[instance.name] = parser_class
        cls._priority.append(instance.name)

    @classmethod
    def get_parser(cls, name: str) -> ClinicalParser:
        """Get parser instance by name."""
        if name not in cls._parsers:
            raise ValueError(
                f"Parser '{name}' not registered. Available: {cls.list_parsers()}"
            )
        return cls._parsers[name]()

    @classmethod
    def list_parsers(cls) -> List[str]:
        """List all registered parser names."""
        return list(cls._parsers.keys())

    @classmethod
    def get_all_parsers(cls) -> List[ClinicalParser]:
        """Get instances of all registered parsers."""
        return [parser_class() for parser_class in cls._parsers.values()]

    @classmethod
    def discover(cls, series: pd.Series) -> ClinicalParser:
        """Auto-detect the best parser for a column.

        Checks parsers in registration order (most specific first).
        """
        for name in cls._priority:
            parser = cls._parsers[name]()
            if parser.can_parse(series):
                return parser
        return OrdinalParser()  # safety fallback

    @classmethod
    def parse_column(cls, df: pd.DataFrame, column: str) -> ParseResult:
        """Convenience: discover parser and parse in one call."""
        parser = cls.discover(df[column])
        return parser.parse(df, column)


# Register parsers in priority order (most specific first)
ParserRegistry.register(TNMParser)
ParserRegistry.register(UICCParser)
ParserRegistry.register(OrdinalParser)  # fallback, always matches
