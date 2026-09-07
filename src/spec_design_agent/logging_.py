# ABOUTME: Structured JSON logging with secret redaction. Lines go to stderr so stdout stays
# ABOUTME: reserved for the single JSON result. Every line carries timestamp, level, event.

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any

_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-ant-[A-Za-z0-9_-]+"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9_-]+"), "[REDACTED_API_KEY]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]+"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"Bearer\s+[^\s\"']+", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"(https?://)[^/\s:@]+:[^/\s@]+@"), r"\1[REDACTED]@"),
]


def redact(value: str) -> str:
    """Strip recognizable credentials before text reaches a log or a result."""
    for pattern, replacement in _REDACTIONS:
        value = pattern.sub(replacement, value)
    return value


def error_message(error: BaseException) -> str:
    return redact(str(error))


def log(level: str, event: str, message: str, **details: Any) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        "message": redact(message),
        **details,
    }
    print(json.dumps(record), file=sys.stderr, flush=True)
