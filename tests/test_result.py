import pytest
from conftest import valid_request

from spec_design_agent.result import ResultInvariantError, build_result
from spec_design_agent.types import HumanDecision, SpecRequest

REQUEST = SpecRequest.from_dict(valid_request())
BASE = {"request": REQUEST, "frozen_artifact_sha256": "a" * 64}


def test_builds_valid_spec_ready_result():
    result = build_result(
        **BASE,
        status="spec_ready",
        summary="ready",
        spec_commit="b" * 40,
        spec_path=".agent/work/INT-MF-0042/spec.md",
        spec_version=1,
    )
    assert result.status == "spec_ready"
    assert result.spec_version == 1


def test_rejects_spec_ready_without_committed_spec():
    with pytest.raises(ResultInvariantError):
        build_result(**BASE, status="spec_ready", summary="ready")


def test_rejects_spec_ready_with_blocking_concern():
    with pytest.raises(ResultInvariantError):
        build_result(
            **BASE,
            status="spec_ready",
            summary="ready",
            spec_commit="b" * 40,
            spec_path="p",
            spec_version=1,
            blocking_concerns=["leftover"],
        )


def test_rejects_needs_decision_without_decision():
    with pytest.raises(ResultInvariantError):
        build_result(**BASE, status="needs_decision", summary="hold")


def test_redacts_secrets_from_summary_and_concerns():
    result = build_result(
        **BASE,
        status="blocked",
        summary="failed using sk-ant-abcdef123456",
        blocking_concerns=["token ghp_deadbeef00000"],
    )
    assert "[REDACTED_ANTHROPIC_KEY]" in result.summary
    assert "[REDACTED_GITHUB_TOKEN]" in result.blocking_concerns[0]


def test_accepts_well_formed_needs_decision():
    result = build_result(
        **BASE,
        status="needs_decision",
        summary="hold",
        human_decisions=[HumanDecision(question="delimiter?", impact="data contract", minimum_authority="product owner")],
    )
    assert len(result.human_decisions) == 1
