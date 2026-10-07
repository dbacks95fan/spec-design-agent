# ABOUTME: SHA-256 helpers and frozen-intent integrity verification.
# ABOUTME: A hash or identity mismatch means STOP with `blocked`, never "proceed cautiously".

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .types import ParsedIntent, PreconditionError, SpecRequest


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def verify_frozen_intent(request: SpecRequest, intent: ParsedIntent, workspace_intent_hash: str) -> None:
    """Verify the workspace intent bytes and identity against the request's pinned values."""
    if workspace_intent_hash != request.intent.frozen_artifact_sha256:
        raise PreconditionError(
            "blocked",
            "INTENT_MUTATED",
            "Frozen intent raw-byte hash mismatch: "
            f"request={request.intent.frozen_artifact_sha256}, workspace={workspace_intent_hash}",
        )
    if intent.intent_id != request.work_item:
        raise PreconditionError(
            "blocked",
            "INTENT_IDENTITY_MISMATCH",
            f"Frozen intent id '{intent.intent_id}' does not match requested work item '{request.work_item}'",
        )
    if intent.product_id and intent.product_id != request.product_id:
        raise PreconditionError(
            "blocked",
            "PRODUCT_MISMATCH",
            f"Frozen intent product '{intent.product_id}' does not match requested product '{request.product_id}'",
        )
    # The intent's lifecycle status is deliberately not gated on. The freeze
    # protocol remains documented in agentic-sdlc/docs/WORKFLOW.md, but a run is
    # admitted on identity and byte integrity alone — the checks above, which are
    # about "are these the exact bytes for the right intent", not "has the
    # organisation committed to it yet".
    if intent.open_decisions:
        raise PreconditionError(
            "needs_decision",
            "INTENT_OPEN_DECISIONS",
            f"Frozen intent still carries {len(intent.open_decisions)} unresolved open decision(s)",
        )


def verify_frozen_policy_profile(request: SpecRequest, profile_path: str | Path, workspace_profile_hash: str) -> str:
    """Verify the staged profile's raw bytes and declared identity against the request."""
    if workspace_profile_hash != request.policy_profile.frozen_artifact_sha256:
        raise PreconditionError("blocked", "POLICY_PROFILE_MUTATED", "Frozen policy-profile raw-byte hash does not match the Conductor request")
    text = Path(profile_path).read_text(encoding="utf-8")
    profile_id = re.search(r"^Profile ID:\s*(.+?)\s*$", text, re.MULTILINE)
    version = re.search(r"^Version:\s*(.+?)\s*$", text, re.MULTILINE)
    if not profile_id or profile_id.group(1) != request.policy_profile.profile_id:
        raise PreconditionError("blocked", "POLICY_PROFILE_IDENTITY_MISMATCH", "Frozen policy-profile ID does not match the Conductor request")
    if not version or version.group(1) != request.policy_profile.version:
        raise PreconditionError("blocked", "POLICY_PROFILE_VERSION_MISMATCH", "Frozen policy-profile version does not match the Conductor request")
    return text
