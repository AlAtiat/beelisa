"""4-Parameter Logistic (4PL) model for ELISA standard curves."""

import numpy as np
from typing import Optional
from .base import CurveModel


class FourPLModel(CurveModel):
    """
    4-Parameter Logistic curve model.

    Equation: y = D + (A - D) / (1 + (x / C)^B)

    Parameters:
        A: Maximum asymptote (OD at concentration → 0)
        B: Hill slope (typically negative for ELISA)
        C: EC50 (inflection point)
        D: Minimum asymptote (OD at concentration → ∞)
    """

    @property
    def name(self) -> str:
        return "4PL"

    @property
    def param_names(self) -> list[str]:
        return ['A', 'B', 'C', 'D']

    @property
    def num_params(self) -> int:
        return 4

    def equation(self, x: np.ndarray, A: float, B: float, C: float, D: float) -> np.ndarray:
        """
        4PL equation: y = D + (A - D) / (1 + (x / C)^B)

        Args:
            x: Concentration values
            A: Maximum asymptote
            B: Hill slope
            C: EC50
            D: Minimum asymptote

        Returns:
            Predicted OD values
        """
        return D + (A - D) / (1 + (x / C) ** B)

    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate smart initial parameter guesses for 4PL.

        Args:
            x: Concentration values
            y: OD values

        Returns:
            (A_init, B_init, C_init, D_init)
        """
        A_init = np.max(y)  # Max OD
        D_init = np.min(y)  # Min OD
        C_init = np.median(x)  # EC50 approximation
        B_init = -1.0  # Typical Hill slope for ELISA

        return (A_init, B_init, C_init, D_init)

    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse 4PL: Convert OD to concentration.

        Formula: concentration = C * ((A - D) / (OD - D) - 1)^(1/B)

        Args:
            y: Measured OD value
            params: [A, B, C, D] fitted parameters

        Returns:
            Predicted concentration or None/inf if outside valid range
        """
        if params is None or len(params) != 4:
            return None

        A, B, C, D = params

        # Check if OD is outside curve range
        if y <= D:
            # OD below minimum asymptote → very high concentration
            return np.inf

        if y >= A:
            # OD above maximum asymptote → very low/zero concentration
            return 0.0

        try:
            # Inverse 4PL formula
            concentration = C * ((A - D) / (y - D) - 1) ** (1 / B)

            # Check for negative concentrations
            if concentration < 0:
                return None

            return concentration

        except (ValueError, ZeroDivisionError, OverflowError):
            return None
