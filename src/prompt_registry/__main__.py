"""Command-line interface for the prompt registry (``python -m prompt_registry``).

Exit codes: 0 on success, 1 for any :class:`~prompt_registry.PromptError` (message on stderr)
and 2 for usage, I/O or parse errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from .errors import PromptError, VariableTypeError, clip
from .loader import load_registry
from .models import PromptVersion
from .render import diff, render

MAX_VARS_JSON_BYTES = 1_048_576

_INT_RE = re.compile(r"[+-]?[0-9]+")
_FLOAT_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class _UsageError(Exception):
    """Raised for command-line usage or parse problems (exit code 2)."""


def _parse_int(text: str, minimum: int) -> int:
    try:
        number = int(text)
    except ValueError:
        number = minimum - 1
    if number < minimum:
        raise argparse.ArgumentTypeError(f"must be an integer >= {minimum}")
    return number


def _positive_int(text: str) -> int:
    return _parse_int(text, 1)


def _non_negative_int(text: str) -> int:
    return _parse_int(text, 0)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prompt-registry", description="Prompt registry.")
    parser.add_argument("--root", default="prompts", metavar="DIR", help="registry root")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    commands.add_parser("list", help="list prompts and versions")
    show = commands.add_parser("show", help="print a prompt body")
    show.add_argument("name")
    show.add_argument("--version", type=_positive_int, default=None)
    render_cmd = commands.add_parser("render", help="render a prompt")
    render_cmd.add_argument("name")
    render_cmd.add_argument("--version", type=_positive_int, default=None)
    render_cmd.add_argument("--var", action="append", default=[], metavar="KEY=VALUE")
    render_cmd.add_argument("--vars-json", metavar="FILE", default=None)
    diff_cmd = commands.add_parser("diff", help="unified diff of two versions")
    diff_cmd.add_argument("name")
    diff_cmd.add_argument("a", type=_positive_int)
    diff_cmd.add_argument("b", type=_positive_int)
    diff_cmd.add_argument("--context", type=_non_negative_int, default=3)
    hash_cmd = commands.add_parser("hash", help="print the sha256 of a prompt")
    hash_cmd.add_argument("name")
    hash_cmd.add_argument("--version", type=_positive_int, default=None)
    return parser


def _read_vars_json(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        raw = handle.read(MAX_VARS_JSON_BYTES + 1)
    if len(raw) > MAX_VARS_JSON_BYTES:
        raise PromptError("variables file exceeds 1 MiB", "too_large")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        raise _UsageError("variables file is not valid JSON") from None
    if not isinstance(data, dict):
        raise _UsageError("variables file must contain a JSON object")
    return data


def _to_int(text: str) -> int | None:
    if _INT_RE.fullmatch(text) is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _coerce(prompt: PromptVersion, key: str, text: str) -> object:
    spec = prompt.variables.get(key)
    if spec is None or spec.type == "str":
        return text
    kind = spec.type
    if kind == "int":
        number = _to_int(text)
        if number is not None:
            return number
    elif kind == "float" and _FLOAT_RE.fullmatch(text):
        return float(text)
    elif kind == "bool" and text in ("true", "false"):
        return text == "true"
    raise VariableTypeError(key, kind, "str")


def _collect_values(prompt: PromptVersion, args: argparse.Namespace) -> dict[str, object]:
    values: dict[str, object] = {}
    if args.vars_json is not None:
        values.update(_read_vars_json(Path(args.vars_json)))
    seen: set[str] = set()
    for item in args.var:
        key, separator, text = item.partition("=")
        if not separator or not key:
            raise _UsageError("--var expects KEY=VALUE")
        if key in seen:
            raise _UsageError(f"--var '{clip(key)}' given more than once")
        seen.add(key)
        values[key] = _coerce(prompt, key, text)
    return values


def _run(args: argparse.Namespace) -> int:
    registry = load_registry(Path(args.root))
    command = args.command
    if command == "list":
        for name in registry.names():
            versions = " ".join(str(version) for version in registry.versions(name))
            print(f"{name} {versions}")
        return 0
    if command == "diff":
        first = registry.get(args.name, args.a)
        second = registry.get(args.name, args.b)
        text = diff(first, second, args.context)
        if text:
            print(text)
        return 0
    prompt = registry.get(args.name, args.version)
    if command == "show":
        print(prompt.body)
    elif command == "hash":
        print(prompt.sha256)
    else:
        print(render(prompt, _collect_values(prompt, args)))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return the process exit code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2
    try:
        return _run(args)
    except PromptError as exc:
        print(f"error[{exc.code}]: {exc}", file=sys.stderr)
        return 1
    except _UsageError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"i/o error: {clip(str(exc), 150)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
