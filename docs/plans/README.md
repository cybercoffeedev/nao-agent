# Stage Plans

This file is the **source of truth** for project milestones, status, and acceptance
criteria. Architectural decisions are recorded separately in [`docs/adr/`](../adr/).

## Status legend

| Status | Meaning |
|---|---|
| **Done** | Scope completed and verified. |
| **In progress** | Actively being implemented. |
| **Planned** | Agreed direction, not started. |
| **Deferred** | Deliberately postponed; reason recorded. |

## Guiding principles

1. Stabilize contracts and tests before large refactors.
2. Prefer a modular monolith with explicit boundaries over a premature ROS2 rewrite.
3. Keep local inference as the production default (ADR-0001).
4. Constrain and validate LLM output before executing actions (ADR-0002).
5. Make the robot safe to stop; never leave an action running after a timeout.
6. Avoid gold-plating: introduce a pattern or dependency only when the milestone needs it.
7. Keep Polish as the only supported conversation language until the multilingual milestone.

## Milestone overview

| ID | Milestone | Status | Goal |
|---|---|---|---|
| M0 | Baseline and guardrails | Done | Make the repository honest, testable, and safe to build on. |
| M0.5 | Developer environment | In progress | Provide one working devcontainer for application development. |
| M1 | Structured output and GBNF | Planned | Enforce the LLM response contract before execution. |
| M2 | Ports, adapters, action catalog | Planned | Separate orchestration from NAOqi and LLM details. |
| M3 | Runtime robustness and safety | Planned | Make reconnects, timeouts, shutdown, and action execution predictable. |
| M4 | Voice activity detection | Planned | Replace the current speech trigger with a proper VAD pipeline. |
| M5 | Simulation (SIL) | Planned | Run conversation and action flows without physical hardware. |
| M6 | Security hardening | Planned | Reduce the attack surface and document the threat model. |
| M7 | ROS2, Piper, vision | Deferred | Migrate to ROS2 and add new capabilities in a separate branch. |

## M0 — Baseline and guardrails

**Goal:** make the repository honest, testable, and safe to build on.

**Scope**

- Add `AGENTS.md` with project conventions.
- Turn `docs/adr/README.md` into an ADR index and add the initial ADRs.
- Add `ARCHITECTURE.md` with current-state diagrams and target boundaries.
- Rewrite this plan with milestones, acceptance criteria, and a test matrix.
- Define the initial LLM response contract in `docs/contracts/`.
- Fix the whisper URL in `.env.example`.
- Move the default system prompt to a tracked location included in the Docker image.
- Add `pyproject.toml`, `requirements-dev.txt`, `ruff`, `pytest`, and initial tests.
- Add a minimal GitHub Actions workflow.
- Persist `known_hosts.json` with a named Docker volume.
- Extend `.gitignore` for tool caches and model caches.

**Out of scope**

- GBNF enforcement (M1).
- Ports/adapters refactor (M2).
- Devcontainer unification (M0.5).
- Simulator choice (M5).
- ROS2 (M7).

**Acceptance criteria**

- `ruff check .` passes.
- `pytest` passes locally and in CI.
- A fresh production image contains `python/prompts/system_msg.txt`.
- `.env.example` matches the actual whisper and llama.cpp service ports.
- The ADR index links to every ADR file.
- The architecture document has current-state diagrams and a roadmap section.

**Verification note:** `ruff` and `pytest` were run locally during M0. The Docker image
build requires a Docker host and is verified separately.

## M0.5 — Developer environment

**Goal:** provide one documented development environment that can run the application,
linting, and tests.

**Status:** In progress. The unified Compose-based devcontainer is implemented; the Docker
image build still needs verification on a Docker host.

**Scope**

- Use the Docker Compose `dev` service as the only devcontainer so that the application,
  linting, and tests share one environment.
- Install `requirements-dev.txt`, `ruff`, `pytest`, and `openssh-client` in the `dev` image.
- Build the NAOqi Python bindings (`qi`) in the shared `builder` stage and install the
  resulting wheel in both `dev` and `production`.
- Pin the libqi-python release tag and the build tooling major versions.
- Install OpenCode through the Node devcontainer feature and pin the npm version.
- Persist OpenCode configuration in a named `opencode-data` volume.
- Document the long first build and the UID/GID expectation.

**Acceptance criteria**

- A new contributor can open the devcontainer and run `ruff check .` and `pytest`.
- The dev image can import `qi` and start `python/main.py`.
- The README does not claim that an environment works when it does not.
- The devcontainer configuration is tracked and reproducible.

**Verification note:** the Docker image build must run on a Docker host. It was not
verified from the sandbox used for the code changes.

## M1 — Structured output and GBNF

**Goal:** the LLM cannot return an invalid or partially parsed plan to the executor.

**Scope**

- Finalize `docs/contracts/llm-response.schema.json` as the source of truth.
- Add runtime models and validation (Pydantic or an equivalent typed model layer).
- Generate or derive the llama.cpp GBNF grammar from the schema.
- Send the constrained-output request through the OpenAI-compatible client.
- Validate action names and arguments against the action catalog.
- Add one repair attempt, then fail safe with speech and no actions.
- Fix the executor bug where `action` + `speak` drops the speech for actions that need a
  follow-up response.
- Remove the regex recovery path from normal execution.
- Add contract tests for valid, malformed, partial, and unknown-action responses.

**Acceptance criteria**

- An invalid response never reaches the executor.
- A combined `action` + `speak` step executes both parts.
- Contract examples validate against the schema.
- Tests cover the repair and fail-safe paths.
- ADR-0002 is updated if the implementation changes the decision.

## M2 — Ports, adapters, and action catalog

**Goal:** orchestration no longer depends directly on NAOqi or the OpenAI client.

**Scope**

- Introduce Python protocols for ASR, LLM, robot control, and action execution.
- Make `python/main.py` the composition root.
- Replace the global `ACTION_DESCRIPTIONS` registry with an explicit action catalog.
- Add action metadata: name, description, argument schema, result semantics, and whether
  the action needs a follow-up response.
- Move follow-up generation out of `StepExecutor` and into the conversation service.
- Add fake adapters for tests.
- Keep behaviour compatible with M1 tests.

**Acceptance criteria**

- `StepExecutor` does not import or know `LLMManager`.
- Adding an action requires only the action module and catalog registration.
- Unit tests run without NAOqi or a GPU.
- ADR-0003 boundaries are reflected in module dependencies.

## M3 — Runtime robustness and safety

**Goal:** the agent behaves predictably when the robot, LLM, ASR, or network fails.

**Scope**

- Introduce a conversation state machine (`IDLE`, `LISTENING`, `TRANSCRIBING`,
  `THINKING`, `ACTING`, `SPEAKING`, `RECONNECTING`).
- Add cancellation or a safe stop for timed-out actions.
- Add reconnect with backoff and cleanup of the previous session and SSH connection.
- Add an initial listening timeout and a maximum utterance duration.
- Add a maximum number of steps per plan.
- Add graceful shutdown and signal handling.
- Add Docker health checks and startup ordering for local inference services.
- Improve structured logging without logging secrets.

**Acceptance criteria**

- A timed-out action cannot continue silently while later steps run.
- A robot disconnect does not terminate the process unexpectedly.
- The process shuts down without leaving recordings, SSH sessions, or threads open.
- Compose starts the agent only after the inference services are healthy.

## M4 — Voice activity detection

**Goal:** detect speech reliably and reduce latency and false starts.

**Scope**

- Evaluate a VAD implementation (WebRTC VAD, Silero, or an NAOqi-native alternative).
- Decide between streamed audio and the current SFTP file transfer.
- Replace the current `ALSpeechRecognition`/`SpeechDetected` trigger where appropriate.
- Keep a fallback path for hardware limitations.
- Measure false positives, false negatives, and response latency.

**Acceptance criteria**

- The robot does not block forever when nobody speaks.
- Short utterances are captured reliably.
- The chosen approach is documented in an ADR.

## M5 — Simulation (SIL)

**Goal:** run the conversation and action flows without physical hardware.

**Scope**

- Implement a fake robot backend for CI first.
- Run a simulator spike: Webots vs Choregraphe virtual robot.
- Evaluate NAOqi API coverage, camera support, 3D environments, and ROS2 compatibility.
- Record the simulator decision in an ADR.
- Add a SIL test scenario for speech, LLM plan, and action execution.

**Acceptance criteria**

- A fake backend runs the full conversation flow in tests.
- The simulator choice is documented with trade-offs.
- No hardware-specific import leaks into unit tests.

## M6 — Security hardening

**Goal:** reduce the attack surface and document the security model.

**Scope**

- Review secrets handling; support SSH keys instead of the default password.
- Restrict or authenticate HTTP services if they are reachable outside the local host.
- Add prompt-injection guardrails for web search results and tool output.
- Add action allowlists, argument limits, and confirmation rules for risky physical actions.
- Add resource limits and container hardening.
- Write a threat model and a security checklist.

**Acceptance criteria**

- No secret is stored in the repository.
- A search result cannot directly cause an unconfirmed physical action.
- The threat model covers robot safety, network exposure, and prompt injection.

## M7 — ROS2, Piper, vision (deferred)

**Goal:** migrate to ROS2 and add new capabilities in a separate branch.

**Scope**

- Create a ROS2 branch and map the M2 boundaries to ROS2 nodes.
- Evaluate `naoqi_driver2`, `llama_ros`/`llava_ros`, `whisper_ros`, and `piper_ros`.
- Add SROS2 at the end of the security work.
- Replace NAOqi TTS with Piper behind the existing TTS/speaker abstraction.
- Add vision via llava.cpp or a local vision-language stack.
- Define topics and actions such as `/joint_states`, `/joint_angles`, and motion actions.

**Acceptance criteria**

- The ROS2 branch has its own architecture and migration ADRs.
- The current branch remains runnable until the ROS2 branch reaches parity.
- Security work includes SROS2 and a migration checklist.

## Test matrix

| Layer | What is tested | Location | Runs in CI |
|---|---|---|---|
| Unit | Config, prompt builder, parser, action metadata | `tests/unit/` | Yes |
| Contract | JSON Schema, examples, invalid LLM output | `tests/contract/` | Yes |
| Integration | Conversation flow with fake ASR/LLM/robot | `tests/integration/` | Yes |
| SIL | Simulator or fake backend end-to-end | `tests/sim/` | Later |
| HIL | Real NAO: audio, actions, reconnect, safety | Manual checklist | No |
| Security | Prompt injection, secrets, network exposure | Manual + targeted tests | Later |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| No robot available during development | Cannot verify NAOqi behaviour | Fake adapters, SIL, manual HIL checklist |
| Model or image drift | Behaviour changes between builds | Pin image digests and model versions |
| Prompt injection via web search | Unsafe physical action | Treat tool output as untrusted, action allowlist |
| NAOqi build fragility on Python 3.13 | Devcontainer and CI break | Pin libqi versions, document workaround |
| Scope creep into ROS2/vision too early | Nothing reaches production quality | Follow milestones; keep ROS2 in a separate branch |
| Simulator decision delayed | SIL blocked | Build fake backend first; decide in M5 |

## Out of scope for now

- Cloud inference.
- Full ROS2 rewrite.
- Webots or Choregraphe integration before M5.
- Piper TTS before M7.
- Vision/llava before M7.
- Multilingual conversation support.
- Kubernetes or multi-host orchestration.

## Definition of done

A milestone is done when:

1. Its scope is implemented.
2. Tests cover the new behaviour and pass in CI.
3. Documentation and ADRs are updated.
4. The application still starts and the previous milestone's acceptance criteria still hold.
5. Changes are committed in small, focused commits.
