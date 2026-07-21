import time
import json
import re
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from robot import Robot
from asr import RivaASR
from llm import LLMManager

logger = logging.getLogger(__name__)

TOOL_TIMEOUT = 30
ACTIONS_NEEDING_RESPONSE = {"web_search"}


class RobotAgent:
    def __init__(self, robot: Robot, asr: RivaASR, llm: LLMManager):
        self.robot = robot
        self.asr = asr
        self.llm = llm

    def listen_for_speech(self):
        speech_started = False
        silence_start = None

        self.robot.audio.start_recording()
        while True:
            speaking = self.robot.audio.is_speech_detected()
            if speaking:
                if not speech_started:
                    self.robot.set_eyes("listening")
                    speech_started = True
                silence_start = None
            elif speech_started:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= 1.5:
                    self.robot.set_eyes(None)
                    break
            time.sleep(0.1)
        self.robot.audio.stop_recording()

    def _parse_steps(self, raw: str):
        """Parses JSON array from LLM response, handling malformed output."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _execute_action(self, action_name, action_args):
        """Execute a single action. Returns result string."""
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

    def _execute_steps(self, raw: str):
        """Parses JSON steps from LLM and executes them.

        Steps: {"speak": "text"} or {"action": "name", "args": {...}}
        For ACTIONS_NEEDING_RESPONSE: executes, adds result to context,
        then generates response from LLM.
        """
        steps = self._parse_steps(raw)

        if not steps or not isinstance(steps, list):
            if raw.strip():
                self.robot.set_eyes(None)
                self.robot.speak(raw)
            return

        pending_response_needed = False

        for step in steps:
            if "speak" in step:
                self.robot.set_eyes(None)
                self.robot.speak(step["speak"])
            elif "action" in step:
                action_name = step["action"]
                action_args = step.get("args", {})
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
                self.robot.set_eyes(None)
                self.robot.speak(response)

    def run(self):
        self.robot.connect_to_robot()

        try:
            while True:
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
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.robot.disconnect()
