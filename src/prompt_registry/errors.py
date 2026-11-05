"""Typed errors raised by the prompt registry.

Every error derives from :class:`PromptError` and carries a stable, machine-readable ``code``.
Messages are short and never contain more than a clipped excerpt of caller-supplied text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

ErrorCode = Literal[
    "not_found",
    "format",
    "missing_variable",
    "unexpected_variable",
    "variable_type",
    "too_large",
    "outside_root",
    "invalid_argument",
]

MAX_MESSAGE_CHARS = 200
MAX_EXCERPT_CHARS = 64


def clip(text: str, limit: int = MAX_EXCERPT_CHARS) -> str:
    """Return ``text`` with non-printable characters masked and cut to ``limit`` characters."""
    shown = "".join(ch if ch.isprintable() else "?" for ch in text[:limit])
    return shown + "..." if len(text) > limit else shown


class PromptError(Exception):
    """Base class of every error raised by this library.

    Attributes:
        code: Stable machine-readable error code.
    """

    def __init__(self, message: str, code: ErrorCode = "invalid_argument") -> None:
        if len(message) > MAX_MESSAGE_CHARS:
            keep = MAX_MESSAGE_CHARS - 3
            message = message[:keep] + "..."
        super().__init__(message)
        self.code: ErrorCode = code


class PromptNotFoundError(PromptError):
    """Raised when a prompt name, version or registry root does not exist."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "not_found")


class PromptFormatError(PromptError):
    """Raised when a prompt file or file name is malformed.

    Attributes:
        path: The offending file (or directory), when known.
        line: The 1-based line number in the file, when known.
    """

    def __init__(self, message: str, path: Path | None = None, line: int | None = None) -> None:
        location = f" (line {line})" if line is not None else ""
        super().__init__(message + location, "format")
        self.path = path
        self.line = line


class MissingVariableError(PromptError):
    """Raised when a required variable is not supplied.

    Attributes:
        name: Name of the missing variable.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"missing required variable '{clip(name)}'", "missing_variable")
        self.name = name


class UnexpectedVariableError(PromptError):
    """Raised when a supplied variable is not declared by the prompt.

    Attributes:
        name: Name of the unexpected variable.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"unexpected variable '{clip(name)}'", "unexpected_variable")
        self.name = name


class VariableTypeError(PromptError):
    """Raised when a supplied value does not match the declared variable type.

    Attributes:
        name: Name of the variable.
        expected: Declared type, for example ``int``.
        actual: Name of the type that was supplied, for example ``bool``.
    """

    def __init__(self, name: str, expected: str, actual: str) -> None:
        message = f"variable '{clip(name)}' expects {clip(expected)} but got {clip(actual)}"
        super().__init__(message, "variable_type")
        self.name = name
        self.expected = expected
        self.actual = actual
