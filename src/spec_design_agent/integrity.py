# ABOUTME: SHA-256 helpers and frozen-intent integrity verification.
# ABOUTME: A hash or identity mismatch means STOP with `blocked`, never "proceed cautiously".

from __future__ import annotations

import hashlib
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
    if intent.version != request.freeze_activation.intent_version:
        raise PreconditionError("blocked", "INTENT_VERSION_MISMATCH", "Frozen intent version does not match the Prioritized freeze record")
    if intent.trello_card_id != request.freeze_activation.trello_card_id:
        raise PreconditionError("blocked", "CARD_ID_MISMATCH", "Frozen intent card ID does not match the Prioritized freeze record")
    if intent.open_decisions:
        raise PreconditionError(
            "needs_decision",
            "INTENT_OPEN_DECISIONS",
            f"Frozen intent still carries {len(intent.open_decisions)} unresolved open decision(s)",
        )
