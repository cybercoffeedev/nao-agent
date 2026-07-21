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
    asr_function_id: str = ""
    openai_base_url: str = ""
    model: str = ""
    remote_wav_path: str = "/home/nao/capture.wav"
    local_wav_path: str = "./capture.wav"
    ssh_port: int = 22

    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        if not self.robot_ip:
            raise ValueError("robot_ip cannot be empty")
        if not self.nvidia_api_key:
            raise ValueError("nvidia_api_key cannot be empty")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Raises:
            ValueError: If required environment variables are missing.
        """
        required_vars = ("ROBOT_IP", "NVIDIA_API_KEY", "ASR_FUNCTION_ID",
                         "OPENAI_BASE_URL", "MODEL")
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            robot_ip=os.environ["ROBOT_IP"],
            robot_port=int(os.getenv("ROBOT_PORT", "9559")),
            robot_username=os.getenv("ROBOT_USERNAME", ""),
            robot_password=os.getenv("ROBOT_PASSWORD", ""),
            nvidia_api_key=os.environ["NVIDIA_API_KEY"],
            asr_function_id=os.environ["ASR_FUNCTION_ID"],
            openai_base_url=os.environ["OPENAI_BASE_URL"],
            model=os.environ["MODEL"],
            ssh_port=int(os.getenv("SSH_PORT", "22")),
        )
