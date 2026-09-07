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


class SpecGenerator(Protocol):
    name: str

    def generate(self, data: SpecGenerationInput) -> SpecGenerationOutput: ...
