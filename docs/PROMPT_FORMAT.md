# Prompt file format

This document describes the on-disk layout and the file format read by `prompt_registry`.

## Layout

```
<root>/<name>/v<N>.prompt.md
```

- `name` matches `^[a-z0-9_-]{1,64}$`.
- `N` is a positive integer without leading zeros. Versions sort numerically (`v10` is newer than `v2`).
- Limits: 262 144 bytes per file, 10 000 prompt files per root, 200 header lines.
- A file is opened only after `Path.resolve()` confirms that it lives inside the root. A symlink that
  resolves elsewhere raises `PromptError` with code `outside_root`.

## File

```
---
description: Greets a person
vars.name: str
vars.times: int?
---
Hello {{ name }}!
```

The header is not YAML. The first line is `---`, each following line is `key: value`, and a second `---`
line ends the header. Blank header lines are ignored. Keys are `description` and `vars.<name>`
(`<name>` matches `[a-z_][a-z0-9_]{0,63}`). Types are `str`, `int`, `float`, `bool` and `list[str]`;
a trailing `?` marks the variable optional.

## Placeholders

- A placeholder is `{{ name }}` (whitespace inside the braces is optional) and must be declared in the header.
  An undeclared placeholder raises `PromptFormatError` carrying the file path and line number.
- `\{{` writes a literal `{{`; the backslash is removed.
- Text that does not match the placeholder pattern (for example `{{ Name }}` or `{{ a-b }}`) stays literal.
- Values are inserted in a single pass and never scanned again, so `{{n}}` inside a value stays literal.

## Rendering rules

- Undeclared keys raise `UnexpectedVariableError`, missing required variables `MissingVariableError`.
- A `bool` is never accepted as `int` or `float`; `bool` renders `true` or `false`.
- `float` renders `repr(value)`; `list[str]` joins its items with a newline; an omitted optional renders as an empty string.

## Hash

The sha256 covers the normalized file text, header included: UTF-8 decoded with the BOM removed, CRLF and
CR turned into LF, trailing spaces and tabs stripped per line, trailing blank lines removed, and one final LF.
The hash is therefore stable across editors and line endings and changes whenever a variable type changes.

## Command line

```
python -m prompt_registry --root prompts list
python -m prompt_registry --root prompts render greet --var name=Ana
python -m prompt_registry --root prompts diff greet 1 2
```

Exit code 0 means success, 1 a `PromptError` (message on stderr) and 2 a usage, I/O or parse error.
Scalars are passed with `--var key=value`; lists only through `--vars-json FILE` (at most 1 MiB).
