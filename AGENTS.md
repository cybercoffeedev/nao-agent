# AGENTS.md

Project-wide instructions for AI agents and contributors working on **NAO Agent**.

## Mission

NAO Agent lets a SoftBank NAO v6 robot hold a voice conversation with a person and
execute robot actions chosen by a local LLM. The project is experimental, but the
codebase should be treated as a maintainable application rather than a prototype.

## Language policy

- Code, comments, commit messages, and technical documentation must be written in English.
- User-facing speech and prompt content may stay in Polish for now.
- Multilingual support is planned for a later milestone. Do not hardcode new language
  assumptions in core logic.

## Non-negotiable constraints

1. **Local inference only.** The production runtime must not depend on a cloud LLM or
   cloud ASR provider. The local OpenAI-compatible endpoint is llama.cpp.
2. **Contract-first.** LLM output is a versioned JSON contract. It must be constrained
   and validated before any robot action is executed.
3. **Safety before features.** A robot action must never continue silently after a
   timeout or an error. Prefer failing safe over executing an uncertain action.
4. **Small, reversible changes.** Refactor in small steps, with tests, and keep the
   application runnable after each step.
5. **No pushing.** Agents commit locally only. The repository owner decides when to push.

## Architecture direction

The current application is a **modular monolith** with explicit boundaries. The target
boundaries are intentionally compatible with a future ROS2 migration:

- `nao_audio_pipeline` — microphone capture, voice activity detection, ASR
- `nao_state_manager` — connection, posture, battery, health, robot state
- `nao_conversation` — conversation loop and state machine
- `nao_intent_parser` — LLM contract validation and intent parsing
- `nao_intent_dispatcher` — routing intents to actions
- `nao_motion_executor` — NAOqi motion and LED execution
- `nao_bringup` — configuration and composition
- `nao_sim` — simulator adapter (deferred until the simulator decision)

Do not introduce ROS2 dependencies in the current branch. Use Python protocols and
adapters so the ROS2 migration can happen in a separate branch. See ADR-0003.

## Engineering rules

- Follow clean code and SOLID where it improves the design.
- Use design patterns from <https://refactoring.guru/design-patterns/catalog> when they
  solve a real problem. Do not add patterns for decoration.
- Avoid gold-plating. No speculative abstractions, frameworks, event buses, DI
  containers, or microservices unless a milestone explicitly needs them.
- Keep public behaviour covered by tests before refactoring it.
- Prefer constructor injection and an explicit composition root in `python/main.py`.
- Keep platform-specific code (NAOqi, SSH/SFTP, HTTP) behind adapters.
- Do not import NAOqi (`qi`) from modules that should be unit-testable.
- Log actionable context, never secrets.

## Testing

- Use `pytest`.
- Unit tests live in `tests/unit/`.
- Contract tests live in `tests/contract/`.
- Integration tests use fake adapters and live in `tests/integration/`.
- Hardware-in-the-loop checks are documented, not run in CI.
- New behaviour requires a test. Bug fixes require a regression test.

## Documentation

- Every significant architectural decision gets its own ADR in `docs/adr/`.
- `docs/adr/README.md` is the ADR index; use `docs/adr/template.md` when adding one.
- `docs/plans/README.md` is the source of truth for milestones and status.
- `docs/contracts/` owns the LLM response contract.
- `ARCHITECTURE.md` describes the current architecture and target boundaries.
- Update documentation in the same change as the code it describes.

## Git workflow

- Use small, focused commits with a conventional prefix, for example:
  - `docs: ...`
  - `fix(config): ...`
  - `feat(contract): ...`
  - `refactor(executor): ...`
  - `test(contract): ...`
  - `build: ...`
- Every agent commit must include:

  ```text
  Co-authored-by: opencode-agent[bot] <opencode-agent[bot]@users.noreply.github.com>
  ```

- Do not push. Do not rewrite history that the owner has already pushed.
- Do not commit secrets, `.env`, model caches, or generated runtime data.

## Useful commands

```bash
pip install -r requirements-dev.txt
ruff check .
pytest

# Production stack
cd infra
docker compose up -d
```
