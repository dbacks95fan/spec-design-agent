# ABOUTME: The provider-neutral spec generator seam. Implementations (claude, codex, mock)
# ABOUTME: turn a prompt over an immutable intent + read-only repo into spec.md Markdown.

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Protocol

from ..repo_inspect import RepoFacts
from ..types import HumanDecision, ParsedIntent


@dataclass(frozen=True)
class SpecGenerationInput:
    work_item: str
    product_id: str
    intent: ParsedIntent
    repo_facts: RepoFacts
    repo_root: str
    # Cooperative cancellation for timeouts.
    cancel: threading.Event | None = None


@dataclass(frozen=True)
class TokenUsage:
    """What one generation cost. Reported so a run can be costed after the fact;
    providers that cannot measure it (mock) simply omit it."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    turns: int = 0
    cost_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_tokens + self.cache_creation_tokens

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "cacheReadTokens": self.cache_read_tokens,
            "cacheCreationTokens": self.cache_creation_tokens,
            "totalTokens": self.total_tokens,
            "turns": self.turns,
        }
        if self.cost_usd is not None:
            out["costUsd"] = self.cost_usd
        return out


@dataclass
class SpecGenerationOutput:
    # spec.md body Markdown WITHOUT YAML frontmatter (the agent prepends authoritative frontmatter).
    spec_body: str
    model_provider: str
    model: str
    # Material decisions the generator refused to make. Non-empty => needs_decision.
    human_decisions: list[HumanDecision] = field(default_factory=list)
    # Advisory concerns for the human reviewer that do not block routing.
    non_blocking_concerns: list[str] = field(default_factory=list)
    # None when the provider does not report usage.
    usage: TokenUsage | None = None


class SpecGenerator(Protocol):
    name: str

    def generate(self, data: SpecGenerationInput) -> SpecGenerationOutput: ...
