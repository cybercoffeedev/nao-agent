import qi

class RobotEyes:
    """Manages the NAO robot's face LED animations using ALLeds service."""
    def __init__(self, session: qi.Session):
        """Initializes the visual eye indicators on the robot.

        Args:
            session (qi.Session): Active session connected to the NAO robot.
        """
        session.service("ALAutonomousBlinking").setEnabled(False)
        self.leds = session.service("ALLeds")
        self.leds_list = [f"FaceLed{i}" for i in range(8)]
        self.task = qi.PeriodicTask()
        self.task.setCallback(self._tick)
        self.task.setUsPeriod(100000)
        self.mode = None
        self.step = 0

    def _tick(self):
        """Callback step executed periodically by qi.PeriodicTask to update LEDs."""
        if self.mode == "listening":
            self.leds.fadeRGB("FaceLeds", 0x0000FFFF, 0.0)
        elif self.mode == "thinking":
            for i, intensity in enumerate((1.0, 0.6, 0.2, 0.0)):
                self.leds.setIntensity(self.leds_list[(self.step - i) % 8], intensity)
            self.step += 1

    def set(self, mode: str | None):
        """Changes the current eye animation mode.

        Args:
            mode (str | None): Target animation mode or None to deactivate.
        """
        self.task.stop()
        self.mode = mode
        if mode:
            self.step = 0
            self.task.start(True)
        else:
            self.leds.setIntensity("FaceLeds", 1.0)
