# ABOUTME: Selects a spec generator by configuration. Provider is transport-neutral and
# ABOUTME: injected via SPEC_AGENT_PROVIDER (or an explicit override) — never hardcoded.

from __future__ import annotations

import os

from .base import SpecGenerationInput, SpecGenerationOutput, SpecGenerator
from .claude import ClaudeGenerator
from .codex import CodexGenerator
from .mock import MockGenerator

DEFAULT_PROVIDER = "claude"


def create_generator(*, provider: str | None = None, model: str | None = None) -> SpecGenerator:
    name = (provider or os.environ.get("SPEC_AGENT_PROVIDER") or DEFAULT_PROVIDER).lower()
    if name == "claude":
        return ClaudeGenerator(model=model)
    if name == "codex":
        return CodexGenerator(model=model)
    if name == "mock":
        return MockGenerator()
    raise ValueError(f"Unknown SPEC_AGENT_PROVIDER '{name}'. Supported: claude, codex, mock.")


__all__ = [
    "SpecGenerationInput",
    "SpecGenerationOutput",
    "SpecGenerator",
    "ClaudeGenerator",
    "CodexGenerator",
    "MockGenerator",
    "create_generator",
    "DEFAULT_PROVIDER",
]
