"""Parsing, normalization and hashing of prompt files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from types import MappingProxyType

from .errors import PromptFormatError, clip
from .models import PromptVersion, VarSpec

MAX_FILE_BYTES = 262_144
MAX_HEADER_LINES = 200
TYPE_NAMES = frozenset({"str", "int", "float", "bool", "list[str]"})
VAR_NAME_RE = re.compile(r"[a-z_][a-z0-9_]{0,63}")
PLACEHOLDER_RE = re.compile(r"(\\\{\{)|\{\{\s*([a-z_][a-z0-9_]{0,63})\s*\}\}")

_DELIMITER = "---"


def normalize_text(raw: bytes, path: Path | None = None) -> str:
    """Return the canonical text of a prompt file.

    The bytes are decoded as UTF-8 (a leading BOM is dropped), CRLF and CR become LF, trailing
    spaces and tabs are stripped per line, trailing blank lines are removed and exactly one final
    LF is kept.

    Raises:
        PromptFormatError: if ``raw`` is not valid UTF-8.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise PromptFormatError("file is not valid UTF-8", path) from None
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def parse_prompt(raw: bytes, name: str, version: int, path: Path) -> PromptVersion:
    """Parse the bytes of one prompt file into a :class:`PromptVersion`.

    Raises:
        PromptFormatError: if the header or a placeholder is invalid.
    """
    text = normalize_text(raw, path)
    lines = text.split("\n")[:-1]
    if lines[0] != _DELIMITER:
        raise PromptFormatError("file must start with a '---' header line", path, 1)
    close = _find_close(lines, path)
    description, variables = _parse_header(lines, close, path)
    start = close + 1
    body = "\n".join(lines[start:])
    body_first_line = close + 2
    for match in PLACEHOLDER_RE.finditer(body):
        placeholder = match.group(2)
        if placeholder is not None and placeholder not in variables:
            line_no = body_first_line + body.count("\n", 0, match.start())
            raise PromptFormatError(f"placeholder '{placeholder}' is not declared", path, line_no)
    return PromptVersion(
        name=name,
        version=version,
        description=description,
        variables=MappingProxyType(variables),
        body=body,
        path=path,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text=text,
    )


def _find_close(lines: list[str], path: Path) -> int:
    for index in range(1, len(lines)):
        if lines[index] == _DELIMITER:
            return index
        if index > MAX_HEADER_LINES:
            raise PromptFormatError(f"header exceeds {MAX_HEADER_LINES} lines", path, index + 1)
    raise PromptFormatError("header is not closed by a '---' line", path, len(lines))


def _parse_header(lines: list[str], close: int, path: Path) -> tuple[str, dict[str, VarSpec]]:
    description: str | None = None
    variables: dict[str, VarSpec] = {}
    for index in range(1, close):
        line_no = index + 1
        content = lines[index]
        if not content.strip():
            continue
        key, separator, value = content.partition(":")
        if not separator:
            raise PromptFormatError("header line must have the form 'key: value'", path, line_no)
        key = key.strip()
        value = value.strip()
        if key == "description":
            if description is not None:
                raise PromptFormatError("duplicate header key 'description'", path, line_no)
            description = value
        elif key.startswith("vars."):
            var_name, spec = _parse_var_spec(key, value, path, line_no)
            if var_name in variables:
                raise PromptFormatError(f"duplicate variable '{var_name}'", path, line_no)
            variables[var_name] = spec
        else:
            raise PromptFormatError(f"unknown header key '{clip(key)}'", path, line_no)
    return description or "", variables


def _parse_var_spec(key: str, value: str, path: Path, line_no: int) -> tuple[str, VarSpec]:
    var_name = key.removeprefix("vars.")
    if not VAR_NAME_RE.fullmatch(var_name):
        raise PromptFormatError(f"invalid variable name '{clip(var_name)}'", path, line_no)
    optional = value.endswith("?")
    type_name = value[:-1] if optional else value
    if type_name not in TYPE_NAMES:
        raise PromptFormatError(f"unknown type '{clip(value)}'", path, line_no)
    return var_name, VarSpec(type_name, optional)
