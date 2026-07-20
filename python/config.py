import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""
    robot_ip: str
    robot_port: int = 9559
    robot_username: str = "nao"
    robot_password: str = "nao"
    nvidia_api_key: str = ""
    asr_function_id: str = ""
    openai_base_url: str = ""
    model: str = ""
    remote_wav_path: str = "/home/nao/capture.wav"
    local_wav_path: str = "./capture.wav"

    @classmethod
    def from_env(cls) -> "Config":
        """Loads configuration from environment variables.

        Raises:
            ValueError: If required environment variables are missing.
        """
        missing = [var for var in ("ROBOT_IP", "NVIDIA_API_KEY", "ASR_FUNCTION_ID",
                                   "OPENAI_BASE_URL", "MODEL")
                   if not os.environ.get(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            robot_ip=os.environ["ROBOT_IP"],
            robot_port=int(os.getenv("ROBOT_PORT", "9559")),
            robot_username=os.getenv("ROBOT_USERNAME", "nao"),
            robot_password=os.getenv("ROBOT_PASSWORD", "nao"),
            nvidia_api_key=os.environ["NVIDIA_API_KEY"],
            asr_function_id=os.environ["ASR_FUNCTION_ID"],
            openai_base_url=os.environ["OPENAI_BASE_URL"],
            model=os.environ["MODEL"],
        )
