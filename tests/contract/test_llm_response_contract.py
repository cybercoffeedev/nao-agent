"""Contract tests for the documented LLM response schema and example."""

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs" / "contracts" / "llm-response.schema.json"
EXAMPLE_PATH = ROOT / "docs" / "contracts" / "llm-response.example.json"


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_example_matches_schema() -> None:
    jsonschema.validate(_load(EXAMPLE_PATH), _load(SCHEMA_PATH))


def test_contract_rejects_an_empty_plan() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate([], _load(SCHEMA_PATH))


def test_contract_rejects_args_without_action() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate([{"args": {"query": "weather"}}], _load(SCHEMA_PATH))
