import json
import subprocess
import threading
from pathlib import Path

from conftest import canonical_intent, sha256, write_exact

from spec_design_agent.config import load_config
from spec_design_agent.generators.base import SpecGenerationOutput
from spec_design_agent.generators.mock import MockGenerator
from spec_design_agent.run import EXIT_CODES, run_spec_design
from spec_design_agent.types import HumanDecision


def _mock_deps():
    return {"generator": MockGenerator(), "config": load_config(provider="mock")}


def _git(cwd: Path, args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True).stdout.strip()


def test_happy_path_commits_spec_and_returns_spec_ready(staged_repo_and_request):
    root, request, _text, _path = staged_repo_and_request
    outcome = run_spec_design(request, **_mock_deps())
    assert outcome.result.status == "spec_ready"
    assert outcome.exit_code == 0
    assert outcome.result.spec_path == ".agent/work/INT-MF-0042/spec.md"
    assert outcome.result.spec_commit and len(outcome.result.spec_commit) == 40
    assert outcome.run_record.status == "spec_ready"

    work_dir = root / ".agent/work/INT-MF-0042"
    spec = (work_dir / "spec.md").read_text(encoding="utf-8")
    assert spec.startswith("---\nwork_item: INT-MF-0042")
    assert "## Traceability to frozen intent" in spec
    json.loads((work_dir / "spec-run.json").read_text(encoding="utf-8"))
    json.loads((work_dir / "spec-result.json").read_text(encoding="utf-8"))

    assert "spec(INT-MF-0042): spec v1 ready for Design Review" in _git(root, ["log", "-1", "--pretty=%s"])


def test_idempotent_replay_returns_same_result(staged_repo_and_request):
    _root, request, _text, _path = staged_repo_and_request
    first = run_spec_design(request, **_mock_deps())
    second = run_spec_design(request, **_mock_deps())
    assert second.result.to_json() == first.result.to_json()
    assert second.run_record is None


def test_missing_approval_yields_blocked_not_exception(staged_repo_and_request):
    _root, request, _text, _path = staged_repo_and_request
    request["approval"]["readyForPlanning"] = False
    outcome = run_spec_design(request, **_mock_deps())
    assert outcome.result.status == "blocked"
    assert outcome.exit_code == EXIT_CODES["blocked"]
    assert "APPROVAL_MISSING" in " ".join(outcome.result.blocking_concerns)


def test_intent_hash_mismatch_blocks(staged_repo_and_request):
    _root, request, _text, _path = staged_repo_and_request
    request["intent"]["frozenArtifactSha256"] = "f" * 64
    outcome = run_spec_design(request, **_mock_deps())
    assert outcome.result.status == "blocked"
    assert "INTENT_MUTATED" in " ".join(outcome.result.blocking_concerns)


def test_open_decisions_surface_as_needs_decision(staged_repo_and_request):
    root, request, _text, path = staged_repo_and_request
    mutated = canonical_intent(intent_id="INT-MF-0042", open_decisions=["Which CSV delimiter?"])
    write_exact(root / path, mutated)
    request["intent"]["frozenArtifactSha256"] = sha256(mutated)
    outcome = run_spec_design(request, **_mock_deps())
    assert outcome.result.status == "needs_decision"
    assert outcome.exit_code == EXIT_CODES["needs_decision"]
    assert len(outcome.result.human_decisions) >= 1


def test_generator_material_decision_yields_needs_decision_without_commit(staged_repo_and_request):
    root, request, _text, _path = staged_repo_and_request
    gen = MockGenerator(
        force_decisions=[HumanDecision(question="Which export format is authoritative?", impact="external contract", minimum_authority="Product owner")]
    )
    outcome = run_spec_design(request, generator=gen, config=load_config(provider="mock"))
    assert outcome.result.status == "needs_decision"
    assert outcome.result.spec_commit is None
    assert len(_git(root, ["log", "--oneline"]).splitlines()) == 1


def test_structurally_incomplete_spec_yields_failed(staged_repo_and_request):
    _root, request, _text, _path = staged_repo_and_request
    gen = MockGenerator(omit_sections={"Validation strategy", "Risks and unresolved decisions"})
    outcome = run_spec_design(request, generator=gen, config=load_config(provider="mock"))
    assert outcome.result.status == "failed"
    assert outcome.exit_code == EXIT_CODES["failed"]
    assert "missing required section: Validation strategy" in " ".join(outcome.result.blocking_concerns)


def test_generation_timeout_yields_failed(staged_repo_and_request):
    _root, request, _text, _path = staged_repo_and_request

    class SlowGenerator:
        name = "slow"

        def generate(self, data) -> SpecGenerationOutput:
            done = threading.Event()
            while not (data.cancel and data.cancel.is_set()):
                if done.wait(0.05):
                    break
            raise RuntimeError("aborted by caller")

    outcome = run_spec_design(
        request,
        generator=SlowGenerator(),
        config=load_config(provider="mock", generation_timeout_ms=100),
    )
    assert outcome.result.status == "failed"
    assert outcome.exit_code == EXIT_CODES["failed"]


def test_invalid_request_shape_raises_to_caller(staged_repo_and_request):
    _root, request, _text, _path = staged_repo_and_request
    del request["approval"]
    try:
        run_spec_design(request, **_mock_deps())
        assert False, "expected RequestValidationError"
    except Exception as exc:  # noqa: BLE001
        assert "failed validation" in str(exc)
