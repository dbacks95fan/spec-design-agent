# ABOUTME: Loads the JSON Schemas shipped in schemas/ and validates values against them,
# ABOUTME: returning readable error strings instead of raising.

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft7Validator

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft7Validator:
    schema = json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def validate(schema_name: str, value: object) -> list[str]:
    """Return a list of human-readable errors; empty means valid."""
    errors: list[str] = []
    for err in sorted(_validator(schema_name).iter_errors(value), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{location} {err.message}")
    return errors
