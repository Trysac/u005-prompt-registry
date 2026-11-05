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
| Tokens (input / output) | 469830 / 113439 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.8667 |

## Factory run u005 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2312 | 100317 | 0 | 4246 | 0.5043 |
| fix-1 | claude-sonnet-5-5 | no | 4 | 846 | 6634 | 24616 | 0.0275 |
| fix-2 | claude-sonnet-5-5 | no | 8 | 1141 | 10764 | 65247 | 0.0449 |
| fix-3 | claude-sonnet-5-5 | no | 10 | 1329 | 8478 | 71320 | 0.0416 |
| fix-4 | claude-sonnet-5-5 | no | 10 | 1603 | 6644 | 73771 | 0.0400 |
| audit | claude-sonnet-5-5 | no | 12 | 3602 | 36325 | 110357 | 0.1379 |
| docs | claude-haiku-5-5 | no | 117917 | 4601 | 0 | 0 | 0.0705 |

Total: $0.8667. Prices: Anthropic list prices.
