"""Exponential model for ELISA decay/growth curves."""

import numpy as np
from typing import Optional
from .base import CurveModel


class ExponentialModel(CurveModel):
    """
    Exponential model.

    Equation: y = a*exp(b*x) + c

    Parameters:
        a: Amplitude
        b: Decay/growth rate
        c: Asymptote

    Best for: Exponential decay or growth patterns
    """

    @property
    def name(self) -> str:
        return "Exponential"

    @property
    def param_names(self) -> list[str]:
        return ['a', 'b', 'c']

    @property
    def num_params(self) -> int:
        return 3

    def equation(self, x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
        """
        Exponential equation: y = a*exp(b*x) + c

        Args:
            x: Concentration values
            a: Amplitude
            b: Decay/growth rate
            c: Asymptote

        Returns:
            Predicted OD values
        """
        return a * np.exp(b * x) + c

    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate initial parameter guesses for exponential fit.

        Args:
            x: Concentration values
            y: OD values

        Returns:
            (a_init, b_init, c_init)
        """
        # Estimate asymptote from min/max
        c_init = np.min(y)

        # Estimate amplitude
        a_init = np.max(y) - c_init

        # Estimate decay rate (negative for decay, positive for growth)
        # Use log-linear approximation
        y_shifted = y - c_init
        y_safe = np.maximum(y_shifted, 1e-10)

        # Simple linear fit in log space
        log_y = np.log(y_safe)
        x_mean = np.mean(x)
        log_y_mean = np.mean(log_y)

        numerator = np.sum((x - x_mean) * (log_y - log_y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator != 0:
            b_init = numerator / denominator
        else:
            b_init = -0.01  # Small negative decay

        return (a_init, b_init, c_init)

    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse exponential: Convert OD to concentration.

        Formula: x = ln((y - c) / a) / b

        Args:
            y: Measured OD value
            params: [a, b, c] fitted parameters

        Returns:
            Predicted concentration or None if inversion fails
        """
        if params is None or len(params) != 3:
            return None

        a, b, c = params

        if b == 0 or a == 0:
            return None  # Can't invert

        try:
            # Solve: y = a*exp(b*x) + c
            # (y - c) / a = exp(b*x)
            # ln((y - c) / a) = b*x
            # x = ln((y - c) / a) / b

            ratio = (y - c) / a

            if ratio <= 0:
                return None  # Can't take log of negative/zero

            concentration = np.log(ratio) / b

            # Check for negative concentrations
            if concentration < 0:
                return None

            return concentration

        except (ValueError, OverflowError):
            return None
