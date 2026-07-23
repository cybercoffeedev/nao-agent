"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    robot_ip: str
    robot_port: int = 9559
    robot_username: str = ""
    robot_password: str = ""
    nvidia_api_key: str = ""
    whisper_url: str = ""
    openai_base_url: str = ""
    model: str = ""
    local_wav_path: str = "./capture.wav"
    ssh_port: int = 22

    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        required_fields = {
            "robot_ip": self.robot_ip,
            "nvidia_api_key": self.nvidia_api_key,
            "whisper_url": self.whisper_url,
            "openai_base_url": self.openai_base_url,
            "model": self.model,
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            raise ValueError(f"Required config fields are empty: {', '.join(missing)}")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Raises:
            ValueError: If required environment variables are missing.
        """
        return cls(
            robot_ip=os.environ.get("ROBOT_IP", ""),
            robot_port=int(os.getenv("ROBOT_PORT", "9559")),
            robot_username=os.getenv("ROBOT_USERNAME", ""),
            robot_password=os.getenv("ROBOT_PASSWORD", ""),
            nvidia_api_key=os.environ.get("NVIDIA_API_KEY", ""),
            whisper_url=os.environ.get("WHISPER_URL", ""),
            openai_base_url=os.environ.get("OPENAI_BASE_URL", ""),
            model=os.environ.get("MODEL", ""),
            ssh_port=int(os.getenv("SSH_PORT", "22")),
            local_wav_path=os.getenv("LOCAL_WAV_PATH", "./capture.wav"),
        )
