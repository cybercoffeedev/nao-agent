"""System prompt builder tests."""

from agent.llm import build_system_prompt


def test_build_system_prompt_includes_core_rules_and_actions() -> None:
    prompt = build_system_prompt(
        actions={"sit_down": "Make the robot sit down."},
        user_prompt="Custom operator instructions.",
    )

    assert "Always respond as a JSON array of steps" in prompt
    assert "- sit_down - Make the robot sit down." in prompt
    assert "Custom operator instructions." in prompt


def test_build_system_prompt_omits_empty_sections() -> None:
    prompt = build_system_prompt(actions={}, user_prompt="   ")

    assert "Available actions:" not in prompt
    assert prompt.startswith("You are a voice assistant for a NAO robot.")
