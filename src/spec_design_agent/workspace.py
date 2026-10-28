# ABOUTME: Verifies the assigned workspace is isolated to this work item and stages the
# ABOUTME: byte-for-byte frozen intent. Rejects path traversal and cross-work-item paths.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import git
from .integrity import sha256_bytes
from .types import PreconditionError, SpecRequest


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    work_dir: Path
    intent_input: Path
    policy_profile_input: Path
    intent_rel: str
    policy_profile_rel: str
    spec_rel: str
    work_contract_rel: str
    run_rel: str


def resolve_workspace_paths(request: SpecRequest) -> WorkspacePaths:
    root = Path(request.target.workspace).resolve()
    work_rel = Path(".agent") / "work" / request.work_item
    input_rel = Path(".agent") / "inputs" / request.invocation_id
    return WorkspacePaths(
        root=root,
        work_dir=root / work_rel,
        intent_input=root / input_rel / "intent.md",
        policy_profile_input=root / input_rel / "policy-profile.md",
        intent_rel=(work_rel / "intent.md").as_posix(),
        policy_profile_rel=(work_rel / "policy-profile.md").as_posix(),
        spec_rel=(work_rel / "spec.md").as_posix(),
        work_contract_rel=(work_rel / "work-contract.yaml").as_posix(),
        run_rel=(work_rel / "spec-run.json").as_posix(),
    )


def assert_scoped(root: Path, candidate: str) -> Path:
    """Raise unless `candidate` resolves to a path strictly inside `root`."""
    base = Path(candidate)
    resolved = (base if base.is_absolute() else root / base).resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError:
        raise PreconditionError("blocked", "PATH_ESCAPE", f"Path '{candidate}' escapes the workspace root")
    if rel == Path("."):
        raise PreconditionError("blocked", "PATH_ESCAPE", f"Path '{candidate}' escapes the workspace root")
    return resolved


@dataclass(frozen=True)
class PreparedWorkspace:
    paths: WorkspacePaths
    intent_path: Path
    policy_profile_path: Path
    intent_sha256: str
    policy_profile_sha256: str
    head_commit: str


def prepare_workspace(request: SpecRequest) -> PreparedWorkspace:
    """Confirm the assigned worktree and copy both frozen snapshots byte-for-byte."""
    paths = resolve_workspace_paths(request)

    if not paths.root.exists():
        raise PreconditionError("blocked", "WORKSPACE_MISSING", f"Workspace '{paths.root}' does not exist")
    if not git.is_inside_work_tree(paths.root):
        raise PreconditionError("blocked", "WORKSPACE_NOT_GIT", f"Workspace '{paths.root}' is not a Git work tree")

    branch = git.current_branch(paths.root)
    if branch != request.target.branch:
        raise PreconditionError(
            "blocked",
            "WORKSPACE_WRONG_BRANCH",
            f"Workspace is on branch '{branch}', expected '{request.target.branch}'",
        )

    head = git.head_commit(paths.root)
    if head != request.target.base_commit and not git.is_ancestor(paths.root, request.target.base_commit, head):
        raise PreconditionError(
            "blocked",
            "WORKSPACE_WRONG_BASE",
            f"Requested base commit {request.target.base_commit} is not reachable from workspace HEAD {head}",
        )

    paths.work_dir.mkdir(parents=True, exist_ok=True)
    staged_intent = paths.work_dir / "intent.md"
    staged_profile = paths.work_dir / "policy-profile.md"
    if not paths.intent_input.is_file():
        raise PreconditionError("blocked", "INTENT_NOT_STAGED", "The invocation has no staged frozen intent snapshot")
    if not paths.policy_profile_input.is_file():
        raise PreconditionError("blocked", "POLICY_PROFILE_NOT_STAGED", "The invocation has no staged frozen policy-profile snapshot")

    intent_data = paths.intent_input.read_bytes()
    profile_data = paths.policy_profile_input.read_bytes()
    intent_hash = sha256_bytes(intent_data)
    profile_hash = sha256_bytes(profile_data)
    if intent_hash != request.intent.frozen_artifact_sha256:
        raise PreconditionError("blocked", "INTENT_MUTATED", "Staged frozen intent bytes do not match the Prioritized freeze record")
    if profile_hash != request.policy_profile.frozen_artifact_sha256:
        raise PreconditionError("blocked", "POLICY_PROFILE_MUTATED", "Staged policy-profile bytes do not match the Prioritized freeze record")

    staged_intent.write_bytes(intent_data)
    staged_profile.write_bytes(profile_data)

    return PreparedWorkspace(
        paths=paths,
        intent_path=staged_intent,
        intent_sha256=intent_hash,
        policy_profile_sha256=profile_hash,
        policy_profile_path=staged_profile,
        head_commit=head,
    )


# Re-exported for callers that want the raw string form.
def rel_to_root(root: Path, path: Path) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")
