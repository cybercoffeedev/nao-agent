"""Robot agent - orchestrates speech, LLM and robot actions."""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from asr import RivaASR
from llm import LLMManager
from robot import Robot

logger = logging.getLogger(__name__)

TOOL_TIMEOUT: int = 30
SILENCE_THRESHOLD: float = 1.5
SPEECH_CHECK_INTERVAL: float = 0.1
ACTIONS_NEEDING_RESPONSE: frozenset[str] = frozenset({"web_search"})


class RobotAgent:
    """Orchestrates speech recognition, LLM and robot actions."""

    def __init__(self, robot: Robot, asr: RivaASR, llm: LLMManager) -> None:
        """Initialize the robot agent.

        Args:
            robot: Robot instance for controlling the NAO robot.
            asr: Speech recognition service.
            llm: Language model manager.
        """
        if robot is None:
            raise ValueError("robot cannot be None")
        if asr is None:
            raise ValueError("asr cannot be None")
        if llm is None:
            raise ValueError("llm cannot be None")

        self.robot = robot
        self.asr = asr
        self.llm = llm

    def listen_for_speech(self) -> None:
        """Listen for speech and stop after silence threshold."""
        speech_started = False
        silence_start: float | None = None

        self.robot.audio.start_recording()
        while True:
            speaking: bool = self.robot.audio.is_speech_detected()
            if speaking:
                if not speech_started:
                    self.robot.set_eyes("listening")
                    speech_started = True
                silence_start = None
            elif speech_started:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= SILENCE_THRESHOLD:
                    self.robot.set_eyes(None)
                    break
            time.sleep(SPEECH_CHECK_INTERVAL)
        self.robot.audio.stop_recording()

    def _parse_steps(self, raw: str) -> list[dict] | None:
        """Parse JSON array from LLM response, handling malformed output.

        Args:
            raw: Raw LLM response text.

        Returns:
            Parsed list of steps, or None if parsing fails.
        """
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

    def _execute_action(self, action_name: str, action_args: dict) -> str:
        """Execute a single action with timeout.

        Args:
            action_name: Name of the action to execute.
            action_args: Arguments to pass to the action.

        Returns:
            Action result string.
        """
        logger.info("Executing: %s %s", action_name, action_args or "")
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self.robot.execute_action, action_name, **action_args
                )
                return future.result(timeout=TOOL_TIMEOUT)
        except FuturesTimeoutError:
            result = f"Timeout after {TOOL_TIMEOUT}s"
            logger.warning(result)
            return result
        except Exception as e:
            result = f"Error: {e}"
            logger.error(result)
            return result

    def _execute_steps(self, raw: str) -> None:
        """Parse JSON steps from LLM and execute them.

        Steps: {"speak": "text"} or {"action": "name", "args": {...}}
        For ACTIONS_NEEDING_RESPONSE: executes, adds result to context,
        then generates response from LLM.
        """
        steps = self._parse_steps(raw)

        if not steps or not isinstance(steps, list):
            cleaned = self._clean_raw_text(raw)
            if cleaned:
                self.robot.set_eyes(None)
                self.robot.speak(cleaned)
            return

        pending_response_needed = False

        for step in steps:
            if "speak" in step:
                self.robot.set_eyes(None)
                self.robot.speak(step["speak"])
            elif "action" in step:
                action_name: str = step["action"]
                action_args: dict = step.get("args", {})
                result = self._execute_action(action_name, action_args)

                if action_name in ACTIONS_NEEDING_RESPONSE:
                    self.llm.add_user_message(f"[Wynik wyszukiwania: {result}]")
                    pending_response_needed = True
                else:
                    self.llm.add_user_message(f"[Wynik: {result}]")

        if pending_response_needed:
            self.robot.set_eyes("thinking")
            response = self.llm.generate_response()
            logger.info("LLM: %s", response[:200] if response else "")
            if response:
                self._speak_response(response)

    def _speak_response(self, raw: str) -> None:
        """Extract and speak text from LLM response without executing actions."""
        steps = self._parse_steps(raw)
        if steps and isinstance(steps, list):
            for step in steps:
                if "speak" in step:
                    self.robot.set_eyes(None)
                    self.robot.speak(step["speak"])
                    return
        cleaned = self._clean_raw_text(raw)
        if cleaned:
            self.robot.set_eyes(None)
            self.robot.speak(cleaned)

    @staticmethod
    def _clean_raw_text(raw: str) -> str:
        """Strip JSON fragments and action keywords from raw LLM output for TTS."""
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

    def run(self) -> None:
        """Main loop - listen, transcribe, generate, execute."""
        self.robot.connect_to_robot()

        try:
            while True:
                try:
                    self.listen_for_speech()
                    self.robot.audio.download_audio(self.robot.local_wav_path)
                    self.robot.set_eyes("thinking")

                    text = self.asr.transcribe_audio()
                    if text:
                        logger.info("User: %s", text)
                        self.llm.add_user_message(text)
                        response = self.llm.generate_response()
                        logger.info("LLM: %s", response[:200] if response else "")
                        self._execute_steps(response)
                    time.sleep(1.0)
                except RuntimeError as e:
                    if "Socket" in str(e) or "not connected" in str(e).lower():
                        logger.warning("Socket lost, reconnecting to robot...")
                        self.robot.reconnect()
                    else:
                        raise
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.robot.disconnect()
