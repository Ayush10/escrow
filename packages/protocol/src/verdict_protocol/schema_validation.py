from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


_VALIDATORS: dict[str, Draft202012Validator] = {}


def _load_validator(name: str) -> Draft202012Validator:
    if name not in _VALIDATORS:
        schema_path = SCHEMA_DIR / name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        _VALIDATORS[name] = Draft202012Validator(schema)
    return _VALIDATORS[name]


def validate_schema(name: str, payload: dict[str, Any]) -> list[str]:
    validator = _load_validator(name)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    return [f"{'/'.join(map(str, err.path))}: {err.message}" for err in errors]
