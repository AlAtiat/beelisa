"""Linear regression model for narrow concentration ranges."""

import numpy as np
from typing import Optional
from .base import CurveModel


class LinearModel(CurveModel):
    """
    Linear regression model.

    Equation: y = m*x + b

    Parameters:
        m: Slope
        b: Y-intercept

    Best for: Narrow concentration ranges where response is approximately linear
    """

    @property
    def name(self) -> str:
        return "Linear"

    @property
    def param_names(self) -> list[str]:
        return ['m', 'b']

    @property
    def num_params(self) -> int:
        return 2

    def equation(self, x: np.ndarray, m: float, b: float) -> np.ndarray:
        """
        Linear equation: y = m*x + b

        Args:
            x: Concentration values
            m: Slope
            b: Y-intercept

        Returns:
            Predicted OD values
        """
        return m * x + b

    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate initial parameter guesses using simple linear regression.

        Args:
            x: Concentration values
            y: OD values

        Returns:
            (m_init, b_init)
        """
        # Simple linear regression for initial guess
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        # Calculate slope
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator != 0:
            m_init = numerator / denominator
        else:
            m_init = 0.0

        b_init = y_mean - m_init * x_mean

        return (m_init, b_init)

    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse linear: Convert OD to concentration.

        Formula: x = (y - b) / m

        Args:
            y: Measured OD value
            params: [m, b] fitted parameters

        Returns:
            Predicted concentration or None if slope is zero
        """
        if params is None or len(params) != 2:
            return None

        m, b = params

        if m == 0:
            return None  # Slope is zero, can't invert

        concentration = (y - b) / m

        # Check for negative concentrations
        if concentration < 0:
            return None

        return concentration
