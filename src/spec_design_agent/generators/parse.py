# ABOUTME: Decodes a strict JSON spec body or needs-decision response from a provider.

from __future__ import annotations

import json
import re

from ..types import HumanDecision
from .base import SpecGenerationOutput, TokenUsage

_FENCED_JSON = re.compile(r"```json\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_LEAD_FENCE = re.compile(r"^```(?:markdown|md)?\s*\n?", re.IGNORECASE)
_TRAIL_FENCE = re.compile(r"\n?```\s*$", re.IGNORECASE)
_FRONTMATTER = re.compile(r"^﻿?---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def _coerce_decisions(value: object) -> list[HumanDecision]:
    if not isinstance(value, list):
        return []
    out: list[HumanDecision] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        q, impact, authority = item.get("question"), item.get("impact"), item.get("minimumAuthority")
        if isinstance(q, str) and isinstance(impact, str) and isinstance(authority, str):
            options = item.get("options")
            out.append(
                HumanDecision(
                    question=q,
                    impact=impact,
                    minimum_authority=authority,
                    options=[o for o in options if isinstance(o, str)] if isinstance(options, list) else None,
                )
            )
    return out


def decode_generator_output(
    raw: str, model_provider: str, model: str, usage: TokenUsage | None = None
) -> SpecGenerationOutput:
    text = raw.strip()

    fenced = _FENCED_JSON.search(text)
    candidate = fenced.group(1).strip() if fenced else (text if text.startswith("{") else None)
    if candidate is None:
        raise ValueError("Provider response must be a JSON object")
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Provider response is not valid JSON") from exc
    if not isinstance(obj, dict):
        raise ValueError("Provider response must be a JSON object")
    decisions = _coerce_decisions(obj.get("needsDecision"))
    if decisions:
        return SpecGenerationOutput(spec_body="", model_provider=model_provider, model=model, human_decisions=decisions, usage=usage)
    body = obj.get("specMarkdown")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("Provider response must contain a non-empty specMarkdown string")
    return SpecGenerationOutput(spec_body=body.strip(), model_provider=model_provider, model=model, usage=usage)
