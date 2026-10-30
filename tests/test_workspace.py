import subprocess
from pathlib import Path

import pytest
from conftest import FORTY_HEX, PROFILE_TEXT, canonical_intent, make_temp_repo, sha256, valid_request, write_exact

from spec_design_agent.git import push_branch, stage_and_commit
from spec_design_agent.types import PreconditionError, SpecRequest
from spec_design_agent.workspace import assert_scoped, prepare_workspace, resolve_workspace_paths


def _req(**target) -> SpecRequest:
    base = {
        "repository": "https://example.test/r",
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
    assert paths.policy_profile_rel == ".agent/work/INT-MF-0042/policy-profile.md"
    assert paths.spec_rel == ".agent/work/INT-MF-0042/spec.md"
    assert paths.work_contract_rel == ".agent/work/INT-MF-0042/work-contract.yaml"


def test_prepares_valid_workspace_and_stages_conductor_intent(tmp_path):
    intent_text = canonical_intent()
    root, base_commit, branch = make_temp_repo(
        tmp_path,
        "INT-MF-0042",
        {
            "README.md": "# fixture\n",
            ".agent/inputs/invoke-INT-MF-0042/intent.md": intent_text,
            ".agent/inputs/invoke-INT-MF-0042/policy-profile.md": PROFILE_TEXT,
        },
    )
    request = _req(baseCommit=base_commit, branch=branch, workspace=str(root))
    prepared = prepare_workspace(request)
    assert prepared.intent_sha256 == sha256(intent_text)
    assert prepared.policy_profile_sha256 == sha256(PROFILE_TEXT)
    assert prepared.head_commit == base_commit


def test_agent_clones_product_repo_creates_and_pushes_first_work_branch(tmp_path):
    source, base_commit, branch = make_temp_repo(tmp_path, files={"README.md": "# product\n"})
    bare = tmp_path / "product.git"
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(bare)], check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "push", "origin", f"{base_commit}:refs/heads/main"], cwd=source, check=True, capture_output=True)

    bundle = tmp_path / "bundle"
    input_dir = bundle / ".agent" / "inputs" / "invoke-INT-MF-0042"
    write_exact(input_dir / "intent.md", canonical_intent())
    write_exact(input_dir / "policy-profile.md", PROFILE_TEXT)
    request = _req(
        repository=bare.as_uri(),
        baseCommit=base_commit,
        branch=branch,
        workspace=str(bundle / "repository"),
    )

    prepared = prepare_workspace(request)
    git_current = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=bundle / "repository", capture_output=True, text=True, check=True
    ).stdout.strip()
    assert git_current == branch
    assert prepared.head_commit == base_commit

    push_branch(bundle / "repository", branch)
    remote = subprocess.run(
        ["git", "--git-dir", str(bare), "show-ref", "--verify", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert remote.split()[0] == base_commit


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
    (bare / "unexpected.txt").write_text("preserve this", encoding="utf-8")
    request = _req(workspace=str(bare))
    with pytest.raises(PreconditionError) as exc:
        prepare_workspace(request)
    assert exc.value.code == "WORKSPACE_NOT_GIT"


def test_blocks_when_policy_profile_bytes_do_not_match_freeze_record(tmp_path):
    root, base_commit, branch = make_temp_repo(
        tmp_path,
        "INT-MF-0042",
        {
            ".agent/inputs/invoke-INT-MF-0042/intent.md": canonical_intent(),
            ".agent/inputs/invoke-INT-MF-0042/policy-profile.md": PROFILE_TEXT + "\nchanged\n",
        },
    )
    request = _req(baseCommit=base_commit, branch=branch, workspace=str(root))
    with pytest.raises(PreconditionError) as exc:
        prepare_workspace(request)
    assert exc.value.code == "POLICY_PROFILE_MUTATED"


def test_copies_both_frozen_inputs_to_agent_work_directory(tmp_path):
    intent_text = canonical_intent()
    root, base_commit, branch = make_temp_repo(
        tmp_path,
        "INT-MF-0042",
        {
            ".agent/inputs/invoke-INT-MF-0042/intent.md": intent_text,
            ".agent/inputs/invoke-INT-MF-0042/policy-profile.md": PROFILE_TEXT,
        },
    )
    request = _req(
        baseCommit=base_commit,
        branch=branch,
        workspace=str(root),
    )
    prepared = prepare_workspace(request)
    assert prepared.intent_sha256 == sha256(intent_text)
    assert (root / ".agent/work/INT-MF-0042/intent.md").read_text(encoding="utf-8") == intent_text
    assert (root / ".agent/work/INT-MF-0042/policy-profile.md").read_text(encoding="utf-8") == PROFILE_TEXT


def test_commits_required_artifacts_even_when_agent_directory_is_ignored(tmp_path):
    root, base_commit, branch = make_temp_repo(
        tmp_path,
        "INT-MF-0042",
        {".gitignore": ".agent/\n", "README.md": "# fixture\n"},
    )
    # The invocation runtime stages its read-only snapshots after the base commit.
    write_exact(root / ".agent/inputs/invoke-INT-MF-0042/intent.md", canonical_intent())
    write_exact(root / ".agent/inputs/invoke-INT-MF-0042/policy-profile.md", PROFILE_TEXT)
    request = _req(baseCommit=base_commit, branch=branch, workspace=str(root))
    prepared = prepare_workspace(request)
    (prepared.paths.work_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    commit = stage_and_commit(
        root,
        [prepared.paths.intent_rel, prepared.paths.policy_profile_rel, prepared.paths.spec_rel],
        "fixture artifacts",
    )
    committed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", commit], cwd=root, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert prepared.paths.intent_rel in committed
    assert prepared.paths.policy_profile_rel in committed
    assert prepared.paths.spec_rel in committed
