"""Strict, non-recursive rendering and unified diffs between prompt versions."""

from __future__ import annotations

import difflib
from collections.abc import Mapping, Sequence

from .errors import (
    MissingVariableError,
    PromptError,
    PromptFormatError,
    UnexpectedVariableError,
    VariableTypeError,
)
from .models import PromptVersion, VarSpec
from .parser import PLACEHOLDER_RE

MAX_RENDERED_CHARS = 4_194_304
MAX_DIFF_LINES = 20_000


def render(prompt: PromptVersion, values: Mapping[str, object]) -> str:
    """Render ``prompt`` with ``values``.

    Placeholders are replaced in a single pass: inserted values are never scanned again, so
    placeholder text inside a value stays literal. ``\\{{`` produces a literal ``{{``. A ``bool``
    is never accepted as ``int`` or ``float``; ``bool`` renders as ``true``/``false``, ``float``
    as ``repr(value)`` (an ``int`` supplied for a ``float`` variable is converted first),
    ``list[str]`` joins with newlines and an omitted (or ``None``) optional renders as ``''``.

    Raises:
        UnexpectedVariableError: a key is not declared by the prompt.
        MissingVariableError: a required variable is absent.
        VariableTypeError: a value does not match its declared type.
        PromptError: ``invalid_argument`` for bad arguments, ``too_large`` for oversized output.
    """
    if not isinstance(prompt, PromptVersion):
        raise PromptError("prompt must be a PromptVersion", "invalid_argument")
    if not isinstance(values, Mapping):
        raise PromptError("values must be a mapping", "invalid_argument")
    keys = list(values)
    if any(not isinstance(key, str) for key in keys):
        raise PromptError("variable names must be strings", "invalid_argument")
    variables = prompt.variables
    for key in sorted(keys):
        if key not in variables:
            raise UnexpectedVariableError(key)
    rendered: dict[str, str] = {}
    for name, spec in variables.items():
        if name not in values or (values[name] is None and spec.optional):
            if not spec.optional:
                raise MissingVariableError(name)
            rendered[name] = ""
        else:
            rendered[name] = _render_value(name, spec, values[name])
    body = prompt.body
    parts: list[str] = []
    position = 0
    size = 0
    for match in PLACEHOLDER_RE.finditer(body):
        start = match.start()
        literal = body[position:start]
        placeholder = match.group(2)
        if placeholder is None:
            piece = "{{"
        elif placeholder in rendered:
            piece = rendered[placeholder]
        else:
            raise PromptFormatError(f"placeholder '{placeholder}' is not declared", prompt.path)
        size += len(literal) + len(piece)
        if size > MAX_RENDERED_CHARS:
            raise PromptError("rendered text is too large", "too_large")
        parts.extend((literal, piece))
        position = match.end()
    parts.append(body[position:])
    return "".join(parts)


def diff(a: PromptVersion, b: PromptVersion, context: int = 3) -> str:
    """Return a unified diff between two versions of the same prompt.

    The normalized file texts (header included) are compared with :func:`difflib.unified_diff`,
    with file names ``<name>@v<a>`` and ``<name>@v<b>``; lines are joined with ``\\n``. The
    result is empty when the texts are identical.

    Raises:
        PromptError: ``invalid_argument`` for different prompt names or bad arguments, and
            ``too_large`` when a prompt has more than 20 000 lines.
    """
    if not isinstance(a, PromptVersion) or not isinstance(b, PromptVersion):
        raise PromptError("diff expects two PromptVersion objects", "invalid_argument")
    if a.name != b.name:
        raise PromptError("cannot diff prompts with different names", "invalid_argument")
    if isinstance(context, bool) or not isinstance(context, int) or context < 0:
        raise PromptError("context must be a non-negative integer", "invalid_argument")
    lines = difflib.unified_diff(
        _diff_lines(a),
        _diff_lines(b),
        fromfile=f"{a.name}@v{a.version}",
        tofile=f"{b.name}@v{b.version}",
        n=context,
        lineterm="",
    )
    return "\n".join(lines)


def _diff_lines(prompt: PromptVersion) -> list[str]:
    text = prompt.text or prompt.body
    lines = text.removesuffix("\n").split("\n")
    if len(lines) > MAX_DIFF_LINES:
        raise PromptError(f"prompt has more than {MAX_DIFF_LINES} lines", "too_large")
    return lines


def _render_value(name: str, spec: VarSpec, value: object) -> str:
    expected = spec.type
    if expected == "str" and isinstance(value, str):
        return value
    if expected == "bool" and isinstance(value, bool):
        return "true" if value else "false"
    if expected == "int" and isinstance(value, int) and not isinstance(value, bool):
        return _int_text(name, value)
    if expected == "float" and isinstance(value, float | int) and not isinstance(value, bool):
        return _float_text(name, value)
    if expected == "list[str]" and isinstance(value, list | tuple):
        return _list_text(name, value)
    raise VariableTypeError(name, expected, type(value).__name__)


def _int_text(name: str, value: int) -> str:
    try:
        return str(value)
    except ValueError:
        raise VariableTypeError(name, "int", "oversized int") from None


def _float_text(name: str, value: float) -> str:
    try:
        return repr(float(value))
    except OverflowError:
        raise VariableTypeError(name, "float", "oversized int") from None


def _list_text(name: str, value: Sequence[object]) -> str:
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise VariableTypeError(name, "list[str]", f"list[{type(item).__name__}]")
        items.append(item)
    return "\n".join(items)
