# Testing

## Running

```sh
uv run pytest --cov=prompt_registry   # tests with coverage report
uv run python scripts/check.py      # every gate, as CI and the factory run it
```

## Policy

- Branch coverage of `src/prompt_registry` must stay at or above 80 %; the gate fails below it.
- Tests exercise the public API (`import prompt_registry`) and assert observable effects: return values, raised exceptions, error codes and messages.
- Each bug fix starts with a failing test that reproduces it.
- Tests are deterministic: no network, no wall clock, no dependence on test order.

## Layout

`tests/test_<module>.py` mirrors each public module. Shared fixtures go in `tests/conftest.py`.

The acceptance criteria to cover are: version ordering and rejection of leading zeros; single-pass rendering without re-expansion; missing, unexpected and mistyped variables; placeholder line numbers in format errors; CRLF and trailing-space normalization with stable hashes; diff headers and cross-name rejection; size and symlink bounds; and CLI exit codes 0, 1 and 2.
