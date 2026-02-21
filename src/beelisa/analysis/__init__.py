"""ELISA analysis module with multi-model curve fitting and AIC/BIC selection."""

from .analysis_engine import AnalysisEngine
from .selection import ModelSelector, ModelComparison
from .visualization import ELISAVisualizer
from .tnm import TNMProcessor, ClinicalDataProcessor
from .clinical import build_trend_jobs, prepare_trend_df, process_clinical_columns
from .statistics import spearman_correlation, benjamini_hochberg, lowess_with_band
from .parsers import (
    ClinicalParser,
    ParseResult,
    ParserRegistry,
    TNMParser,
    UICCParser,
    OrdinalParser,
)
from .models import (
    CurveModel,
    FitResult,
    LinearModel,
    LogLinearModel,
    ExponentialModel,
    # Polynomial2Model,
    # Polynomial3Model,
    FourPLModel,
    FivePLModel,
    ModelRegistry,
)

__all__ = [
    "AnalysisEngine",
    "ModelSelector",
    "ModelComparison",
    "ELISAVisualizer",
    "ELISAPCAAnalyzer",
    "TNMProcessor",
    "ClinicalDataProcessor",
    # Parsers
    "ClinicalParser",
    "ParseResult",
    "ParserRegistry",
    "TNMParser",
    "UICCParser",
    "OrdinalParser",
    # Statistics
    "spearman_correlation",
    "benjamini_hochberg",
    "lowess_with_band",
    # Clinical
    "build_trend_jobs",
    "prepare_trend_df",
    "process_clinical_columns",
    # Models
    "CurveModel",
    "FitResult",
    "LinearModel",
    "LogLinearModel",
    "ExponentialModel",
    # "Polynomial2Model",
    # "Polynomial3Model",
    "FourPLModel",
    "FivePLModel",
    "ModelRegistry",
]
