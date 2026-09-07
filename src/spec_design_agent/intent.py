# ABOUTME: Parses a canonical frozen intent.md (intent-creation-skill output-format.md):
# ABOUTME: YAML frontmatter plus H2 sections including Open decisions and Acceptance criteria.

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .integrity import sha256_text
from .types import ParsedIntent

_FRONTMATTER = re.compile(r"^﻿?---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.DOTALL)
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_TITLE = re.compile(r"^#\s*Intent:\s*(.+)$", re.MULTILINE)
_BULLET = re.compile(r"^\s*[-*]\s+(.+?)\s*$", re.MULTILINE)
_PLACEHOLDER = re.compile(r"^_?none_?$", re.IGNORECASE)


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    match = _FRONTMATTER.match(raw)
    if not match:
        return {}, raw
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        data = {}
    return data, match.group(2)


def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(_HEADING.finditer(body))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[m.group(1).strip().lower()] = body[start:end].strip()
    return sections


def _bullets(section: str | None) -> list[str]:
    if not section:
        return []
    out = []
    for m in _BULLET.finditer(section):
        line = m.group(1).strip()
        if line and line != "-" and not _PLACEHOLDER.match(line):
            out.append(line)
    return out


def parse_intent(raw: str) -> ParsedIntent:
    data, body = _split_frontmatter(raw)
    sections = _split_sections(body)

    intent_id = str(data.get("intent_id", "")).strip()
    if not intent_id:
        raise ValueError("Frozen intent is missing 'intent_id' in its frontmatter")
    if not data.get("status"):
        raise ValueError("Frozen intent is missing 'status' in its frontmatter")

    title_match = _TITLE.search(body)
    if title_match:
        sections = {**sections, "title": title_match.group(1).strip()}

    raw_version = data.get("intent_version")
    return ParsedIntent(
        intent_id=intent_id,
        product_id=(str(data["product_id"]).strip() if data.get("product_id") else None),
        version=(raw_version if isinstance(raw_version, int) else None),
        status=str(data["status"]).strip(),
        open_decisions=_bullets(sections.get("open decisions")),
        acceptance_criteria=_bullets(sections.get("acceptance criteria")),
        sha256=sha256_text(raw),
        sections=sections,
        raw=raw,
    )


def read_intent_file(path: str | Path) -> ParsedIntent:
    return parse_intent(Path(path).read_text(encoding="utf-8"))
