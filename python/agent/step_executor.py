"""Step executor - executes parsed action steps."""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

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
            llm: Language model manager.
        """
        self.robot = robot
        self.llm = llm
        self._executor = ThreadPoolExecutor(max_workers=1)

    def shutdown(self) -> None:
        """Shut down the thread pool."""
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
        future = self._executor.submit(
            self.robot.execute_action, action_name, **action_args
        )
        try:
            return future.result(timeout=TOOL_TIMEOUT)
        except FuturesTimeoutError:
            logger.warning("Timeout after %ds for %s", TOOL_TIMEOUT, action_name)
            return f"Timeout after {TOOL_TIMEOUT}s"
        except Exception as e:
            logger.error("Error: %s", e)
            return f"Error: {e}"

    def _speak(self, text: str) -> None:
        """Turn off eyes and speak text."""
        self.robot.set_eyes(None)
        self.robot.speak(text)

    def _speak_raw_or_fallback(self, steps: list[dict] | None, raw: str) -> None:
        """Speak the first speak step found, or fall back to cleaned raw text.

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

    def _run_followup(self, action_results: list[str]) -> None:
        """Generate a follow-up response from the LLM and speak it inline.

        Used when an ACTIONS_NEEDING_RESPONSE action runs, so the spoken
        answer happens at the right point in the step sequence.

        Args:
            action_results: Results from actions just executed.
        """
        self.llm.add_user_message("\n".join(action_results))
        logger.info("Action results in context: %s", action_results)
        self.robot.set_eyes("thinking")
        response = self.llm.generate_response()
        self.llm.log_preview(response)
        if response:
            self._speak_raw_or_fallback(parse_steps(response), response)

    def execute(self, raw: str) -> None:
        """Parse JSON steps from LLM and execute them.

        Steps: {"speak": "text"} or {"action": "name", "args": {...}}
        For ACTIONS_NEEDING_RESPONSE: executes inline, then immediately runs
        a follow-up LLM call and speaks its answer. Subsequent steps continue
        from there, preserving the order requested by the user.

        Args:
            raw: Raw LLM response text containing steps.
        """
        steps = parse_steps(raw)

        if not steps or not isinstance(steps, list):
            self._speak_raw_or_fallback(None, raw)
            return

        action_results: list[str] = []

        for step in steps:
            if "action" in step:
                action_name: str = step["action"]
                action_args: dict = step.get("args", {})
                result = self._execute_action(action_name, action_args)
                self.robot.set_eyes(None)

                action_results.append(f"[Result: {result}]")
                if action_name in ACTIONS_NEEDING_RESPONSE:
                    self._run_followup(action_results)
                    action_results.clear()
                    continue

            if "speak" in step:
                self._speak(step["speak"])

        if action_results:
            self.llm.add_user_message("\n".join(action_results))
