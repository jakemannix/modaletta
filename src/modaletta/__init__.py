"""Modaletta: AI agents using Letta and Modal."""

__version__ = "0.1.0"
__author__ = "Jake Mannix"
__email__ = "jake.mannix@gmail.com"

from .agent import ModalettaAgent
from .client import ModalettaClient
from .config import ModalettaConfig

__all__ = [
    "ModalettaAgent",
    "ModalettaClient", 
    "ModalettaConfig",
]