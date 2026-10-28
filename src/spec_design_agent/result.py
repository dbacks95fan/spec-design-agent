# ABOUTME: Builds and validates the bounded structured result returned to the Conductor,
# ABOUTME: enforcing the status <-> content invariants from docs/OPERATING_CONTRACT.md.

from __future__ import annotations

from .logging_ import redact
from .schema import validate
from .types import HumanDecision, SpecRequest, SpecResult, SpecStatus


class ResultInvariantError(Exception):
    pass


def build_result(
    *,
    request: SpecRequest,
    status: SpecStatus,
    summary: str,
    frozen_artifact_sha256: str,
    spec_commit: str | None = None,
    spec_path: str | None = None,
    spec_sha256: str | None = None,
    spec_version: int | None = None,
    work_contract_path: str | None = None,
    work_contract_sha256: str | None = None,
    blocking_concerns: list[str] | None = None,
    non_blocking_concerns: list[str] | None = None,
    human_decisions: list[HumanDecision] | None = None,
    usage: dict[str, object] | None = None,
) -> SpecResult:
    result = SpecResult(
        run_id=request.run_id,
        invocation_id=request.invocation_id,
        trigger_event_id=request.trigger_event_id,
        stage=request.stage,
        work_item=request.work_item,
        product_id=request.product_id,
        intent_version=request.freeze_activation.intent_version,
        trello_card_id=request.freeze_activation.trello_card_id,
        status=status,
        summary=redact(summary),
        branch=request.target.branch,
        workspace=request.target.workspace,
        intent_commit=request.intent.commit,
        frozen_artifact_sha256=frozen_artifact_sha256,
        policy_profile_id=request.policy_profile.profile_id,
        policy_profile_version=request.policy_profile.version,
        policy_profile_sha256=request.policy_profile.frozen_artifact_sha256,
        intent_content_sha256=request.intent.content_sha256,
        blocking_concerns=[redact(c) for c in (blocking_concerns or [])],
        non_blocking_concerns=[redact(c) for c in (non_blocking_concerns or [])],
        human_decisions=list(human_decisions or []),
        spec_commit=spec_commit,
        spec_path=spec_path,
        spec_sha256=spec_sha256,
        spec_version=spec_version,
        work_contract_path=work_contract_path,
        work_contract_sha256=work_contract_sha256,
        usage=usage,
    )

    if result.status == "spec_ready":
        if not result.spec_commit or not result.spec_path or not result.spec_sha256 or result.spec_version is None or not result.work_contract_path or not result.work_contract_sha256:
            raise ResultInvariantError("spec_ready requires immutable spec and Work Contract references")
        if result.blocking_concerns or result.human_decisions:
            raise ResultInvariantError("spec_ready must not carry blocking concerns or unresolved human decisions")
    if result.status == "needs_decision" and not result.human_decisions:
        raise ResultInvariantError("needs_decision requires at least one specific human decision")

    errors = validate("spec-result.schema.json", result.to_json())
    if errors:
        raise ResultInvariantError("Result failed schema validation: " + "; ".join(errors))
    return result
