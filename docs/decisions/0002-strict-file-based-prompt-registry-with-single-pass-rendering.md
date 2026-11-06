# Strict file-based prompt registry with single-pass rendering and normalized hashes

Status: accepted (generated, pending human review)

## Context

Prompts edited inline drift silently, outputs cannot be traced to a prompt version, and general template engines render missing variables as empty strings or execute logic inside templates. The library must stay small, offline and dependency-free, and must treat prompt files and rendering values as untrusted input.

## Decision

Prompts live in <root>/<name>/v<N>.prompt.md with a deliberately tiny non-YAML header declaring typed variables. The registry is loaded eagerly so every format, size and containment error surfaces at load time. Files are opened only after Path.resolve() confirms containment in the root, with caps on file size, file count and header length. Rendering is one regex pass in which inserted values are never rescanned, with no loops or conditionals, and every mismatch raises a typed PromptError with a stable code. The sha256 is computed over a normalized text that includes the header, so line endings and trailing whitespace do not change it while a type change does.

## Consequences

Rendering is predictable, linear-time and safe against injected placeholder text, and each call can log a stable hash. Eager loading bounds memory only by the per-file and file-count caps, so a very large registry costs memory at load time. The template language is intentionally limited, so users who need logic must compute values before rendering. Resolving then opening a path leaves a small time-of-check/time-of-use window that is acceptable for a local, trusted-filesystem registry.
