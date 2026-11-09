# ADR-0003: Modular monolith with ROS2-ready boundaries

- **Status:** Accepted
- **Date:** 2026-11-09
- **Deciders:** project owner
- **Related:** `ARCHITECTURE.md`, `docs/plans/README.md`

## Context

The current code is a single Python application with a `Robot` facade, an agent loop,
LLM/ASR clients, and action execution. It works, but responsibilities are mixed and a
future ROS2 migration would otherwise require a large rewrite.

The target direction discussed by the project owner uses ROS2-style components such as
`nao_audio_pipeline`, `nao_state_manager`, `nao_conversation`, `nao_intent_parser`,
`nao_intent_dispatcher`, `nao_motion_executor`, `nao_bringup`, and a possible `nao_sim`.

## Decision

Keep a **modular monolith** for the current branch and prepare boundaries that map cleanly
to future ROS2 nodes.

1. Do not introduce ROS2, `rclpy`, ROS messages, or ROS topics in the current branch.
2. Introduce Python protocols and adapters for audio, ASR, LLM, robot control, and action
   execution. The composition root in `python/main.py` selects concrete adapters.
3. Use the future ROS2 package names as a design vocabulary, not as a premature package
   structure. The mapping is:

   | Future ROS2 package | Responsibility | Current modules |
   |---|---|---|
   | `nao_audio_pipeline` | Microphone capture, VAD, ASR | `robot/audio.py`, `agent/asr.py`, `agent/speech_detector.py` |
   | `nao_state_manager` | Connection, posture, battery, health | `robot/robot.py`, parts of `robot/actions.py` |
   | `nao_conversation` | Conversation loop and state machine | `agent/agent.py` |
   | `nao_intent_parser` | LLM contract validation | `agent/response_parser.py`, `agent/llm.py` |
   | `nao_intent_dispatcher` | Routing validated intents | `agent/step_executor.py` |
   | `nao_motion_executor` | NAOqi motion and LED execution | `robot/actions.py`, `robot/eyes.py` |
   | `nao_bringup` | Configuration and composition | `python/main.py`, `python/config.py`, Docker |
   | `nao_sim` | Simulator adapter | Not implemented yet |

4. The simulator choice is deferred. A fake backend for tests comes first; Webots is the
   preferred candidate for a realistic SIL environment, but no simulator dependency is
   added until milestone M5.
5. The actual ROS2 migration happens in a separate branch after the contract, adapters,
   and runtime robustness are stable. Topic names such as `/joint_states`,
   `/joint_angles`, and `/cmd_vel` are deferred to that branch.

## Consequences

### Positive

- No big-bang rewrite; each boundary can be introduced and tested incrementally.
- The ROS2 migration becomes an adapter/node-wiring exercise rather than a redesign.
- Unit tests can run without NAOqi, ROS2, or a robot.
- The same contract can later be reused as a ROS2 message or action definition.

### Negative

- Some names and boundaries are provisional until the ROS2 design is validated.
- The team must resist creating ROS2 abstractions before there is a second implementation.
- The simulator decision remains open and can affect the `nao_sim` boundary.

### Follow-up

- M2: introduce protocols and the action catalog.
- M5: decide the simulator and implement the fake backend first.
- M7: create the ROS2 branch, map nodes to the boundaries above, and add SROS2 at the end.

## Alternatives considered

- **Migrate to ROS2 immediately:** rejected; it would multiply the current complexity
  before the contracts and tests are in place.
- **Keep the current structure and rewrite later:** rejected; it repeats the same coupling
  and makes the migration harder.
- **Choregraphe virtual robot as the only SIL path:** not chosen as the primary path;
  it is useful for quick NAOqi checks but is legacy and less representative for 3D
  environments and future vision work.
- **Webots now:** deferred until M5; it is the preferred candidate but needs a concrete
  integration spike before commitment.

## References

- `ARCHITECTURE.md`
- `docs/plans/README.md`
- `python/agent/step_executor.py`
- `python/robot/robot.py`
