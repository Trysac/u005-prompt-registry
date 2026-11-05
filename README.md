# prompt-registry

[![PyPI version](https://img.shields.io/pypi/v/trysac-prompt-registry)](https://pypi.org/project/trysac-prompt-registry/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-prompt-registry)](LICENSE)
[![CI](https://github.com/Trysac/u005-prompt-registry/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u005-prompt-registry/actions/workflows/ci.yml)

Versioned prompt files with typed variables, strict non-recursive rendering, unified diffs between versions and normalized sha256 hashes for traceability.

## Problem

Prompts edited inline drift silently, so nobody knows which version produced an output. Template engines render a missing variable as an empty string or evaluate logic inside templates. This library keeps each prompt as a numbered file with a stable sha256 hash, checks typed variables at render time, and shows readable diffs between versions, without a template language.

## Install

```sh
pip install trysac-prompt-registry
# or
uv add trysac-prompt-registry
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
from pathlib import Path
from prompt_registry import diff, load_registry, render

registry = load_registry(Path("prompts"))
prompt = registry.get("greet")  # latest version
print(prompt.sha256)  # log this with every model call
print(render(prompt, {"name": "Ana"}))
if registry.versions("greet")[:2] == [1, 2]:
    print(diff(registry.get("greet", 1), registry.get("greet", 2)))
```

## Public API

- `load_registry(root: Path) -> Registry`: parses and validates every `<root>/<name>/v<N>.prompt.md` eagerly.
- `Registry.names() -> list[str]`, `Registry.versions(name) -> list[int]`, `Registry.get(name, version: int | None = None) -> PromptVersion` (latest when `version` is `None`).
- `PromptVersion` (frozen dataclass): `name`, `version`, `description`, `variables`, `body`, `path`, `sha256`.
- `VarSpec` (frozen dataclass): `type` (`str`, `int`, `float`, `bool`, `list[str]`) and `optional`.
- `render(prompt, values: Mapping[str, object]) -> str`: single-pass substitution; inserted values are never re-scanned; `\{{` yields a literal `{{`; `bool` is never accepted as `int` or `float`; `bool` renders `true`/`false`; `float` renders `repr(value)`; `list[str]` joins with newlines; an omitted optional renders as an empty string.
- `diff(a, b, context: int = 3) -> str`: unified diff of normalized texts labelled `<name>@v<a>` and `<name>@v<b>`.
- CLI: `python -m prompt_registry` with commands `list`, `show`, `render`, `diff`, `hash`; `--root` defaults to `prompts`. Exit codes: 0 success, 1 for any `PromptError`, 2 for usage, I/O or parse errors.

Errors derive from `PromptError`, which exposes a `code` of `not_found`, `format`, `missing_variable`, `unexpected_variable`, `variable_type`, `too_large`, `outside_root` or `invalid_argument`. Subclasses: `PromptNotFoundError`, `PromptFormatError` (`.path`, `.line`), `MissingVariableError` (`.name`), `UnexpectedVariableError` (`.name`), `VariableTypeError` (`.name`, `.expected`, `.actual`).

Limits: files up to 262,144 bytes; at most 10,000 prompt files per root; header up to 200 lines; a `--vars-json` file up to 1 MiB; diffs up to 20,000 lines per prompt. Prompt names match `[a-z0-9_-]{1,64}`; version numbers are positive integers without leading zeros.

The library does not support loops, conditionals, remote registries or A/B assignment.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
