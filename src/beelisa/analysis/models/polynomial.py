"""Polynomial models (2nd and 3rd order) for non-sigmoid ELISA curves."""

import numpy as np
from typing import Optional
from .base import CurveModel


class Polynomial2Model(CurveModel):
    """
    2nd order polynomial (quadratic) model.

    Equation: y = a*x² + b*x + c

    Parameters:
        a: Quadratic coefficient
        b: Linear coefficient
        c: Constant term

    Best for: Non-sigmoid curves with one inflection point
    """

    @property
    def name(self) -> str:
        return "Polynomial-2"

    @property
    def param_names(self) -> list[str]:
        return ['a', 'b', 'c']

    @property
    def num_params(self) -> int:
        return 3

    def equation(self, x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
        """
        2nd order polynomial: y = a*x² + b*x + c

        Args:
            x: Concentration values
            a: Quadratic coefficient
            b: Linear coefficient
            c: Constant

        Returns:
            Predicted OD values
        """
        return a * x**2 + b * x + c

    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate initial parameter guesses using numpy polyfit.

        Args:
            x: Concentration values
            y: OD values

        Returns:
            (a_init, b_init, c_init)
        """
        # Use numpy's polyfit for initial guess
        coeffs = np.polyfit(x, y, 2)
        return tuple(coeffs)

    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse quadratic: Solve a*x² + b*x + (c - y) = 0

        Uses quadratic formula: x = (-b ± sqrt(b² - 4a(c-y))) / 2a

        Args:
            y: Measured OD value
            params: [a, b, c] fitted parameters

        Returns:
            Predicted concentration (positive root) or None if no real solution
        """
        if params is None or len(params) != 3:
            return None

        a, b, c = params

        # Solve a*x² + b*x + (c - y) = 0
        # Quadratic formula: x = (-b ± sqrt(b² - 4a(c-y))) / 2a

        discriminant = b**2 - 4*a*(c - y)

        if discriminant < 0:
            return None  # No real solution

        if a == 0:
            # Degenerate to linear
            if b == 0:
                return None
            return (y - c) / b

        # Take positive root
        sqrt_discriminant = np.sqrt(discriminant)
        root1 = (-b + sqrt_discriminant) / (2*a)
        root2 = (-b - sqrt_discriminant) / (2*a)

        # Return the positive concentration
        if root1 >= 0:
            return root1
        elif root2 >= 0:
            return root2
        else:
            return None


class Polynomial3Model(CurveModel):
    """
    3rd order polynomial (cubic) model.

    Equation: y = a*x³ + b*x² + c*x + d

    Parameters:
        a: Cubic coefficient
        b: Quadratic coefficient
        c: Linear coefficient
        d: Constant term

    Best for: Complex non-sigmoid curves with multiple inflection points
    """

    @property
    def name(self) -> str:
        return "Polynomial-3"

    @property
    def param_names(self) -> list[str]:
        return ['a', 'b', 'c', 'd']

    @property
    def num_params(self) -> int:
        return 4

    def equation(self, x: np.ndarray, a: float, b: float, c: float, d: float) -> np.ndarray:
        """
        3rd order polynomial: y = a*x³ + b*x² + c*x + d

        Args:
            x: Concentration values
            a: Cubic coefficient
            b: Quadratic coefficient
            c: Linear coefficient
            d: Constant

        Returns:
            Predicted OD values
        """
        return a * x**3 + b * x**2 + c * x + d

    def initial_guess(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Generate initial parameter guesses using numpy polyfit.

        Args:
            x: Concentration values
            y: OD values

        Returns:
            (a_init, b_init, c_init, d_init)
        """
        # Use numpy's polyfit for initial guess
        coeffs = np.polyfit(x, y, 3)
        return tuple(coeffs)

    def inverse(self, y: float, params: np.ndarray) -> Optional[float]:
        """
        Inverse cubic: Solve a*x³ + b*x² + c*x + (d - y) = 0

        Uses numpy.roots to find real positive solution.

        Args:
            y: Measured OD value
            params: [a, b, c, d] fitted parameters

        Returns:
            Predicted concentration (real positive root) or None if no valid solution
        """
        if params is None or len(params) != 4:
            return None

        a, b, c, d = params

        # Solve a*x³ + b*x² + c*x + (d - y) = 0
        # Coefficients in descending order for numpy.roots: [a, b, c, d-y]
        coefficients = [a, b, c, d - y]

        try:
            # Find roots
            roots = np.roots(coefficients)

            # Filter for real, positive roots
            real_positive_roots = []
            for root in roots:
                # Check if root is real (imaginary part is negligible)
                if np.abs(np.imag(root)) < 1e-10 and np.real(root) >= 0:
                    real_positive_roots.append(np.real(root))

            if len(real_positive_roots) == 0:
                return None

            # Return the smallest positive root (most physically meaningful)
            # For ELISA, lower concentration is more conservative
            return float(min(real_positive_roots))

        except Exception:
            # If root finding fails, return None
            return None
