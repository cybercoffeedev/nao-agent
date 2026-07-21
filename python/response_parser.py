"""Response parser - extracts and cleans text from LLM output."""

import re
from typing import Any


class ResponseParser:
    """Parses and cleans LLM response text for TTS output."""

    @staticmethod
    def parse_steps(raw: str) -> list[dict[str, Any]] | None:
        """Parse JSON array from LLM response, handling malformed output.

        Args:
            raw: Raw LLM response text.

        Returns:
            Parsed list of steps, or None if parsing fails.
        """
        import json

        try:
            result = json.loads(raw)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        for match in re.finditer(r"\[.*?\]", raw, re.DOTALL):
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                continue

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def clean_for_tts(raw: str) -> str:
        """Strip JSON fragments and action keywords from raw LLM output for TTS.

        Args:
            raw: Raw LLM response text.

        Returns:
            Cleaned text suitable for text-to-speech.
        """
        texts = re.findall(r'"speak"\s*:\s*"([^"]*)"', raw)
        if texts:
            return " ".join(texts)

        cleaned = re.sub(r"\[.*?\]", "", raw, flags=re.DOTALL)
        cleaned = re.sub(r"\{.*?\}", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'"(speak|action|args|query)"\s*:\s*', "", cleaned)
        cleaned = re.sub(r"\b(speak|action|args)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[{}\[\]\":]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def extract_speak_text(raw: str) -> str | None:
        """Extract speak text from LLM response.

        Args:
            raw: Raw LLM response text.

        Returns:
            Extracted speak text, or None if not found.
        """
        import json

        steps = ResponseParser.parse_steps(raw)
        if steps and isinstance(steps, list):
            for step in steps:
                if "speak" in step:
                    return step["speak"]
        return None
