# ABOUTME: Builds and schema-validates the sanitized spec-run.json provenance record.

from __future__ import annotations

from .config import AGENT_VERSION
from .prompt import PROMPT_VERSION
from .schema import validate
from .types import SpecRequest, SpecRunRecord, SpecStatus


def build_run_record(
    *,
    request: SpecRequest,
    base_commit: str,
    frozen_artifact_sha256: str,
    model_provider: str,
    model: str,
    started_at: str,
    completed_at: str,
    status: SpecStatus,
    spec_version: int | None = None,
    policy_versions: list[str] | None = None,
    usage: dict[str, object] | None = None,
) -> SpecRunRecord:
    record = SpecRunRecord(
        run_id=request.run_id,
        work_item=request.work_item,
        product_id=request.product_id,
        intent_commit=request.intent.commit,
        frozen_artifact_sha256=frozen_artifact_sha256,
        intent_content_sha256=request.intent.content_sha256,
        base_commit=base_commit,
        branch=request.target.branch,
        model_provider=model_provider,
        model=model,
        agent_version=AGENT_VERSION,
        prompt_version=PROMPT_VERSION,
        started_at=started_at,
        completed_at=completed_at,
        status=status,
        policy_versions=policy_versions or [],
        spec_version=spec_version,
        usage=usage,
    )
    errors = validate("spec-run.schema.json", record.to_json())
    if errors:
        raise ValueError("Run record failed schema validation: " + "; ".join(errors))
    return record
