# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Builds the proposed Work Contract v3 from frozen inputs and repository checks.

from __future__ import annotations

import re
from typing import Any

import yaml

from .policy_profile import ParsedPolicyProfile
from .repo_inspect import RepoFacts
from .schema import validate
from .types import ParsedIntent, PreconditionError, SpecRequest


def _scope_items(text: str, label: str) -> list[str]:
    suffix = "s?" if label == "non-goal" else ""
    next_label = r"non-goals?\s*:" if label == "in scope" else r"$"
    match = re.search(rf"{re.escape(label)}{suffix}\s*:\s*(.*?)(?={next_label})", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    value = match.group(1).strip()
    return [part.strip(" -*\t") for part in re.split(r"\n|;", value) if part.strip(" -*\t")]


def _requirements(intent: ParsedIntent, heading: str) -> list[str]:
    return [line.strip().lstrip("-* ") for line in intent.sections.get(heading, "").splitlines() if line.strip().lstrip("-* ")]


def build_work_contract(
    request: SpecRequest,
    intent: ParsedIntent,
    policy_profile: ParsedPolicyProfile,
    repo_facts: RepoFacts,
) -> dict[str, Any]:
    if not intent.acceptance_criteria:
        raise PreconditionError(
            "needs_decision",
            "ACCEPTANCE_CRITERIA_MISSING",
            "The frozen intent has no acceptance criteria from which to define the execution contract.",
        )
    if intent.version != request.freeze_activation.intent_version:
        raise PreconditionError("blocked", "INTENT_VERSION_MISMATCH", "Frozen intent version does not match the Prioritized freeze record")
    if intent.trello_card_id != request.freeze_activation.trello_card_id:
        raise PreconditionError("blocked", "CARD_ID_MISMATCH", "Frozen intent card ID does not match the Prioritized freeze record")

    scope = intent.sections.get("scope and non-goals", "")
    included = _scope_items(scope, "in scope") or list(intent.acceptance_criteria)
    excluded = _scope_items(scope, "non-goal")
    contract = {
        "schema_version": 3,
        "work_item": {
            "product_id": request.product_id,
            "intent_id": request.work_item,
            "intent_version": request.freeze_activation.intent_version,
            "trello_card_id": request.freeze_activation.trello_card_id,
        },
        "intent": {
            "repository": request.intent.repository,
            "commit_sha": request.intent.commit,
            "path": request.intent.path,
            "sha256": request.intent.frozen_artifact_sha256,
        },
        "policy_profile_id": policy_profile.profile_id,
        "policy_profile_version": policy_profile.version,
        "policy_profile": {
            "repository": request.policy_profile.repository,
            "commit_sha": request.policy_profile.commit,
            "path": request.policy_profile.path,
            "sha256": request.policy_profile.frozen_artifact_sha256,
        },
        "target": {"repository": request.target.repository, "commit_sha": request.target.base_commit},
        "acceptance_criteria": list(intent.acceptance_criteria),
        "permitted_scope": {"included": included, "excluded": excluded},
        "required_validation": list(repo_facts.validation_commands),
        "policy_controls": [control.to_json() for control in policy_profile.controls],
        "release_requirements": _requirements(intent, "release requirements"),
        "observation_requirements": _requirements(intent, "observation requirements"),
    }
    errors = validate("work-contract.schema.json", contract)
    if errors:
        raise ValueError("Proposed Work Contract failed canonical schema validation: " + "; ".join(errors))
    return contract


def render_work_contract(contract: dict[str, Any]) -> str:
    return yaml.safe_dump(contract, sort_keys=False, allow_unicode=True)
