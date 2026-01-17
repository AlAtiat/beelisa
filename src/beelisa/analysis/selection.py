"""Model comparison and selection using AIC/BIC information criteria."""

from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
import numpy as np
from .models.base import FitResult
from .models.registry import ModelRegistry


@dataclass
class ModelComparison:
    """Results of comparing multiple curve fitting models."""

    all_results: List[FitResult]
    comparison_df: pd.DataFrame
    best_model_bic: Optional[str]
    best_model_aic: Optional[str]
    recommended_model: str
    selection_method: str  # "bic" or "aic"


class ModelSelector:
    """
    Model comparison and selection using information criteria.

    Uses AIC (Akaike Information Criterion) or BIC (Bayesian Information Criterion)
    to select the best curve fitting model from multiple candidates.

    For ELISA analysis, BIC is recommended due to small sample sizes (5-8 calibrants).
    """

    def __init__(self, selection_method: str = "bic"):
        """
        Initialize model selector.

        Args:
            selection_method: "bic" (default, recommended for small n) or "aic"
        """
        self.selection_method = selection_method.lower()


    def compare_models(self, x: np.ndarray, y: np.ndarray, models: Optional[List[str]] = None) -> ModelComparison:
        """
        Fit all models and compare using AIC/BIC.
        Record: each Plate standard curve as a case
        Least squares: the method of fitting a regression by minimizing the sum of squared residuals
        Residuals: The difference between the observed values and the fitted values (observed Y - predicted Y)
        Args:
            x: Independent variable (concentrations) -> Feature or Predictor
            y: Dependent variable (OD values) -> Response or Target
            models: List of model names to try (None = all models)
        Returns:
            ModelComparison with results and recommendation
        """
        # Get models to fit
        if models is None:
            model_instances = ModelRegistry.get_all_models()
        else:
            model_instances = [ModelRegistry.get_model(name) for name in models]

        # Fit all models
        results = []
        for model in model_instances:
            fit_result = model.fit(x, y)
            results.append(fit_result)

        # Create comparison DataFrame
        comparison_data = []
        for result in results:
            if result.success:
                # Format parameters for display
                param_strs = []
                for name, val in zip(result.param_names, result.params):
                    param_strs.append(f'{name}={val:.4f}')
                params_display = ', '.join(param_strs)

                comparison_data.append({
                    'Model': result.model_name,
                    'Parameters': params_display,
                    'R²': result.r_squared,
                    'Adj R²': result.adjusted_r_squared,
                    'RMSE': result.rmse,
                    'AIC': result.aic,
                    'BIC': result.bic,
                    'Status': 'Success'
                })
            else:
                comparison_data.append({
                    'Model': result.model_name,
                    'Parameters': 'N/A',
                    'R²': None,
                    'Adj R²': None,
                    'RMSE': None,
                    'AIC': None,
                    'BIC': None,
                    'Status': f'Failed: {result.error}'
                })

        comparison_df = pd.DataFrame(comparison_data)

        # Find best models
        successful_results = [r for r in results if r.success and r.bic is not None]

        if not successful_results:
            return ModelComparison(
                all_results=results,
                comparison_df=comparison_df,
                best_model_bic=None,
                best_model_aic=None,
                recommended_model=None,
                selection_method=self.selection_method
            )

        # Best by BIC (lowest = better)
        best_bic_result = min(successful_results, key=lambda r: r.bic)
        best_aic_result = min(successful_results, key=lambda r: r.aic)

        # Recommended based on selection method
        recommended_result = best_bic_result if self.selection_method == "bic" else best_aic_result

        return ModelComparison(
            all_results=results,
            comparison_df=comparison_df,
            best_model_bic=best_bic_result.model_name,
            best_model_aic=best_aic_result.model_name,
            recommended_model=recommended_result.model_name,
            selection_method=self.selection_method
        )

    def get_best_fit(self, comparison: ModelComparison) -> Optional[FitResult]:
        """
        Get the FitResult for the recommended model.

        Args:
            comparison: ModelComparison object from compare_models()

        Returns:
            FitResult for recommended model or None if no successful fits
        """
        if comparison.recommended_model is None:
            return None

        for result in comparison.all_results:
            if result.model_name == comparison.recommended_model:
                return result

        return None
