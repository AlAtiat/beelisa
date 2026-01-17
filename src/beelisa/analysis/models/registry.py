"""Model registry for curve fitting models - Factory pattern implementation."""

from typing import Dict, Type, List
from .base import CurveModel
from .linear import LinearModel
from .log_linear import LogLinearModel
from .exponential import ExponentialModel
from .polynomial import Polynomial2Model, Polynomial3Model
from .four_pl import FourPLModel
from .five_pl import FivePLModel

class ModelRegistry:
    """
    Factory and registry for curve fitting models.

    Provides centralized model management with auto-registration.
    """

    _models: Dict[str, Type[CurveModel]] = {}

    @classmethod
    def register(cls, model_class: Type[CurveModel]):
        """
        Register a model class.

        Args:
            model_class: CurveModel subclass to register
        """
        instance = model_class()
        cls._models[instance.name] = model_class

    @classmethod
    def get_model(cls, name: str) -> CurveModel:
        """
        Get model instance by name.

        Args:
            name: Model name (e.g., "4PL", "Linear")

        Returns:
            CurveModel instance

        Raises:
            ValueError: If model not registered
        """
        if name not in cls._models:
            raise ValueError(f"Model '{name}' not registered. Available: {cls.list_models()}")
        return cls._models[name]()

    @classmethod
    def list_models(cls) -> List[str]:
        """
        List all registered model names.

        Returns:
            List of model names
        """
        return list(cls._models.keys())

    @classmethod
    def get_all_models(cls) -> List[CurveModel]:
        """
        Get instances of all registered models.

        Returns:
            List of CurveModel instances
        """
        return [model_class() for model_class in cls._models.values()]


# register all available models
ModelRegistry.register(LinearModel)
ModelRegistry.register(LogLinearModel)
ModelRegistry.register(ExponentialModel)
ModelRegistry.register(Polynomial2Model)
ModelRegistry.register(Polynomial3Model)
ModelRegistry.register(FourPLModel)
ModelRegistry.register(FivePLModel)
