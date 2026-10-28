# ABOUTME: Loads the JSON Schemas shipped in schemas/ and validates values against them,
# ABOUTME: returning readable error strings instead of raising.

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema.validators import validator_for
from jsonschema import FormatChecker

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


@lru_cache(maxsize=None)
def _validator(name: str):
    schema = json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))
    validator_type = validator_for(schema)
    validator_type.check_schema(schema)
    return validator_type(schema, format_checker=FormatChecker())


def validate(schema_name: str, value: object) -> list[str]:
    """Return a list of human-readable errors; empty means valid."""
    errors: list[str] = []
    for err in sorted(_validator(schema_name).iter_errors(value), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{location} {err.message}")
    return errors
