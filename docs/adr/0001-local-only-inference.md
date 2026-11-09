# ADR-0001: Local-only inference

- **Status:** Accepted
- **Date:** 2026-11-09
- **Deciders:** project owner
- **Related:** ADR-0002, `README.md`, `infra/compose.yml`

## Context

NAO Agent is intended to run as an experimental, educational robot assistant. The
conversation pipeline needs an LLM and a speech recognizer. A cloud API would be simple
to integrate, but it introduces:

- privacy and data-governance concerns for microphone audio and conversation text;
- recurring cost and dependency on network availability;
- unpredictable latency for a real-time voice interaction;
- a vendor lock-in risk for a long-lived robotics project.

The target machine already has a local NVIDIA GPU suitable for small and medium models.

## Decision

All production inference runs locally:

- **LLM:** llama.cpp server with an OpenAI-compatible API;
- **ASR:** whisper.cpp server with an HTTP inference endpoint.

The application communicates with both services over HTTP inside the Docker Compose
network. `OPENAI_BASE_URL` points to the local llama.cpp server. `OPENAI_API_KEY` is a
compatibility placeholder required by the OpenAI Python client, not a cloud credential.

A cloud provider may be used for experiments, but it must not become a runtime
dependency of the production stack.

## Consequences

### Positive

- Audio and conversation data stay on the local network.
- No per-token cost and no network dependency during operation.
- Reproducible deployment once model and image versions are pinned.
- The same OpenAI-compatible interface can be reused with another local server.

### Negative

- The host needs a capable GPU and enough VRAM.
- Model quality is bounded by the locally hosted model.
- Model downloads, updates, and cache management are operational work.
- The project owns the latency, health checks, and failure handling of both services.

### Follow-up

- Pin llama.cpp and whisper.cpp image digests.
- Add service health checks and startup ordering.
- Keep the model name and endpoint configurable through environment variables.
- Revisit hybrid inference only if a concrete requirement justifies it.

## Alternatives considered

- **Cloud LLM/ASR:** rejected for privacy, cost, latency, and availability reasons.
- **Hybrid local/cloud fallback:** deferred; it doubles the operational surface and
  weakens the privacy guarantee.
- **Direct in-process inference:** rejected for now; separate servers give process
  isolation, independent restarts, and a stable HTTP contract.

## References

- `infra/compose.yml` — local inference services.
- `python/config.py` — endpoint configuration.
- `python/agent/llm.py` — OpenAI-compatible client.
- `python/agent/asr.py` — whisper.cpp client.
