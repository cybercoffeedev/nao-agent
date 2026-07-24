"""Manages the NAO robot's face LED animations using ALLeds service."""

import threading

import qi

LED_UPDATE_PERIOD_US: int = 100_000
FACE_LEDS_COUNT: int = 8
SPEAK_HEX_YELLOW: int = 0x0000FFFF
LED_INTENSITIES: tuple[float, ...] = (1.0, 0.6, 0.2, 0.0)


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
        self._lock = threading.Lock()
        self.mode: str | None = None
        self._active_mode: str | None = None
        self.step: int = 0
        self._running: bool = False

    def _tick(self) -> None:
        """Callback step executed periodically by qi.PeriodicTask to update LEDs."""
        try:
            with self._lock:
                mode = self.mode
                step = self.step
                active_mode = self._active_mode

            if mode is None:
                return

            if mode == "listening":
                if active_mode != "listening":
                    self.leds.fadeRGB("FaceLeds", SPEAK_HEX_YELLOW, 0.0)
                    with self._lock:
                        self._active_mode = "listening"
            elif mode == "thinking":
                if active_mode != "thinking":
                    with self._lock:
                        self.step = 0
                        self._active_mode = "thinking"
                    step = 0
                for i, intensity in enumerate(LED_INTENSITIES):
                    self.leds.setIntensity(
                        self.leds_list[(step - i) % FACE_LEDS_COUNT], intensity
                    )
                with self._lock:
                    if self.mode == mode:
                        self.step = step + 1
        except RuntimeError:
            pass

    def set(self, mode: str | None) -> None:
        """Change the current eye animation mode.

        Args:
            mode: Target animation mode or None to deactivate.
        """
        with self._lock:
            was_running = self._running
            self.mode = mode
            self._active_mode = None
            self.step = 0
            self._running = mode is not None

        if was_running:
            self.task.stop()

        if not mode:
            self.leds.setIntensity("FaceLeds", 1.0)
        else:
            self.task.start(True)
            with self._lock:
                if not self._running:
                    self.task.stop()
