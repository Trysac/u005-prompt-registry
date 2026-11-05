"""Versioned prompt files with typed variables, strict rendering, diffs and hashes."""

from __future__ import annotations

import logging

from .errors import (
    MissingVariableError,
    PromptError,
    PromptFormatError,
    PromptNotFoundError,
    UnexpectedVariableError,
    VariableTypeError,
)
from .loader import load_registry
from .models import PromptVersion, Registry, VarSpec
from .render import diff, render

__all__ = [
    "MissingVariableError",
    "PromptError",
    "PromptFormatError",
    "PromptNotFoundError",
    "PromptVersion",
    "Registry",
    "UnexpectedVariableError",
    "VarSpec",
    "VariableTypeError",
    "__version__",
    "diff",
    "load_registry",
    "render",
]

__version__ = "0.1.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())
