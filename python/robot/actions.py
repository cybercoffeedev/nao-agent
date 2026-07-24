"""Manages robot actions like waving, sitting, standing, etc."""

import inspect
from typing import Any, Callable


def action(description: str) -> Callable:
    """Decorator that registers a method as an available robot action."""

    def decorator(func: Callable) -> Callable:
        func._action_description = description  # type: ignore[attr-defined]
        return func

    return decorator


def get_action_descriptions() -> dict[str, str]:
    """Return action names and descriptions from @action decorators."""
    return {
        name: method._action_description  # type: ignore[attr-defined]
        for name, method in RobotActions.__dict__.items()
        if callable(method) and hasattr(method, "_action_description")
    }


class RobotActions:
    """Manages robot actions like waving, sitting, standing, etc."""

    def __init__(self, session: Any) -> None:
        """Initialize robot actions with AL services.

        Args:
            session: Active NAOqi session.
        """
        self.posture = session.service("ALRobotPosture")
        self.motion = session.service("ALMotion")
        self.memory = session.service("ALMemory")
        self.battery = session.service("ALBattery")
        self.background_movement = session.service("ALBackgroundMovement")
        self.listening_movement = session.service("ALListeningMovement")
        self.basic_awareness = session.service("ALBasicAwareness")

    @action("Wave your right hand in greeting.")
    def wave_right_hand(self) -> str:
        """Wave the robot's right hand."""
        family: str = self.posture.getPostureFamily()
        if family in ("LyingBelly", "LyingBack"):
            return "Cannot wave while lying down."
        names = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RWristYaw"]
        time_lists = [[1.5, 1.75, 2, 2.35, 2.75, 3, 4.5] for _ in range(4)]
        angle_lists = [
            [-1, -1, -1, -1, -1, -1, 1.5],
            [-0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.3],
            [1.3, 0.2, 1.2, 0.2, 1.2, 0.2, 0.5],
            [0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.0],
        ]
        self.motion.angleInterpolation(names, angle_lists, time_lists, True)
        return "Waved right hand."

    @action("Check the robot's current posture.")
    def get_posture(self) -> str:
        """Get the current posture of the robot."""
        return f"Current posture: {self.posture.getPostureFamily()}"

    def _set_autonomous_moves(self, enabled: bool) -> None:
        """Enable or disable all autonomous movement services."""
        self.background_movement.setEnabled(enabled)
        self.listening_movement.setEnabled(enabled)
        self.basic_awareness.setEnabled(enabled)

    @action("Make the robot sit down.")
    def sit_down(self) -> str:
        """Make the robot sit down."""
        family: str = self.posture.getPostureFamily()
        if family == "Sitting":
            return "Already sitting."
        self._set_autonomous_moves(True)
        self.posture.goToPosture("Sit", 0.8)
        return "Sat down."

    @action("Make the robot stand up.")
    def stand_up(self) -> str:
        """Make the robot stand up."""
        family: str = self.posture.getPostureFamily()
        if family == "Standing":
            return "Already standing."
        self._set_autonomous_moves(True)
        self.posture.goToPosture("StandInit", 0.8)
        return "Stood up."

    @action("Make the robot lie down on its stomach.")
    def lie_on_stomach(self) -> str:
        """Make the robot lie on stomach."""
        family: str = self.posture.getPostureFamily()
        if family == "LyingBelly":
            return "Already lying on stomach."
        self._set_autonomous_moves(False)
        self.posture.goToPosture("LyingBelly", 0.8)
        return "Lying on stomach."

    @action("Make the robot lie down on its back.")
    def lie_on_back(self) -> str:
        """Make the robot lie on back."""
        family: str = self.posture.getPostureFamily()
        if family == "LyingBack":
            return "Already lying on back."
        self._set_autonomous_moves(False)
        self.posture.goToPosture("LyingBack", 0.8)
        return "Lying on back."

    @action("Check the robot's status including battery, charging state, and CPU temperature.")
    def get_status(self) -> str:
        """Get robot status including battery and temperature."""
        battery: int = self.battery.getBatteryCharge()
        current: Any = self.memory.getData(
            "Device/SubDeviceList/Battery/Current/Sensor/Value"
        )
        cpu_temp: Any = self.memory.getData(
            "Device/SubDeviceList/Head/Temperature/Sensor/Value"
        )
        try:
            is_charging: bool = float(current) > 0
            charging_state = "Charging" if is_charging else "On battery"
        except (ValueError, TypeError):
            charging_state = "Unknown"
        try:
            cpu_temp = round(float(cpu_temp), 1)
        except (ValueError, TypeError):
            cpu_temp = "N/A"
        return f"Battery: {battery}% ({charging_state}), CPU temp: {cpu_temp}°C"

    @action(
        "Search the internet for information. "
        "Use this when you need to find current data, facts, or answers to questions."
    )
    def web_search(self, query: str) -> str:
        """Search the internet using DuckDuckGo."""
        from ddgs import DDGS

        try:
            results: list[dict] = DDGS(timeout=10).text(query, max_results=3)
            if results:
                return "\n".join(r["body"] for r in results)
            return "No results found."
        except (OSError, ValueError) as e:
            return f"Search error: {e}"

    def execute(self, name: str, *args: Any, **kwargs: Any) -> str:
        """Execute a named action.

        Args:
            name: Name of the action to execute.
            *args: Positional arguments for the action.
            **kwargs: Keyword arguments for the action.

        Returns:
            Action result string.
        """
        if name not in ACTION_DESCRIPTIONS:
            return f"Unknown action: {name}"

        method = getattr(self, name)
        if kwargs:
            return method(**kwargs)

        params = list(inspect.signature(method).parameters.keys())
        if len(args) < len(params):
            return f"Action '{name}' requires {len(params)} argument(s): {', '.join(params)}"
        if len(args) > len(params):
            return f"Action '{name}' takes {len(params)} argument(s), got {len(args)}"
        return method(*args)


ACTION_DESCRIPTIONS: dict[str, str] = get_action_descriptions()
