# ABOUTME: Builds the specification-generation prompt from the frozen intent and confirmed
# ABOUTME: repository facts. PROMPT_VERSION is recorded in every run record for provenance.

from __future__ import annotations

from dataclasses import dataclass

from .repo_inspect import RepoFacts
from .types import ParsedIntent

# Bump on any change to prompt text or the section contract. Recorded in spec-run.json.
PROMPT_VERSION = "spec-prompt-1"

# Required H2 sections of spec.md, from docs/ARTIFACTS.md. Order is significant.
SPEC_SECTIONS: tuple[str, ...] = (
    "Intent fidelity",
    "Confirmed repository context",
    "User and system-observable outcomes",
    "Functional requirements and acceptance criteria",
    "Non-functional requirements",
    "Design and affected boundaries",
    "Data, security, privacy, and compliance considerations",
    "Error handling and operational behavior",
    "Validation strategy",
    "Dependencies, assumptions, and non-goals",
    "Risks and unresolved decisions",
    "Traceability to frozen intent",
)

SYSTEM_RULES = """You are the Spec & Design Agent in an intent-driven Agentic SDLC.
Your only job is to turn ONE frozen product intent into a reviewable requirements and design specification for a human Design Review.

Hard boundaries:
- The frozen intent is immutable. Never restate it as changed, expanded, or narrowed.
- Do not write product code, implementation plans, or test code. Describe outcomes and boundaries, not code.
- Do not claim any approval. Your output is "ready for review", never "approved".
- Preserve the distinction between confirmed repository facts, design decisions, and assumptions.
- A choice that materially affects behavior, architecture, security, compliance, data semantics, destructive actions, external contracts, cost, or scope is NOT yours to make. Surface it as a decision request.
- Never include secrets, credentials, or private chain-of-thought in the specification."""


@dataclass(frozen=True)
class SpecPromptInput:
    work_item: str
    product_id: str
    intent: ParsedIntent
    repo_facts: RepoFacts


def _summarize_repo_facts(facts: RepoFacts) -> str:
    langs = ", ".join(
        f"{ext or '(none)'}={n}"
        for ext, n in sorted(facts.language_histogram.items(), key=lambda kv: kv[1], reverse=True)[:12]
    )
    if facts.instruction_files:
        instructions = "\n\n".join(
            f"--- {f.path}{' (truncated)' if f.truncated else ''} ---\n{f.excerpt}"
            for f in facts.instruction_files
        )
    else:
        instructions = "(no repository-local instruction files found)"
    return "\n".join(
        [
            f"Top-level entries: {', '.join(facts.top_level_entries)}",
            f"File extension histogram: {langs or '(none)'}",
            f"Test signals: {'; '.join(facts.test_signals) or '(none detected)'}",
            (
                f"Inspection bound hit: {facts.limit_hit} (repository not fully enumerated)"
                if facts.limit_hit
                else "Inspection completed within bounds"
            ),
            "",
            "Repository-local instructions:",
            instructions,
        ]
    )


def build_spec_prompt(data: SpecPromptInput) -> tuple[str, str]:
    """Return (system, user). The generator returns spec.md body Markdown, OR a fenced
    ```json {"needsDecision": [...]} block when a material decision blocks specification."""
    section_list = "\n".join(f"{i + 1}. ## {s}" for i, s in enumerate(SPEC_SECTIONS))
    user = "\n".join(
        [
            f"Work item: {data.work_item}",
            f"Product: {data.product_id}",
            "",
            "=== FROZEN INTENT (verbatim, immutable) ===",
            data.intent.raw.strip(),
            "=== END FROZEN INTENT ===",
            "",
            "=== CONFIRMED REPOSITORY FACTS ===",
            _summarize_repo_facts(data.repo_facts),
            "=== END REPOSITORY FACTS ===",
            "",
            "Produce spec.md as Markdown. Do not include YAML frontmatter; it is added by the agent.",
            "Use exactly these H2 sections, in this order:",
            section_list,
            "",
            "A section may be marked 'Not relevant' only with an explicit one-line rationale beginning with 'because'.",
            "Every functional requirement must have at least one observable acceptance criterion.",
            "The 'Traceability to frozen intent' section must map each acceptance criterion in the intent to a requirement here.",
            "",
            "If a material decision prevents you from specifying responsibly, return ONLY a fenced json block:",
            "```json",
            '{"needsDecision":[{"question":"...","impact":"...","options":["..."],"minimumAuthority":"..."}]}',
            "```",
        ]
    )
    return SYSTEM_RULES, user
