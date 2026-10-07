# ABOUTME: End-to-end tests driving the real CLI entrypoint as a child process, exactly as the
# ABOUTME: Conductor would invoke it. The mock provider keeps the run deterministic and offline.

import json
import subprocess
import sys
from pathlib import Path

from conftest import canonical_intent, sha256, write_exact


def _invoke(request_path: Path, extra: list[str] | None = None) -> tuple[int, dict, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "spec_design_agent", "spec", "--request", str(request_path), "--provider", "mock", *(extra or [])],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "SPEC_AGENT_PROVIDER": "mock"},
    )
    try:
        parsed = json.loads(proc.stdout) if proc.stdout.strip() else {"status": "no-output"}
    except json.JSONDecodeError:
        parsed = {"status": "unparseable", "raw": proc.stdout}
    return proc.returncode, parsed, proc.stderr


def _write(root: Path, request: dict) -> Path:
    path = root / "request.json"
    path.write_text(json.dumps(request, indent=2), encoding="utf-8")
    return path


def test_e2e_conductor_request_produces_committed_spec(staged_repo_and_request):
    root, request, _text, _path = staged_repo_and_request
    code, result, _stderr = _invoke(_write(root, request))

    assert code == 0
    assert result["status"] == "spec_ready"
    assert result["specCommit"]

    work_dir = root / ".agent/work/INT-MF-0042"
    assert "## Traceability to frozen intent" in (work_dir / "spec.md").read_text(encoding="utf-8")
    record = json.loads((work_dir / "spec-run.json").read_text(encoding="utf-8"))
    assert record["status"] == "spec_ready" and record["agentVersion"]

    show = subprocess.run(["git", "show", "--stat", "HEAD"], cwd=str(root), capture_output=True, text=True, check=True)
    assert "spec.md" in show.stdout


def test_e2e_missing_approval_exits_20(staged_repo_and_request):
    root, request, _text, _path = staged_repo_and_request
    request["approval"]["prioritized"] = False
    code, result, _stderr = _invoke(_write(root, request))
    assert code == 20
    assert result["status"] == "blocked"


def test_e2e_mutated_intent_exits_20(staged_repo_and_request):
    root, request, _text, path = staged_repo_and_request
    write_exact(root / path, canonical_intent(intent_id="INT-MF-0042") + "\n<!-- tampered -->\n")
    code, result, _stderr = _invoke(_write(root, request))
    assert code == 20
    assert result["status"] == "blocked"
    assert "INTENT_MUTATED" in " ".join(result["blockingConcerns"])


def test_e2e_ambiguous_requirement_exits_10(staged_repo_and_request):
    root, request, _text, path = staged_repo_and_request
    ambiguous = canonical_intent(intent_id="INT-MF-0042", open_decisions=["Which delimiter does finance require?"])
    write_exact(root / path, ambiguous)
    request["intent"]["frozenArtifactSha256"] = sha256(ambiguous)
    code, result, _stderr = _invoke(_write(root, request))
    assert code == 10
    assert result["status"] == "needs_decision"
    assert len(result["humanDecisions"]) >= 1


def test_e2e_invalid_workspace_exits_20(staged_repo_and_request):
    root, request, _text, _path = staged_repo_and_request
    request["target"]["workspace"] = str(root / "does-not-exist")
    code, result, _stderr = _invoke(_write(root, request))
    assert code == 20
    assert result["status"] == "blocked"


def test_e2e_malformed_request_file_exits_2(staged_repo_and_request):
    root, _request, _text, _path = staged_repo_and_request
    path = root / "request.json"
    path.write_text("{ not json", encoding="utf-8")
    code, _result, _stderr = _invoke(path)
    assert code == 2
