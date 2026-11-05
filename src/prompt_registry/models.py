"""Immutable data model and the in-memory registry."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .errors import PromptError, PromptNotFoundError, clip

NAME_RE = re.compile(r"[a-z0-9_-]{1,64}")


@dataclass(frozen=True)
class VarSpec:
    """Declared type of a template variable.

    Attributes:
        type: One of ``str``, ``int``, ``float``, ``bool`` or ``list[str]``.
        optional: Whether the variable may be omitted (it then renders as an empty string).
    """

    type: str
    optional: bool = False


@dataclass(frozen=True)
class PromptVersion:
    """One immutable version of a prompt.

    Attributes:
        name: Prompt name.
        version: Positive integer version.
        description: Free-text description from the header.
        variables: Declared variables by name.
        body: Template body with trailing newline removed.
        path: Path of the file the prompt was loaded from.
        sha256: Hex digest of the normalized file text (header included).
        text: Normalized file text, used by :func:`prompt_registry.diff`.
    """

    name: str
    version: int
    description: str
    variables: Mapping[str, VarSpec]
    body: str
    path: Path
    sha256: str
    text: str = field(default="", repr=False, compare=False)


class Registry:
    """Read-only collection of prompt versions."""

    __slots__ = ("_prompts",)

    def __init__(self, prompts: Mapping[str, Mapping[int, PromptVersion]]) -> None:
        self._prompts = {name: dict(versions) for name, versions in prompts.items() if versions}

    def names(self) -> list[str]:
        """Return the prompt names in alphabetical order."""
        return sorted(self._prompts)

    def versions(self, name: str) -> list[int]:
        """Return the versions of ``name`` in ascending numeric order.

        Raises:
            PromptError: ``invalid_argument`` for a malformed name.
            PromptNotFoundError: if the prompt does not exist.
        """
        return sorted(self._versions_of(name))

    def get(self, name: str, version: int | None = None) -> PromptVersion:
        """Return one version of ``name``; the highest version when ``version`` is ``None``.

        Raises:
            PromptError: ``invalid_argument`` for a malformed name or version.
            PromptNotFoundError: if the prompt or the version does not exist.
        """
        versions = self._versions_of(name)
        if version is None:
            return versions[max(versions)]
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise PromptError("version must be a positive integer", "invalid_argument")
        if version not in versions:
            raise PromptNotFoundError(f"prompt '{clip(name)}' has no version {clip(str(version))}")
        return versions[version]

    def _versions_of(self, name: str) -> dict[int, PromptVersion]:
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise PromptError("invalid prompt name", "invalid_argument")
        versions = self._prompts.get(name)
        if versions is None:
            raise PromptNotFoundError(f"prompt '{clip(name)}' not found")
        return versions
