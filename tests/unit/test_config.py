"""Configuration tests."""

import pytest

from config import Config

ENV_KEYS = (
    "ROBOT_IP",
    "ROBOT_PORT",
    "ROBOT_USERNAME",
    "ROBOT_PASSWORD",
    "WHISPER_URL",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "MODEL",
    "SSH_PORT",
    "LOCAL_WAV_PATH",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_from_env_requires_robot_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)

    with pytest.raises(ValueError, match="ROBOT_IP"):
        Config.from_env()


def test_from_env_uses_documented_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("ROBOT_IP", "192.0.2.10")

    config = Config.from_env()

    assert config.robot_ip == "192.0.2.10"
    assert config.robot_port == 9559
    assert config.robot_username == "nao"
    assert config.robot_password == "nao"
    assert config.whisper_url == "http://whisper-server:8081"
    assert config.openai_base_url == "http://llama-server:8080/v1"
    assert config.openai_api_key == "dummy"
    assert config.model == "model"
    assert config.local_wav_path == "./capture.wav"
    assert config.ssh_port == 22


def test_from_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("ROBOT_IP", "10.0.0.5")
    monkeypatch.setenv("ROBOT_PORT", "9669")
    monkeypatch.setenv("WHISPER_URL", "http://asr:9000")
    monkeypatch.setenv("MODEL", "qwen-test")
    monkeypatch.setenv("SSH_PORT", "2222")

    config = Config.from_env()

    assert config.robot_port == 9669
    assert config.whisper_url == "http://asr:9000"
    assert config.model == "qwen-test"
    assert config.ssh_port == 2222
