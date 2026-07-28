"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    robot_ip: str
    robot_port: int = 9559
    robot_username: str = "nao"
    robot_password: str = "nao"
    whisper_url: str = "http://whisper-server:8081"
    openai_base_url: str = "http://llama-server:8080/v1"
    openai_api_key: str = "dummy"
    model: str = "model"
    local_wav_path: str = "./capture.wav"
    ssh_port: int = 22

    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        required_fields = {
            "robot_ip": self.robot_ip,
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            raise ValueError(f"Required config fields are empty: {', '.join(missing)}")

    @classmethod
    def from_env(cls) -> "Config":
        robot_ip = os.environ.get("ROBOT_IP", "")
        if not robot_ip:
            raise ValueError("ROBOT_IP environment variable is required")

        kwargs = {}
        for env_name, field_name, transform in [
            ("ROBOT_PORT", "robot_port", int),
            ("ROBOT_USERNAME", "robot_username", str),
            ("ROBOT_PASSWORD", "robot_password", str),
            ("WHISPER_URL", "whisper_url", str),
            ("OPENAI_BASE_URL", "openai_base_url", str),
            ("OPENAI_API_KEY", "openai_api_key", str),
            ("MODEL", "model", str),
            ("SSH_PORT", "ssh_port", int),
            ("LOCAL_WAV_PATH", "local_wav_path", str),
        ]:
            value = os.environ.get(env_name)
            if value is not None:
                kwargs[field_name] = transform(value)

        return cls(robot_ip=robot_ip, **kwargs)
