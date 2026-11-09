"""Response parser tests documenting the pre-M1 behaviour."""

import json

from agent.response_parser import clean_for_tts, parse_steps


def test_parse_steps_accepts_a_valid_json_array() -> None:
    steps = [{"speak": "Hello"}, {"action": "stand_up"}]

    assert parse_steps(json.dumps(steps)) == steps


def test_parse_steps_recovers_an_array_from_surrounding_text() -> None:
    raw = 'Here is the plan: [{"speak": "Hello"}] Done.'

    assert parse_steps(raw) == [{"speak": "Hello"}]


def test_parse_steps_returns_none_for_invalid_output() -> None:
    assert parse_steps("I cannot produce JSON right now.") is None


def test_clean_for_tts_extracts_speak_values() -> None:
    raw = '[{"speak": "Hello"}, {"action": "stand_up"}]'

    assert clean_for_tts(raw) == "Hello"
