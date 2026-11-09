# Architecture Decision Records

This directory contains the architectural decisions for **NAO Agent**. Each significant
decision has its own file so that the context, trade-offs, and consequences remain
reviewable later.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-local-only-inference.md) | Local-only inference | Accepted | 2026-11-09 |
| [0002](0002-llm-structured-output-gbnf.md) | Structured LLM output via JSON Schema and GBNF | Accepted | 2026-11-09 |
| [0003](0003-modular-monolith-ros2-boundaries.md) | Modular monolith with ROS2-ready boundaries | Accepted | 2026-11-09 |

## Adding an ADR

1. Copy [`template.md`](template.md).
2. Use the next free four-digit number: `0004-...`, `0005-...`, etc.
3. Give the file a short, kebab-case title.
4. Add it to the index above.
5. Link related ADRs from the new file and from the affected code or plan.

An ADR is immutable once accepted, except for corrections. If a decision changes,
create a new ADR that supersedes the old one and mark the old one as `Superseded`.

## Status meanings

- **Proposed** — under discussion; not binding yet.
- **Accepted** — the current decision; code and docs should follow it.
- **Superseded** — replaced by a newer ADR; kept for history.
- **Deprecated** — no longer recommended, but may still exist in the codebase.

## Scope

Use an ADR for decisions that affect more than one module or are expensive to reverse,
for example:

- inference and ASR architecture
- LLM output contract and decoding strategy
- robot abstraction and simulation strategy
- ROS2 migration strategy
- security boundaries
- action execution and safety model

Do not use an ADR for local implementation details that fit in a code comment or a
regular design note.
