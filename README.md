# prompt-registry

[![PyPI version](https://img.shields.io/pypi/v/trysac-prompt-registry)](https://pypi.org/project/trysac-prompt-registry/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-prompt-registry)](LICENSE)
[![CI](https://github.com/Trysac/u005-prompt-registry/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u005-prompt-registry/actions/workflows/ci.yml)

Versioned prompt files with typed variables, strict non-recursive rendering, unified diffs between versions and normalized sha256 hashes for traceability

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-prompt-registry
# or
uv add trysac-prompt-registry
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import prompt_registry

# normalize() trims surrounding whitespace and lower-cases the text.
print(prompt_registry.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    prompt_registry.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
