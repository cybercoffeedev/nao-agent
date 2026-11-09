# ADR-0002: Structured LLM output via JSON Schema and GBNF

- **Status:** Accepted
- **Date:** 2026-11-09
- **Deciders:** project owner
- **Related:** ADR-0001, `docs/contracts/`, `python/agent/llm.py`,
  `python/agent/response_parser.py`

## Context

The LLM must return a machine-readable plan of speech and robot actions. The current
implementation asks for JSON in the prompt and then tries to recover it with regular
expressions. This is fragile:

- the model may return Markdown, prose, or partial JSON;
- nested objects and escaped quotes break the regex parser;
- an invalid step can reach the executor;
- there is no single source of truth for the response shape;
- the model can invent action names or argument shapes.

The project uses a local llama.cpp server, so the decoding process can be constrained
without changing to a cloud provider.

## Decision

Use **JSON Schema as the single source of truth** for the LLM response contract and
enforce it with **GBNF grammar-constrained decoding** in llama.cpp.

1. The contract lives in `docs/contracts/llm-response.schema.json` and is versioned.
2. The runtime derives the llama.cpp grammar from that schema (schema-to-GBNF). If the
   running llama.cpp version cannot do this at request time, the grammar is generated
   from the same schema during the build. The schema remains the source of truth.
3. Every model response is validated against the schema before execution.
4. Invalid output gets **at most one repair attempt**. If it is still invalid, the agent
   speaks a short error and executes no actions. Partial or unvalidated plans are never
   executed.
5. Action names and action argument schemas are generated from the action catalog, not
   invented by the model. The contract grows as actions are added.
6. The regex-based recovery path is removed from the normal execution path. A parser may
   remain only for diagnostics.

The contract currently describes a JSON array of steps:

```json
[
  {"speak": "text"},
  {"action": "name", "args": {"param": "value"}},
  {"action": "name", "speak": "text"}
]
```

A step may combine `action` and `speak`; the executor must preserve both.

## Consequences

### Positive

- Invalid JSON and invented action names are rejected before execution.
- The prompt, parser, tests, and documentation share one contract.
- Behaviour is more predictable and easier to test.
- The same schema can later drive native tool calling or a ROS2 intent message.

### Negative

- The schema must be maintained when actions or step semantics change.
- Very strict grammars can make some valid natural-language plans harder to express.
- The exact llama.cpp feature set and version must be pinned and tested.

### Follow-up

- Implement the contract in milestone M1.
- Add contract tests for valid, malformed, and partial outputs.
- Add a schema/action-catalog consistency test.
- Record the llama.cpp version that supports the chosen schema-to-grammar path.

## Alternatives considered

- **Prompt-only JSON plus regex (current):** rejected; too brittle for robot actions.
- **Native OpenAI tool calling:** deferred; it is a good candidate later, but the
  project already has a step-based plan and wants to stay local-first. Mixing tool
  calling and JSON steps now would create two execution paths.
- **Hand-maintained GBNF:** rejected; it duplicates the contract and drifts quickly.
- **Unconstrained output with post-hoc repair only:** rejected as the primary strategy;
  it wastes latency and still allows invalid plans.

## References

- `docs/contracts/llm-response.schema.json`
- `docs/contracts/README.md`
- `python/agent/response_parser.py`
- `python/agent/step_executor.py`
