"""ELISA analysis module with multi-model curve fitting and AIC/BIC selection."""

from .analysis_engine import AnalysisEngine
from .selection import ModelSelector, ModelComparison
from .visualization import ELISAVisualizer
from .models import (
    CurveModel,
    FitResult,
    LinearModel,
    LogLinearModel,
    ModelRegistry,
)

__all__ = [
    "AnalysisEngine",
    "ModelSelector",
    "ModelComparison",
    "ELISAVisualizer",
    "ELISAPCAAnalyzer",
    "CurveModel",
    "FitResult",
    "LinearModel",
    "LogLinearModel",
    "ModelRegistry",
]
