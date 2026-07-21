"""LLM logger - logs requests and responses to JSON files."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent.parent / "logs"


class LLMLogger:
    """Logs LLM requests and responses to JSON files."""

    def __init__(self) -> None:
        """Initialize LLM logger and create log directory."""
        self._request_counter: int = 0
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, request_kwargs: dict, response_content: str | None) -> None:
        """Log LLM request/response to a JSON file.

        Args:
            request_kwargs: Request parameters including model and messages.
            response_content: The LLM response content.
        """
        self._request_counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{ts}_{self._request_counter:04d}.json"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": request_kwargs.get("model"),
            "request": {
                "messages": request_kwargs.get("messages"),
            },
            "response": {
                "content": response_content,
            },
        }

        try:
            path = LOG_DIR / filename
            path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not write LLM log: %s", e)
