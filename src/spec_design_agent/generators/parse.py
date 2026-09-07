# ABOUTME: Shared decoding of model output into a SpecGenerationOutput: either a spec body,
# ABOUTME: or a fenced json {"needsDecision":[...]} block signalling a material decision.

from __future__ import annotations

import json
import re

from ..types import HumanDecision
from .base import SpecGenerationOutput

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


def decode_generator_output(raw: str, model_provider: str, model: str) -> SpecGenerationOutput:
    text = raw.strip()

    fenced = _FENCED_JSON.search(text)
    candidate = fenced.group(1).strip() if fenced else (text if text.startswith("{") else None)
    if candidate is not None:
        try:
            obj = json.loads(candidate)
            decisions = _coerce_decisions(obj.get("needsDecision")) if isinstance(obj, dict) else []
            if decisions:
                return SpecGenerationOutput(
                    spec_body="", model_provider=model_provider, model=model, human_decisions=decisions
                )
        except json.JSONDecodeError:
            pass  # not a decision block — treat as spec body

    body = _LEAD_FENCE.sub("", text)
    body = _TRAIL_FENCE.sub("", body)
    body = _FRONTMATTER.sub("", body, count=1)
    return SpecGenerationOutput(spec_body=body.strip(), model_provider=model_provider, model=model)
