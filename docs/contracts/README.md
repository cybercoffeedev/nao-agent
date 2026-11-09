# LLM Response Contract

Status: **Draft v0** (defined in M0, enforced in M1).

This directory owns the contract between the LLM and the robot agent. The contract is the
single source of truth for the model's output; the prompt, parser, tests, and (later) the
llama.cpp grammar must all follow it.

## Files

| File | Purpose |
|---|---|
| `llm-response.schema.json` | JSON Schema for a model response. Source of truth. |
| `llm-response.example.json` | Human-readable example used in documentation and tests. |

## Response shape

The model returns a non-empty JSON array of steps. A step may contain:

- `speak` — text that the robot should say;
- `action` — name from the action catalog;
- `args` — keyword arguments for the action, only valid together with `action`;
- `speak` and `action` together — the robot executes the action and speaks the text.

The current version intentionally keeps `action` as a bounded string rather than an enum
of every action. In M1 the runtime composes the contract with the action catalog so that
action names and argument schemas are generated from the code, not maintained twice.

## Semantics

1. Steps are executed in order.
2. `speak` alone is a pure speech step.
3. `action` alone is a pure action step.
4. `action` + `speak` is an action step with narration. The executor must preserve both
   parts. This is a known bug in the current executor and is fixed in M1.
5. An empty array, an unknown action, or an invalid argument is a contract violation.
6. The executor never runs an unvalidated or partially parsed plan.

## Validation and failure policy

The runtime will:

1. request constrained output from llama.cpp (JSON Schema → GBNF);
2. validate the response against this schema;
3. validate action names and arguments against the action catalog;
4. on failure, make at most one repair request;
5. if the repair also fails, speak a short error and execute no actions.

The regex fallback in `python/agent/response_parser.py` is diagnostic only and must not be
part of the normal execution path after M1.

## Versioning

The contract is versioned in the `$id` (`urn:nao-agent:contract:llm-response:v0`). A
breaking change requires a new version and an update to ADR-0002 or a superseding ADR.
Backward-compatible additions (for example a new optional field) still require updating
the example and contract tests.

## Relationship to actions

The action catalog is the source of truth for action names, descriptions, argument
schemas, and whether an action produces a result that needs a follow-up response. The LLM
response contract must not duplicate that information by hand.

See `docs/adr/0002-llm-structured-output-gbnf.md` for the decision record.
