# NAO Agent

An AI-powered voice assistant agent for the **SoftBank NAO v6 humanoid robot**. It listens for speech via the robot's microphone, transcribes it with Whisper, processes the request through a local LLM (OpenAI-compatible API), and executes actions on the robot.

## Prerequisites

- SoftBank NAO v6 robot on the same network (or a NAOqi simulator)
- Docker with NVIDIA Container Toolkit (for GPU-accelerated inference)

## Quick Start (Production)

```bash
cd infra
# Edit .env with your ROBOT_IP
docker compose up -d
```

This starts three services:
- `llama-server` (port 8080) — LLM inference with Qwen2.5-14B
- `whisper-server` (port 8081) — speech recognition with large-v3-turbo
- `nao-agent` — the agent itself

## Development

### VS Code Dev Container

The current `.devcontainer/devcontainer.json` is a lightweight OpenCode workspace and does
not include NAOqi. For the full application environment, use the `dev` Docker target:

```bash
docker compose run --rm dev
```

Unifying the devcontainer with the application environment is tracked in
[`docs/plans/README.md`](docs/plans/README.md) as milestone M0.5.

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `ROBOT_IP` | — | NAO robot IP address |
| `ROBOT_PORT` | `9559` | NAOqi port |
| `ROBOT_USERNAME` | `nao` | SSH username |
| `ROBOT_PASSWORD` | `nao` | SSH password |
| `WHISPER_URL` | `http://whisper-server:8081` | whisper.cpp server URL |
| `OPENAI_BASE_URL` | `http://llama-server:8080/v1` | Local OpenAI-compatible API base URL |
| `OPENAI_API_KEY` | `dummy` | Compatibility placeholder; no cloud key is used |
| `MODEL` | `model` | Model name sent to llama.cpp |
| `SSH_PORT` | `22` | SSH port for SFTP |
| `LOCAL_WAV_PATH` | `./capture.wav` | Downloaded audio path |

System prompt (`python/prompts/system_msg.txt`) — tracked, editable file that sets the
LLM's language, role, and behaviour. It is packaged into the production image.

## Adding Actions

Decorate a method in `python/robot/actions.py` with `@action("description")`:

```python
@action("Wave the right hand")
def wave_right_hand(self) -> str:
    ...
```

The LLM receives action descriptions automatically and can invoke them via structured JSON steps.

## Documentation

- [`docs/plans/README.md`](docs/plans/README.md) — milestones, status, and test matrix
- [`docs/adr/README.md`](docs/adr/README.md) — architecture decision records
- [`docs/contracts/README.md`](docs/contracts/README.md) — LLM response contract
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — current architecture and target boundaries
- [`AGENTS.md`](AGENTS.md) — contribution and agent conventions

## Testing

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

The GitHub Actions workflow runs the same checks on pull requests and pushes to `main`.


## Tech Stack

| Technology | Role |
|---|---|
| Python 3.13 | Application language |
| NAOqi (libqi-python) | SoftBank NAO robot SDK |
| OpenAI Python SDK | LLM API client |
| whisper.cpp | On-device speech recognition |
| llama.cpp | On-device LLM inference |
| paramiko | SSH/SFTP audio transfer |
| httpx | HTTP client |
| ddgs | DuckDuckGo web search |
| Docker Compose | Service orchestration |

**Language support:** Currently only Polish is fully supported (system prompt, ASR language model, speech recognition vocabulary).
**Tested with:** Qwen2.5-14B-Instruct (Q4_K_M) + whisper-large-v3-turbo (Q5_0) on NVIDIA Quadro RTX 6000 (24 GB VRAM).

---

> **Disclaimer**: This project is **experimental** and intended **for educational and research purposes only**. It was developed under a very tight deadline, which significantly impacted the overall quality, structure, and completeness of the codebase. Use at your own risk. It may contain bugs, incomplete features, security limitations, or unexpected behavior. The author assume no responsibility for any damage or injury caused by operating a physical robot with this software. Always supervise the robot and have a hard stop mechanism available. This is not a production-ready system.
