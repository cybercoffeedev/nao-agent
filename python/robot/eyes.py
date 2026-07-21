"""Manages the NAO robot's face LED animations using ALLeds service."""

import qi

LED_UPDATE_PERIOD_US: int = 100_000
FACE_LEDS_COUNT: int = 8
SPEAK_HEX_YELLOW: int = 0x0000FFFF


class RobotEyes:
    """Manages the NAO robot's face LED animations using ALLeds service."""

    def __init__(self, session: qi.Session) -> None:
        """Initialize the visual eye indicators on the robot.

        Args:
            session: Active session connected to the NAO robot.
        """
        session.service("ALAutonomousBlinking").setEnabled(False)
        self.leds = session.service("ALLeds")
        self.leds_list: list[str] = [f"FaceLed{i}" for i in range(FACE_LEDS_COUNT)]
        self.task = qi.PeriodicTask()
        self.task.setCallback(self._tick)
        self.task.setUsPeriod(LED_UPDATE_PERIOD_US)
        self.mode: str | None = None
        self.step: int = 0

    def _tick(self) -> None:
        """Callback step executed periodically by qi.PeriodicTask to update LEDs."""
        try:
            if self.mode == "listening":
                self.leds.fadeRGB("FaceLeds", SPEAK_HEX_YELLOW, 0.0)
            elif self.mode == "thinking":
                for i, intensity in enumerate((1.0, 0.6, 0.2, 0.0)):
                    self.leds.setIntensity(
                        self.leds_list[(self.step - i) % FACE_LEDS_COUNT], intensity
                    )
                self.step += 1
        except RuntimeError:
            pass

    def set(self, mode: str | None) -> None:
        """Change the current eye animation mode.

        Args:
            mode: Target animation mode or None to deactivate.
        """
        self.task.stop()
        self.mode = mode
        if mode:
            self.step = 0
            self.task.start(True)
        else:
            self.leds.setIntensity("FaceLeds", 1.0)
