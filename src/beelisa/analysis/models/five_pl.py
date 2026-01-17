"""5-Parameter Logistic (5PL) model for asymmetric ELISA curves."""

import numpy as np
from typing import Optional
from .base import CurveModel


class FivePLModel(CurveModel):
    """
    5-Parameter Logistic curve model with asymmetry.

    Equation: y = D + (A - D) / ((1 + (x / C)^B)^M)

    Parameters:
        A: Maximum asymptote
        B: Hill slope
        C: EC50 (inflection point)
        D: Minimum asymptote
        M: Asymmetry parameter (M=1 reduces to 4PL)
    """

    @property
    def name(self) -> str:
        return "5PL"

    @property
    def param_names(self) -> list[str]:
        return ['A', 'B', 'C', 'D', 'M']

    @property
    def num_params(self) -> int:
        return 5

    def equation(self, x: np.ndarray, A: float, B: float, C: float, D: float, M: float) -> np.ndarray:
        """
        5PL equation with asymmetry parameter.

        Args:
            x: Concentration values
            A: Maximum asymptote
            B: Hill slope
            C: EC50
            D: Minimum asymptote
            M: Asymmetry parameter

        Returns:
            Predicted OD values
        """
        # Prevent division by zero and ensure positive base
        C = max(C, 1e-10)
        x = np.maximum(x, 1e-10)

        # Calculate with safeguards against numerical issues
        base = 1 + (x / C) ** B
        # Ensure base is positive before raising to power M
        base = np.maximum(base, 1e-10)

        return D + (A - D) / (base ** M)

    @property
    def bounds(self) -> tuple:
        """
        Parameter bounds for 5PL to ensure numerical stability.

        Returns:
            (lower_bounds, upper_bounds) tuples
        """
        # Bounds: [A, B, C, D, M]
        # A (max): 0 to inf
        # B (slope): -inf to inf
        # C (EC50): 0 to inf (must be positive)
        # D (min): 0 to inf
        # M (asymmetry): 0.1 to 10 (prevent extreme asymmetry)
        lower_bounds = [0, -np.inf, 1e-10, 0, 0.1]
        upper_bounds = [np.inf, np.inf, np.inf, np.inf, 10.0]
        return (lower_bounds, upper_bounds)

    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate initial parameter guesses for 5PL.

        Args:
            x: Concentration values
            y: OD values

        Returns:
            (A_init, B_init, C_init, D_init, M_init)
        """
        A_init = np.max(y)
        D_init = np.min(y)
        C_init = np.median(x)
        B_init = -1.0
        M_init = 1.0  # Start with symmetric (reduces to 4PL)

        return (A_init, B_init, C_init, D_init, M_init)

    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse 5PL: Convert OD to concentration using numerical methods.

        The 5PL equation: y = D + (A - D) / ((1 + (x / C)^B)^M)

        We need to solve for x given y. Since there's no closed-form solution,
        we use numerical root-finding (scipy.optimize.brentq).

        Args:
            y: Measured OD value
            params: [A, B, C, D, M] fitted parameters

        Returns:
            Predicted concentration or None if solving fails
        """
        if params is None or len(params) != 5:
            return None

        A, B, C, D, M = params

        # Check if y is outside curve range
        if y <= D or y >= A:
            # Outside valid range
            if y <= D:
                return np.inf  # Very high concentration
            else:
                return 0.0  # Very low concentration

        from scipy.optimize import brentq

        # Define the equation to solve: equation(x) - y = 0
        def equation_to_solve(x):
            if x <= 0:
                return np.inf
            try:
                base = 1 + (x / C) ** B
                base = max(base, 1e-10)
                return D + (A - D) / (base ** M) - y
            except:
                return np.inf

        try:
            # Search for root in a reasonable concentration range
            # Use a wide range: 1e-6 to 1e6 (covers typical ELISA ranges from pg/mL to mg/mL)
            concentration = brentq(
                equation_to_solve,
                a=1e-6,
                b=1e6,
                xtol=1e-8,
                maxiter=100
            )

            return float(concentration) if np.isfinite(concentration) else None

        except Exception:
            # If numerical solving fails, return None
            return None
