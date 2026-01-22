"""Base classes for curve fitting models with AIC/BIC model selection."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np


# more detail information about each model for INFO
MODEL_INFO = {
    "4PL": {
        "full_name": "4-Parameter Logistic",
        "equation": "y = D + (A-D) / (1 + (x/C)^B)",
        "description": "The 4PL model assumes the curve is symmetrical around the inflection point.",
        "literature": "Gottschalk & Dunn, J Immunol Methods (2005)",
        "params": {"A": "Max asymptote (high OD)", "B": "Hill slope (steepness)", "C": "EC50 (inflection)", "D": "Min asymptote (low OD)"}
    },
    "5PL": {
        "full_name": "5-Parameter Logistic",
        "equation": "y = D + (A-D) / (1 + (x/C)^B)^M",
        "description": "Asymmetric sigmoidal curve. Adds asymmetry parameter M for curves with unequal upper/lower shoulders.",
        "literature": "Gottschalk & Dunn, J Immunol Methods (2005)",
        "params": {"A": "Max asymptote", "B": "Hill slope", "C": "EC50", "D": "Min asymptote", "M": "Asymmetry factor"}
    },
    "Linear": {
        "full_name": "Linear",
        "equation": "y = mx + b",
        "description": "Linear calibration model valid only over narrow concentration ranges with proportional response.",
        "literature": "Harris, Quantitative Chemical Analysis (2010)",
        "params": {"m": "Slope (sensitivity)", "b": "Y-intercept (background)"}
    },
    "Log-Linear": {
        "full_name": "Log-Linear",
        "equation": "y = m*log(x) + b",
        "description": "Linear relationship in logarithmic concentration space, suitable for wide dynamic ranges without saturation modeling.",
        "literature": "Standard calibration method for wide-range assays",
        "params": {"m": "Slope in log-space", "b": "Y-intercept"}
    },
    "Exponential": {
        "full_name": "Exponential",
        "equation": "y = a*exp(b*x) + c",
        "description": "Exponential growth or decay model describing first-order kinetic behavior.",
        "literature": "Motulsky & Christopoulos (2004). Fitting Models to Biological Data.",
        "params": {"a": "Amplitude", "b": "Rate constant", "c": "Offset/baseline"}
    }
}

# Information about model selection criteria
SELECTION_INFO = {
    "bic": {
        "name": "BIC (Bayesian Information Criterion)",
        "formula": "BIC = n*ln(RSS/n) + k*ln(n)",
        "description": "Model selection should prefer simpler models unless the data provide sufficient evidence to support higher dimensionality (Penalizes complexity). Gideon Schwarz (1978)",
        "why": "BIC applies a sample-size dependent penalty on model dimensionality derived from Bayesian model selection theory, preventing systematic overfitting inherent to maximum likelihood estimation. Schwarz, G. (1978), Burnham, K. P., & Anderson, D. R. (2002). Model Selection and Multimodel Inference."
    },
    "aic": {
        "name": "AIC (Akaike Information Criterion)",
        "formula": "AIC = n*ln(RSS/n) + 2k",
        "description": "Information-theoretic model selection criterion that balances goodness of fit with model complexity by penalizing the number of parameters. Hirotugu Akaike (1974) Akaike, H. A new look at the statistical model identification",
        "why": "Derived to minimize expected information loss between the fitted model and the true data-generating process, AIC favors models with strong predictive performance and may retain additional parameters when they improve approximation accuracy. Akaike, H. 1974."
    }
}


@dataclass
class FitResult:
    """Container for curve fitting results with comprehensive diagnostics."""

    success: bool
    model_name: str
    params: Optional[np.ndarray]
    param_names: list[str]
    fitted_values: Optional[np.ndarray]
    residuals: Optional[np.ndarray]

    # Goodness of fit metrics
    r_squared: Optional[float]
    adjusted_r_squared: Optional[float]
    rss: Optional[float]  # Residual sum of squares
    aic: Optional[float]  # Akaike Information Criterion
    bic: Optional[float]  # Bayesian Information Criterion
    rmse: Optional[float]  # Root mean squared error

    # Error info
    error: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary for storage/serialization."""
        return {
            'success': self.success,
            'model_name': self.model_name,
            'params': self.params.tolist() if self.params is not None else None, # because parms is a array thats why converted to list
            'param_names': self.param_names,
            'r_squared': self.r_squared,
            'adjusted_r_squared': self.adjusted_r_squared,
            'rss': self.rss,
            'aic': self.aic,
            'bic': self.bic,
            'rmse': self.rmse,
            'error': self.error
        }


class CurveModel(ABC):
    """Abstract base class for all curve fitting models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Model name identifier.
        A string ID for reporting and selection (“4PL”, “Linear”, …)
        """
        pass

    @property
    @abstractmethod
    def param_names(self) -> list[str]:
        """Parameter names for this model.
        Names for parameters
        """
        pass

    @property
    @abstractmethod
    def num_params(self) -> int:
        """Number of parameters (k) for AIC/BIC calculation."""
        pass

    @abstractmethod
    def equation(self, x: np.ndarray, *params) -> np.ndarray:
        """
        Forward equation: predict y from x given parameters.
        Scipy curve_fit Assumes ydata = f(xdata, *params) + eps
        Args:
            x: Independent variable (concentration)
            *params: Model parameters

        Returns:
            Predicted (Y-hat) values (OD)
        """
        pass

    @abstractmethod
    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate initial parameter guesses.

        Args:
            x: Independent variable (concentration)
            y: Dependent variable (OD)

        Returns:
            Tuple of initial parameter values
        """
        pass

    @abstractmethod
    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse equation: predict x from y given parameters.

        Args:
            y: Measured OD sample value
            params: Fitted parameters

        Returns:
            Predicted concentration (or None if inversion fails)
        """
        pass

    @property
    def bounds(self) -> tuple:
        """
        Optional parameter bounds for constrained fitting.

        Returns:
            (lower_bounds, upper_bounds) or (-inf, inf) for unconstrained
        """
        return (-np.inf, np.inf)

    def fit(self, x: np.ndarray, y: np.ndarray) -> FitResult:
        """
        Fit the model to data with comprehensive diagnostics.

        Args:
            x: Independent variable (concentrations)
            y: Dependent variable (OD values) z.B for Linear model Yi = b0+ b1Xi+ ei

        Returns:
            FitResult with metrics and diagnostics
        """
        from scipy.optimize import curve_fit


        # Input validation
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)

        if len(x) != len(y):
            return FitResult(
                success=False,
                model_name=self.name,
                params=None,
                param_names=self.param_names,
                fitted_values=None,
                residuals=None,
                r_squared=None,
                adjusted_r_squared=None,
                rss=None,
                aic=None,
                bic=None,
                rmse=None,
                error='for each calibrant concetration x must be equal number of calibrant od values'
            )

        # Remove NaN values
        valid_mask = ~(np.isnan(x) | np.isnan(y))
        x_clean = x[valid_mask]
        y_clean = y[valid_mask]
        n = len(x_clean)

        #  n = k causes false results so with 5 calibrants we cant use 5PL 
        if n <= self.num_params: # as a Degrees of Freedom n must be greater than k
            return FitResult(
                success=False,
                model_name=self.name,
                params=None,
                param_names=self.param_names,
                fitted_values=None,
                residuals=None,
                r_squared=None,
                adjusted_r_squared=None,
                rss=None,
                aic=None,
                bic=None,
                rmse=None,
                error=(
                    f"Insufficient calibration points for model fitting (n ≤ k). "
                    f"Number of model parameters (k) = {self.num_params}, "
                    f"number of calibrants (n) = {n}. "
                )            
            )

        try:
            # Get initial guess
            p0 = self.initial_guess(x_clean, y_clean)

            # Fit curve
            params, covariance = curve_fit(
                self.equation, # for each model such as 4PL or linear
                x_clean,
                y_clean,
                p0=p0,
                bounds=self.bounds,
                maxfev=20000,
                method='trf' # Trust Region Reflective handle the "Reflective" boundaries 
            )

            # Calculate fitted values for linear model Yi(hat) = b0(hat) + b1(hat)Xi and residuals ei(hat)= Yi(hat) − Y(hat)
            fitted_values = self.equation(x_clean, *params) # Yi(hat)
            residuals = y_clean - fitted_values # ei(hat)
            
            if not (np.all(np.isfinite(params)) and np.all(np.isfinite(fitted_values))):
                raise ValueError("Non-finite fit result")
            
            # Calculate metrics
            rss = np.sum(residuals ** 2) # Residual sum of squares
            tss = np.sum((y_clean - np.mean(y_clean)) ** 2) # Total Sum of Squares

            # R² and adjusted R²
            r_squared = 1 - (rss / tss) if tss != 0 else 0
            k = self.num_params
            adjusted_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k - 1) if n > k + 1 else None # Penalize for using too many k 

            # AIC and BIC
            # AIC = n*ln(RSS/n) + 2k
            # BIC = n*ln(RSS/n) + k*ln(n)
            if rss > 0 and n > 0:
                aic = n * np.log(rss / n) + 2 * k
                bic = n * np.log(rss / n) + k * np.log(n)
            else:
                aic = None
                bic = None

            # RMSE The square root of the average squared error of the regression (to compare regression models).
            n_minus_k = n - k
            rmse = np.sqrt(rss / n_minus_k) # Root mean squared error

            return FitResult(
                success=True,
                model_name=self.name,
                params=params,
                param_names=self.param_names,
                fitted_values=fitted_values,
                residuals=residuals,
                r_squared=r_squared,
                adjusted_r_squared=adjusted_r_squared,
                rss=rss,
                aic=aic,
                bic=bic,
                rmse=rmse,
                error=None
            )

        except Exception as e:
            return FitResult(
                success=False,
                model_name=self.name,
                params=None,
                param_names=self.param_names,
                fitted_values=None,
                residuals=None,
                r_squared=None,
                adjusted_r_squared=None,
                rss=None,
                aic=None,
                bic=None,
                rmse=None,
                error=f'{self.name} fitting failed: {str(e)}'
            )
