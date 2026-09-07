# ABOUTME: Runtime configuration resolved from environment variables. Transport-neutral:
# ABOUTME: nothing here is hardcoded to a provider or deployment platform.

from __future__ import annotations

import os
from dataclasses import dataclass

from . import __version__
from .repo_inspect import DEFAULT_LIMITS, InspectionLimits

AGENT_VERSION = __version__
DEFAULT_PROVIDER = "claude"


@dataclass(frozen=True)
class AgentConfig:
    provider: str
    model: str | None
    generation_timeout_ms: int
    inspection: InspectionLimits


def _int_from_env(name: str, fallback: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return fallback
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"Environment variable {name} must be a positive number; got {raw!r}")
    if value <= 0:
        raise ValueError(f"Environment variable {name} must be a positive number; got {raw!r}")
    return value


def load_config(
    *,
    provider: str | None = None,
    model: str | None = None,
    generation_timeout_ms: int | None = None,
    inspection: InspectionLimits | None = None,
) -> AgentConfig:
    return AgentConfig(
        provider=provider or os.environ.get("SPEC_AGENT_PROVIDER") or DEFAULT_PROVIDER,
        model=model or os.environ.get("SPEC_AGENT_MODEL") or None,
        generation_timeout_ms=(
            generation_timeout_ms
            if generation_timeout_ms is not None
            else _int_from_env("SPEC_AGENT_TIMEOUT_MS", 10 * 60_000)
        ),
        inspection=inspection
        or InspectionLimits(
            max_files=_int_from_env("SPEC_AGENT_MAX_FILES", DEFAULT_LIMITS.max_files),
            max_bytes_per_file=_int_from_env("SPEC_AGENT_MAX_BYTES_PER_FILE", DEFAULT_LIMITS.max_bytes_per_file),
            max_depth=_int_from_env("SPEC_AGENT_MAX_DEPTH", DEFAULT_LIMITS.max_depth),
            deadline_ms=_int_from_env("SPEC_AGENT_INSPECT_DEADLINE_MS", DEFAULT_LIMITS.deadline_ms),
        ),
    )
