"""Step executor - executes parsed action steps."""

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from .llm import LLMManager
from .response_parser import parse_steps, clean_for_tts
from robot import Robot

logger = logging.getLogger(__name__)

TOOL_TIMEOUT: int = 30
ACTIONS_NEEDING_RESPONSE: frozenset[str] = frozenset({"web_search", "get_status", "get_posture"})


class StepExecutor:
    """Executes parsed action steps from LLM responses."""

    def __init__(self, robot: Robot, llm: LLMManager) -> None:
        """Initialize step executor.

        Args:
            robot: Robot instance for executing actions.
            llm: LLM manager for adding context and generating responses.
        """
        self.robot = robot
        self.llm = llm
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._abandoned_futures: list[Future] = []
        self._lock = threading.Lock()

    def shutdown(self) -> None:
        """Shut down the thread pool and cancel abandoned futures."""
        with self._lock:
            for future in self._abandoned_futures:
                future.cancel()
            self._abandoned_futures.clear()
        self._executor.shutdown(wait=True)

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
            future = self._executor.submit(
                self.robot.execute_action, action_name, **action_args
            )
            try:
                return future.result(timeout=TOOL_TIMEOUT)
            except FuturesTimeoutError:
                with self._lock:
                    self._abandoned_futures.append(future)
                result = f"Timeout after {TOOL_TIMEOUT}s"
                logger.warning(result)
                return result
        except Exception as e:
            result = f"Error: {e}"
            logger.error(result)
            return result

    def _speak(self, text: str) -> None:
        """Turn off eyes and speak text."""
        self.robot.set_eyes(None)
        self.robot.speak(text)

    def _speak_response(self, steps: list[dict] | None, raw: str) -> None:
        """Extract and speak text from LLM response without executing actions.

        Args:
            steps: Already parsed steps (to avoid double parsing).
            raw: Raw LLM response text for fallback cleaning.
        """
        if steps:
            for step in steps:
                if "speak" in step:
                    self._speak(step["speak"])
                    return

        cleaned = clean_for_tts(raw)
        if cleaned:
            self._speak(cleaned)

    def execute(self, raw: str) -> None:
        """Parse JSON steps from LLM and execute them.

        Steps: {"speak": "text"} or {"action": "name", "args": {...}}
        For ACTIONS_NEEDING_RESPONSE: executes, adds result to context,
        then generates response from LLM.

        Args:
            raw: Raw LLM response text containing steps.
        """
        steps = parse_steps(raw)

        if not steps or not isinstance(steps, list):
            self._speak_response(None, raw)
            return

        pending_response_needed = False
        action_results: list[str] = []

        for step in steps:
            if "action" in step:
                action_name: str = step["action"]
                action_args: dict = step.get("args", {})
                result = self._execute_action(action_name, action_args)
                self.robot.set_eyes(None)

                action_results.append(f"[Result: {result}]")
                if action_name in ACTIONS_NEEDING_RESPONSE:
                    pending_response_needed = True

            if "speak" in step:
                self._speak(step["speak"])

        if action_results:
            self.llm.add_user_message("\n".join(action_results))

        if pending_response_needed:
            self.robot.set_eyes("thinking")
            response = self.llm.generate_response()
            logger.info("LLM: %s", response[:200] if response else "")
            if response:
                response_steps = parse_steps(response)
                self._speak_response(response_steps, response)
            self.robot.set_eyes(None)
