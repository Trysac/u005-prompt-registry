"""Loading a prompt registry from a directory tree."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from .errors import PromptError, PromptFormatError, PromptNotFoundError, clip
from .models import NAME_RE, PromptVersion, Registry
from .parser import MAX_FILE_BYTES, parse_prompt

logger = logging.getLogger(__name__)

MAX_FILES = 10_000
SUFFIX = ".prompt.md"

_VERSION_FILE_RE = re.compile(r"v([0-9]+)\.prompt\.md")


def load_registry(root: Path) -> Registry:
    """Load every ``<root>/<name>/v<N>.prompt.md`` file into a :class:`Registry`.

    All files are parsed and validated eagerly. Files are opened only after ``Path.resolve()``
    confirms they live inside ``root``. Operating-system errors (for example permissions) are
    propagated as :class:`OSError`.

    Raises:
        PromptNotFoundError: if ``root`` does not exist.
        PromptError: ``invalid_argument`` (bad root), ``too_large`` (file or file-count limit) or
            ``outside_root`` (a file resolves outside ``root``).
        PromptFormatError: if a directory name, file name or file content is malformed.
    """
    if not isinstance(root, str | os.PathLike):
        raise PromptError("root must be a path", "invalid_argument")
    root_path = Path(root)
    try:
        root_real = root_path.resolve(strict=True)
    except FileNotFoundError:
        raise PromptNotFoundError("registry root does not exist") from None
    if not root_real.is_dir():
        raise PromptError("registry root is not a directory", "invalid_argument")
    prompts: dict[str, dict[int, PromptVersion]] = {}
    count = 0
    for directory in sorted(root_path.iterdir()):
        if not directory.is_dir():
            continue
        files = sorted(entry for entry in directory.iterdir() if entry.name.endswith(SUFFIX))
        if not files:
            continue
        name = directory.name
        if not NAME_RE.fullmatch(name):
            raise PromptFormatError(f"invalid prompt name '{clip(name)}'", directory)
        versions = prompts.setdefault(name, {})
        for file_path in files:
            count += 1
            if count > MAX_FILES:
                raise PromptError(f"registry has more than {MAX_FILES} prompt files", "too_large")
            version = _parse_version(file_path)
            raw = _read_inside(file_path, root_real)
            versions[version] = parse_prompt(raw, name, version, file_path)
    logger.debug("loaded %d prompt files", count)
    return Registry(prompts)


def _parse_version(path: Path) -> int:
    match = _VERSION_FILE_RE.fullmatch(path.name)
    if match is None or match.group(1).startswith("0"):
        raise PromptFormatError(f"invalid prompt file name '{clip(path.name)}'", path)
    return int(match.group(1))


def _read_inside(path: Path, root_real: Path) -> bytes:
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        raise PromptFormatError("cannot resolve prompt file", path) from None
    if not resolved.is_relative_to(root_real):
        raise PromptError("prompt file resolves outside the registry root", "outside_root")
    if not resolved.is_file():
        raise PromptFormatError("prompt file is not a regular file", path)
    with resolved.open("rb") as handle:
        raw = handle.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise PromptError(f"prompt file exceeds {MAX_FILE_BYTES} bytes", "too_large")
    return raw
