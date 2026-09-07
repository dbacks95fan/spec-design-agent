# ABOUTME: Assembles spec.md with agent-authoritative frontmatter and validates that every
# ABOUTME: required section is present and grounded (no unresolved TODO/decision markers).

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .prompt import SPEC_SECTIONS


@dataclass(frozen=True)
class SpecFrontmatter:
    work_item: str
    product_id: str
    intent_commit: str
    frozen_artifact_sha256: str
    intent_content_sha256: str
    base_commit: str
    spec_version: int
    status: str = "draft"


def assemble_spec(body: str, fm: SpecFrontmatter) -> str:
    yaml_block = "\n".join(
        [
            "---",
            f"work_item: {fm.work_item}",
            f"product_id: {fm.product_id}",
            f"intent_commit: {fm.intent_commit}",
            f"frozen_artifact_sha256: {fm.frozen_artifact_sha256}",
            f"intent_content_sha256: {fm.intent_content_sha256}",
            f"base_commit: {fm.base_commit}",
            f"spec_version: {fm.spec_version}",
            f"status: {fm.status}",
            "---",
            "",
        ]
    )
    return f"{yaml_block}{body.strip()}\n"


@dataclass
class SpecValidation:
    missing_sections: list[str] = field(default_factory=list)
    unresolved_markers: list[str] = field(default_factory=list)
    not_relevant_without_rationale: list[str] = field(default_factory=list)
    criteria_without_observability: bool = False

    @property
    def ok(self) -> bool:
        return (
            not self.missing_sections
            and not self.unresolved_markers
            and not self.not_relevant_without_rationale
            and not self.criteria_without_observability
        )


_FRONTMATTER = re.compile(r"^﻿?---\r?\n.*?\r?\n---\r?\n", re.DOTALL)
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_MARKER = re.compile(r"\b(TODO|TBD|FIXME|DECISION REQUIRED|\?\?\?|<placeholder>)\b", re.IGNORECASE)
_NOT_RELEVANT = re.compile(r"\bnot (relevant|applicable)\b|\bn/a\b", re.IGNORECASE)
_RATIONALE = re.compile(r"\bbecause\b|\brationale\b", re.IGNORECASE)
_OBSERVABLE = re.compile(r"\b(AC-?\d|acceptance cri|observable)\b", re.IGNORECASE)


def _section_map(markdown: str) -> dict[str, str]:
    body = _FRONTMATTER.sub("", markdown, count=1)
    out: dict[str, str] = {}
    matches = list(_HEADING.finditer(body))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[m.group(1).strip().lower()] = body[start:end].strip()
    return out


def validate_spec(markdown: str) -> SpecValidation:
    """Structural + grounding checks. Semantic intent-fidelity review remains a human gate."""
    sections = _section_map(markdown)
    result = SpecValidation()

    for required in SPEC_SECTIONS:
        body = sections.get(required.lower())
        if not body:
            result.missing_sections.append(required)
            continue
        if _NOT_RELEVANT.search(body) and not _RATIONALE.search(body):
            result.not_relevant_without_rationale.append(required)
        if _MARKER.search(body):
            result.unresolved_markers.append(required)

    fr = sections.get("functional requirements and acceptance criteria", "")
    result.criteria_without_observability = bool(fr) and not _OBSERVABLE.search(fr)
    return result
