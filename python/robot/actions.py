def action(description):
    """Decorator that registers a method as an available robot action."""
    def decorator(func):
        func._action_description = description
        return func
    return decorator

class RobotActions:
    """Manages robot actions like waving, sitting, standing, etc."""

    def __init__(self, posture, motion, memory, battery):
        self.posture = posture
        self.motion = motion
        self.memory = memory
        self.battery = battery
        self._actions = {
            name: method._action_description
            for name, method in self.__class__.__dict__.items()
            if callable(method) and hasattr(method, "_action_description")
        }

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

    @action("Make the robot sit down.")
    def sit_down(self):
        family = self.posture.getPostureFamily()
        if family == "Sitting":
            return "Already sitting."
        self.posture.goToPosture("Sit", 0.8)
        return "Sat down."

    @action("Make the robot stand up.")
    def stand_up(self):
        family = self.posture.getPostureFamily()
        if family == "Standing":
            return "Already standing."
        self.posture.goToPosture("StandInit", 0.8)
        return "Stood up."

    @action("Make the robot lie down on its stomach.")
    def lie_on_stomach(self):
        family = self.posture.getPostureFamily()
        if family == "LyingBelly":
            return "Already lying on stomach."
        self.posture.goToPosture("LyingBelly", 0.8)
        return "Lying on stomach."

    @action("Make the robot lie down on its back.")
    def lie_on_back(self):
        family = self.posture.getPostureFamily()
        if family == "LyingBack":
            return "Already lying on back."
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

    def execute(self, name: str):
        """Executes a named action."""
        if name in self._actions:
            return getattr(self, name)()
        return f"Unknown action: {name}"
