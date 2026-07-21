"""Step executor - executes parsed action steps."""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from .llm import LLMManager
from .response_parser import ResponseParser
from ..robot import Robot

logger = logging.getLogger(__name__)

TOOL_TIMEOUT: int = 30
ACTIONS_NEEDING_RESPONSE: frozenset[str] = frozenset({"web_search"})


class StepExecutor:
    """Executes parsed action steps from LLM responses."""

    def __init__(self, robot: Robot, llm: LLMManager) -> None:
        """Initialize step executor.

        Args:
            robot: Robot instance for executing actions.
            llm: LLM manager for adding context and generating responses.
        """
        if robot is None:
            raise ValueError("robot cannot be None")
        if llm is None:
            raise ValueError("llm cannot be None")

        self.robot = robot
        self.llm = llm
        self.parser = ResponseParser()

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
                try:
                    return future.result(timeout=TOOL_TIMEOUT)
                except FuturesTimeoutError:
                    future.cancel()
                    result = f"Timeout after {TOOL_TIMEOUT}s"
                    logger.warning(result)
                    return result
        except Exception as e:
            result = f"Error: {e}"
            logger.error(result)
            return result

    def _speak_response(self, steps: list[dict] | None, raw: str) -> None:
        """Extract and speak text from LLM response without executing actions.

        Args:
            steps: Already parsed steps (to avoid double parsing).
            raw: Raw LLM response text for fallback cleaning.
        """
        if steps:
            for step in steps:
                if "speak" in step:
                    self.robot.set_eyes(None)
                    self.robot.speak(step["speak"])
                    return

        cleaned = self.parser.clean_for_tts(raw)
        if cleaned:
            self.robot.set_eyes(None)
            self.robot.speak(cleaned)

    def execute(self, raw: str) -> None:
        """Parse JSON steps from LLM and execute them.

        Steps: {"speak": "text"} or {"action": "name", "args": {...}}
        For ACTIONS_NEEDING_RESPONSE: executes, adds result to context,
        then generates response from LLM.

        Args:
            raw: Raw LLM response text containing steps.
        """
        steps = self.parser.parse_steps(raw)

        if not steps or not isinstance(steps, list):
            cleaned = self.parser.clean_for_tts(raw)
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
                response_steps = self.parser.parse_steps(response)
                self._speak_response(response_steps, response)
