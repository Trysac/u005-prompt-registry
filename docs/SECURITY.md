# Security notes

## Threat model

`trysac-prompt-registry` reads files from a registry directory and performs no network access. The main risks are:

**Defended**

- **Path escape**: each prompt file is resolved with `Path.resolve()` and must lie inside the resolved root (`outside_root`); symlinks pointing outside are rejected before the file is opened.
- **Oversized input**: prompt files over 262,144 bytes, registries with more than 10,000 prompt files, headers over 200 lines, `--vars-json` files over 1 MiB and diffs over 20,000 lines are rejected with `too_large`.
- **Template injection**: values are substituted in one pass and never re-scanned, so placeholder text inside a value stays literal. No `eval`, `exec` or template logic is used.
- **Silent misuse**: missing or unexpected variables and type mismatches raise typed errors; `bool` is never accepted as `int` or `float`.
- **Log leakage**: the library never logs input text and never configures logging.

**Not defended**

- A registry directory that is writable by an attacker can change prompts; the library verifies no signature, only computes a hash.
- The sha256 hash is for traceability, not authentication.
- Symlinks inside the root that point to other files inside the root are followed.
- Operating-system errors such as permission failures are propagated as `OSError`, and the CLI reports them with exit code 2.
- Prompt text supplied by the caller is not sanitized for the downstream model; prompt-injection defence is the caller's responsibility.
- Rendered output size is capped by the same `too_large` limit, but the caller's values are otherwise unchecked.

## Publishing

Releases are published to PyPI with trusted publishing (OIDC) when available, never with a long-lived token stored in the repository.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
