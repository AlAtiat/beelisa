"""Log-linear model for semi-logarithmic ELISA response."""

import numpy as np
from typing import Optional
from .base import CurveModel


class LogLinearModel(CurveModel):
    """
    Log-linear model (semi-log response).

    Equation: y = m*log(x) + b

    Parameters:
        m: Slope (in log space)
        b: Y-intercept

    Best for: Concentration ranges spanning multiple orders of magnitude
    """

    @property
    def name(self) -> str:
        return "Log-Linear"

    @property
    def param_names(self) -> list[str]:
        return ['m', 'b']

    @property
    def num_params(self) -> int:
        return 2

    def equation(self, x: np.ndarray, m: float, b: float) -> np.ndarray:
        """
        Log-linear equation: y = m*log(x) + b

        Args:
            x: Concentration values (must be > 0)
            m: Slope in log space
            b: Y-intercept

        Returns:
            Predicted OD values
        """
        # Avoid log of zero or negative values
        x_safe = np.maximum(x, 1e-10)
        return m * np.log(x_safe) + b

    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate initial parameter guesses for log-linear regression.

        Args:
            x: Concentration values
            y: OD values

        Returns:
            (m_init, b_init)
        """
        # Transform to log space
        x_log = np.log(np.maximum(x, 1e-10))
        y_mean = np.mean(y)
        x_log_mean = np.mean(x_log)

        # Simple linear regression in log space
        numerator = np.sum((x_log - x_log_mean) * (y - y_mean))
        denominator = np.sum((x_log - x_log_mean) ** 2)

        if denominator != 0:
            m_init = numerator / denominator
        else:
            m_init = 0.0

        b_init = y_mean - m_init * x_log_mean

        return (m_init, b_init)

    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse log-linear: Convert OD to concentration.

        Formula: x = exp((y - b) / m)

        Args:
            y: Measured OD value
            params: [m, b] fitted parameters

        Returns:
            Predicted concentration or None if inversion fails
        """
        if params is None or len(params) != 2:
            return None

        m, b = params

        if m == 0:
            return None  # Slope is zero, can't invert

        try:
            concentration = np.exp((y - b) / m)

            # Check for negative concentrations (shouldn't happen with exp)
            if concentration < 0:
                return None

            return concentration

        except (ValueError, OverflowError):
            return None
