# ABOUTME: Deterministic generator used for tests and offline end-to-end runs. It derives a
# ABOUTME: complete spec body from the frozen intent without calling any model.

from __future__ import annotations

from dataclasses import dataclass, field

from ..prompt import SPEC_SECTIONS
from ..types import HumanDecision
from .base import SpecGenerationInput, SpecGenerationOutput


def _section_body(name: str, data: SpecGenerationInput) -> str:
    intent = data.intent
    sec = intent.sections
    match name:
        case "Intent fidelity":
            return (
                f'The frozen intent "{sec.get("title", intent.intent_id)}" is reproduced without change. '
                f'Desired outcome: {sec.get("desired outcome", "(see intent)")}.'
            )
        case "Confirmed repository context":
            return (
                f"Confirmed fact: top-level entries are {', '.join(data.repo_facts.top_level_entries) or '(none)'}. "
                f"Test signals: {'; '.join(data.repo_facts.test_signals) or '(none)'}."
            )
        case "User and system-observable outcomes":
            return sec.get("evidence of success", "A user can observe the intended result end to end.")
        case "Functional requirements and acceptance criteria":
            if intent.acceptance_criteria:
                return "\n".join(
                    f"- FR-{i + 1}: {c}\n  - AC-{i + 1}: observable — {c}"
                    for i, c in enumerate(intent.acceptance_criteria)
                )
            return "- FR-1: deliver the intent outcome.\n  - AC-1: the outcome is observable by the user."
        case "Non-functional requirements":
            return sec.get("constraints", "Assumption: existing performance and reliability budgets apply unchanged.")
        case "Design and affected boundaries":
            return (
                "Design decision: the change is confined to the boundaries named in the intent scope. "
                "No new external contracts are introduced."
            )
        case "Data, security, privacy, and compliance considerations":
            return "No new personal-data categories are introduced. Existing authorization boundaries are preserved."
        case "Error handling and operational behavior":
            return (
                "Failures surface a user-visible error and are logged with correlation context; "
                "no partial state is persisted."
            )
        case "Validation strategy":
            return (
                "Each acceptance criterion is verified by an automated check; test evidence is necessary "
                "but not sufficient proof of outcome delivery."
            )
        case "Dependencies, assumptions, and non-goals":
            return (
                f"Non-goals: {sec.get('scope and non-goals', '(see intent)')}. "
                "Assumptions are listed inline above."
            )
        case "Risks and unresolved decisions":
            return (
                "Risk: repository inspection bounds may have hidden an affected module. "
                "No unresolved blocking decision remains."
            )
        case "Traceability to frozen intent":
            if intent.acceptance_criteria:
                return "\n".join(
                    f'- Intent AC "{c}" -> FR-{i + 1}/AC-{i + 1}'
                    for i, c in enumerate(intent.acceptance_criteria)
                )
            return "- Intent outcome -> FR-1/AC-1"
        case _:
            return "Not relevant because this section does not apply to the frozen intent's scope."


@dataclass
class MockGenerator:
    name: str = "mock"
    force_decisions: list[HumanDecision] = field(default_factory=list)
    omit_sections: set[str] = field(default_factory=set)

    def generate(self, data: SpecGenerationInput) -> SpecGenerationOutput:
        if self.force_decisions:
            return SpecGenerationOutput(
                spec_body="",
                model_provider="mock",
                model="deterministic-1",
                human_decisions=list(self.force_decisions),
            )
        body = "\n\n".join(
            f"## {s}\n\n{_section_body(s, data)}"
            for s in SPEC_SECTIONS
            if s not in self.omit_sections
        )
        return SpecGenerationOutput(
            spec_body=f"# Requirements and Design Specification\n\n{body}\n",
            model_provider="mock",
            model="deterministic-1",
        )
