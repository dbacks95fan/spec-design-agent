import pytest
from conftest import valid_request

from spec_design_agent.config import AGENT_VERSION
from spec_design_agent.prompt import PROMPT_VERSION
from spec_design_agent.spec_run import build_run_record
from spec_design_agent.types import SpecRequest

REQUEST = SpecRequest.from_dict(valid_request())
COMMON = dict(
    request=REQUEST,
    base_commit="c" * 40,
    frozen_artifact_sha256="d" * 64,
    model_provider="mock",
    model="deterministic-1",
    started_at="2026-09-06T12:00:00+00:00",
    completed_at="2026-09-06T12:00:30+00:00",
)


def test_builds_schema_valid_run_record_with_provenance():
    record = build_run_record(**COMMON, status="spec_ready", spec_version=1)
    assert record.agent_version == AGENT_VERSION
    assert record.prompt_version == PROMPT_VERSION
    assert record.intent_commit == REQUEST.intent.commit
    assert record.frozen_artifact_sha256 == "d" * 64
    assert record.intent_content_sha256 == REQUEST.intent.content_sha256
    assert record.spec_version == 1


def test_omits_spec_version_for_non_ready_status():
    record = build_run_record(**COMMON, status="blocked")
    assert record.spec_version is None
    assert record.status == "blocked"


def test_rejects_malformed_hash():
    with pytest.raises(ValueError, match="schema validation"):
        build_run_record(**{**COMMON, "frozen_artifact_sha256": "too-short"}, status="failed")
