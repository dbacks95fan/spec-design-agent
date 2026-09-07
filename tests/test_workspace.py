from pathlib import Path

import pytest
from conftest import FORTY_HEX, canonical_intent, make_temp_repo, sha256, valid_request, write_exact

from spec_design_agent.types import PreconditionError, SpecRequest
from spec_design_agent.workspace import assert_scoped, prepare_workspace, resolve_workspace_paths


def _req(**target) -> SpecRequest:
    base = {
        "repository": "o/r",
        "baseCommit": FORTY_HEX,
        "branch": "work/INT-MF-0042",
        "workspace": "/tmp/x",
    }
    base.update(target)
    return SpecRequest.from_dict(valid_request(target=base))


def test_assert_scoped_rejects_traversal_and_absolute_escape():
    root = Path("/work/x").resolve()
    with pytest.raises(PreconditionError):
        assert_scoped(root, "../y/intent.md")
    with pytest.raises(PreconditionError):
        assert_scoped(root, str(Path("/etc/passwd").resolve()))
    assert assert_scoped(root, "sub/ok.md") == (root / "sub/ok.md").resolve()


def test_resolve_workspace_paths_places_artifacts_under_agent_work():
    paths = resolve_workspace_paths(SpecRequest.from_dict(valid_request()))
    assert paths.intent_rel == ".agent/work/INT-MF-0042/intent.md"
    assert paths.spec_rel == ".agent/work/INT-MF-0042/spec.md"


def test_prepares_valid_workspace_and_stages_conductor_intent(tmp_path):
    intent_text = canonical_intent()
    root, base_commit, branch = make_temp_repo(
        tmp_path,
        "INT-MF-0042",
        {
            "README.md": "# fixture\n",
            "products/mealflow/intents/INT-MF-0042/intent.md": intent_text,
        },
    )
    request = _req(baseCommit=base_commit, branch=branch, workspace=str(root))
    prepared = prepare_workspace(request)
    assert prepared.frozen_artifact_sha256 == sha256(intent_text)
    assert prepared.head_commit == base_commit


def test_blocks_wrong_branch(tmp_path):
    root, base_commit, _branch = make_temp_repo(tmp_path)
    request = _req(baseCommit=base_commit, branch="work/INT-OTHER-1", workspace=str(root))
    with pytest.raises(PreconditionError) as exc:
        prepare_workspace(request)
    assert exc.value.code == "WORKSPACE_WRONG_BRANCH"


def test_blocks_when_no_intent_available(tmp_path):
    root, base_commit, branch = make_temp_repo(tmp_path)
    request = _req(baseCommit=base_commit, branch=branch, workspace=str(root))
    with pytest.raises(PreconditionError) as exc:
        prepare_workspace(request)
    assert exc.value.code == "INTENT_NOT_STAGED"


def test_blocks_non_git_workspace(tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    request = _req(workspace=str(bare))
    with pytest.raises(PreconditionError) as exc:
        prepare_workspace(request)
    assert exc.value.code == "WORKSPACE_NOT_GIT"


def test_reuses_already_staged_intent(tmp_path):
    intent_text = canonical_intent()
    root, base_commit, branch = make_temp_repo(tmp_path)
    work_dir = root / ".agent/work/INT-MF-0042"
    work_dir.mkdir(parents=True)
    write_exact(work_dir / "intent.md", intent_text)
    request = _req(
        baseCommit=base_commit,
        branch=branch,
        workspace=str(root),
    )
    prepared = prepare_workspace(request)
    assert prepared.frozen_artifact_sha256 == sha256(intent_text)
