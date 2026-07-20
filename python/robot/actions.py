import inspect


def action(description):
    """Decorator that registers a method as an available robot action."""
    def decorator(func):
        func._action_description = description
        return func
    return decorator

class RobotActions:
    """Manages robot actions like waving, sitting, standing, etc."""

    def __init__(self, posture, motion, memory, battery, background_movement, listening_movement, basic_awareness):
        self.posture = posture
        self.motion = motion
        self.memory = memory
        self.battery = battery
        self.background_movement = background_movement
        self.listening_movement = listening_movement
        self.basic_awareness = basic_awareness
        self._actions = {
            name: method._action_description
            for name, method in self.__class__.__dict__.items()
            if callable(method) and hasattr(method, "_action_description")
        }

    def get_tool_schemas(self):
        """Generate OpenAI function schemas for all registered actions."""
        tools = []
        for name, description in self._actions.items():
            method = getattr(self, name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())

            properties = {}
            required = []
            for param_name in params:
                properties[param_name] = {"type": "string"}
                required.append(param_name)

            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        return tools

    @action("Wave your right hand in greeting.")
    def wave_right_hand(self):
        family = self.posture.getPostureFamily()
        if family in ("LyingBelly", "LyingBack"):
            return "Cannot wave while lying down."
        names = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RWristYaw"]
        time_lists = [[1.5, 1.75, 2, 2.35, 2.75, 3, 4.5] for _ in range(4)]
        angle_lists = [
            [  -1,   -1,   -1,   -1,   -1,   -1,  1.5],
            [-0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.3],
            [ 1.3,  0.2,  1.2,  0.2,  1.2,  0.2,  0.5],
            [ 0.5, -0.5,  0.5, -0.5,  0.5, -0.5,  0.0]
        ]
        self.motion.angleInterpolation(names, angle_lists, time_lists, True)
        return "Waved right hand."

    @action("Check the robot's current posture.")
    def get_posture(self):
        return f"Current posture: {self.posture.getPostureFamily()}"

    def _set_autonomous_moves(self, enabled: bool):
        """Enable or disable all autonomous movement services."""
        self.background_movement.setEnabled(enabled)
        self.listening_movement.setEnabled(enabled)
        self.basic_awareness.setEnabled(enabled)

    @action("Make the robot sit down.")
    def sit_down(self):
        family = self.posture.getPostureFamily()
        if family == "Sitting":
            return "Already sitting."
        self._set_autonomous_moves(True)
        self.posture.goToPosture("Sit", 0.8)
        return "Sat down."

    @action("Make the robot stand up.")
    def stand_up(self):
        family = self.posture.getPostureFamily()
        if family == "Standing":
            return "Already standing."
        self._set_autonomous_moves(True)
        self.posture.goToPosture("StandInit", 0.8)
        return "Stood up."

    @action("Make the robot lie down on its stomach.")
    def lie_on_stomach(self):
        family = self.posture.getPostureFamily()
        if family == "LyingBelly":
            return "Already lying on stomach."
        self._set_autonomous_moves(False)
        self.posture.goToPosture("LyingBelly", 0.8)
        return "Lying on stomach."

    @action("Make the robot lie down on its back.")
    def lie_on_back(self):
        family = self.posture.getPostureFamily()
        if family == "LyingBack":
            return "Already lying on back."
        self._set_autonomous_moves(False)
        self.posture.goToPosture("LyingBack", 0.8)
        return "Lying on back."

    @action("Check the robot's status including battery, charging state, and CPU temperature.")
    def get_status(self):
        battery = self.battery.getBatteryCharge()
        current = self.memory.getData("Device/SubDeviceList/Battery/Current/Sensor/Value")
        cpu_temp = self.memory.getData("Device/SubDeviceList/Head/Temperature/Sensor/Value")
        try:
            is_charging = float(current) > 0
            charging_state = "Charging" if is_charging else "On battery"
        except (ValueError, TypeError):
            charging_state = "Unknown"
        try:
            cpu_temp = round(float(cpu_temp), 1)
        except (ValueError, TypeError):
            cpu_temp = "N/A"
        return f"Battery: {battery}% ({charging_state}), CPU temp: {cpu_temp}°C"

    @action("Search the internet for information. Use this when you need to find current data, facts, or answers to questions.")
    def web_search(self, query: str):
        """Searches the internet using DuckDuckGo."""
        from ddgs import DDGS
        try:
            results = DDGS(timeout=10).text(query, max_results=3)
            if results:
                output = []
                for r in results:
                    output.append(f"{r['title']}: {r['body']}")
                return "\n".join(output)
            return "No results found."
        except Exception as e:
            return f"Search error: {e}"

    def execute(self, name: str, *args, **kwargs):
        """Executes a named action."""
        if name in self._actions:
            method = getattr(self, name)
            if kwargs:
                return method(**kwargs)
            params = list(inspect.signature(method).parameters.keys())
            if len(args) < len(params):
                return f"Action '{name}' requires {len(params)} argument(s): {', '.join(params)}"
            return method(*args)
        return f"Unknown action: {name}"
