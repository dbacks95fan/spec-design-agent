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
    spec_version: int | None = None,
    blocking_concerns: list[str] | None = None,
    non_blocking_concerns: list[str] | None = None,
    human_decisions: list[HumanDecision] | None = None,
) -> SpecResult:
    result = SpecResult(
        run_id=request.run_id,
        work_item=request.work_item,
        status=status,
        summary=redact(summary),
        branch=request.target.branch,
        workspace=request.target.workspace,
        intent_commit=request.intent.commit,
        frozen_artifact_sha256=frozen_artifact_sha256,
        intent_content_sha256=request.intent.content_sha256,
        blocking_concerns=[redact(c) for c in (blocking_concerns or [])],
        non_blocking_concerns=[redact(c) for c in (non_blocking_concerns or [])],
        human_decisions=list(human_decisions or []),
        spec_commit=spec_commit,
        spec_path=spec_path,
        spec_version=spec_version,
    )

    if result.status == "spec_ready":
        if not result.spec_commit or not result.spec_path or result.spec_version is None:
            raise ResultInvariantError("spec_ready requires specCommit, specPath, and specVersion")
        if result.blocking_concerns or result.human_decisions:
            raise ResultInvariantError("spec_ready must not carry blocking concerns or unresolved human decisions")
    if result.status == "needs_decision" and not result.human_decisions:
        raise ResultInvariantError("needs_decision requires at least one specific human decision")

    errors = validate("spec-result.schema.json", result.to_json())
    if errors:
        raise ResultInvariantError("Result failed schema validation: " + "; ".join(errors))
    return result
