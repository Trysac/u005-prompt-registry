# Project record

## Objective

Prompts edited inline drift silently and template engines can hide missing variables or run template logic. This library gives each prompt a numeric version, a stable sha256 hash to log with each call, typed variables checked at render time and a readable diff between versions.

## Scope

- In scope: the public API documented in [README.md](../README.md): eager loading of a file-based registry, strict header and placeholder parsing, typed rendering, unified diffs, normalized hashes, and the `prompt-registry` command-line interface.
- Out of scope: loops, conditionals, remote registries, A/B assignment, and any runtime dependency or I/O beyond reading the registry root without an accepted ADR.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | pending measurement |
| Hours (human) | pending measurement |
| Cost (USD) | pending measurement |
