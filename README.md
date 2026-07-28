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

Open the project in VS Code and reopen in the dev container (uses `.devcontainer/devcontainer.json`).

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `ROBOT_IP` | — | NAO robot IP address |
| `ROBOT_PORT` | `9559` | NAOqi port |
| `ROBOT_USERNAME` | `nao` | SSH username |
| `ROBOT_PASSWORD` | `nao` | SSH password |
| `WHISPER_URL` | — | whisper.cpp server URL |
| `OPENAI_BASE_URL` | — | LLM API base URL |
| `OPENAI_API_KEY` | `sk-no-key-required` | LLM API key |
| `MODEL` | `model` | LLM model name |
| `SSH_PORT` | `22` | SSH port for SFTP |
| `LOCAL_WAV_PATH` | `./capture.wav` | Downloaded audio path |

System prompt (`data/system_msg.txt`) — editable file that sets the LLM's language, role, and behavior

## Adding Actions

Decorate a method in `python/robot/actions.py` with `@action("description")`:

```python
@action("Wave the right hand")
def wave_right_hand(self, duration: int = 3) -> str:
    ...
```

The LLM receives action descriptions automatically and can invoke them via structured JSON steps.


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
