"""BeELISA - Elisa Analysis"""

from .app import BeELISA, main
from importlib.metadata import version

__version__ = version("beelisa")
__all__ = ["BeELISA", "main"]