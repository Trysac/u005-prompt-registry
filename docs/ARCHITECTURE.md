# Architecture

## Purpose

`trysac-prompt-registry` is a small, dependency-free Python library and CLI for file-based, versioned prompt templates with typed variables, strict non-recursive rendering, unified diffs and normalized sha256 hashes.

## Shape

```text
caller code --> prompt_registry (public API in __init__.py)
                    |
                    +-- loader.py    reads <root>/<name>/v<N>.prompt.md (only file I/O)
                    +-- parser.py    normalizes text, parses header and placeholders, hashes
                    +-- models.py    frozen dataclasses and the in-memory Registry
                    +-- render.py    render() and diff()
                    +-- errors.py    PromptError hierarchy with stable codes
                    +-- __main__.py  command-line interface
```

- **Public API**: the names listed in `__all__` of `src/prompt_registry/__init__.py`.
- **Errors**: all library errors derive from `PromptError` and carry a `code`.
- **Side effects**: `load_registry` reads files; the CLI prints to stdout and stderr. `render` and `diff` are pure. The library never configures logging and never logs input text.

## Quality contract

`scripts/check.py` is the single definition of the gates; `fabrica.json` tells the factory and CI how to run it. See [TESTING.md](TESTING.md).

## Decisions

Architecture decisions are recorded in [decisions/](decisions/) as numbered ADRs.
