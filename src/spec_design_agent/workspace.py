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
    intent_rel: str
    spec_rel: str
    run_rel: str


def resolve_workspace_paths(request: SpecRequest) -> WorkspacePaths:
    root = Path(request.target.workspace).resolve()
    work_rel = Path(".agent") / "work" / request.work_item
    return WorkspacePaths(
        root=root,
        work_dir=root / work_rel,
        intent_rel=(work_rel / "intent.md").as_posix(),
        spec_rel=(work_rel / "spec.md").as_posix(),
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
    # SHA-256 of the raw bytes of the staged frozen intent.md (the frozen-artifact hash).
    frozen_artifact_sha256: str
    head_commit: str


def prepare_workspace(request: SpecRequest) -> PreparedWorkspace:
    """Confirm workspace isolation and ensure a byte-identical frozen intent is staged."""
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

    data: bytes | None = None
    if staged_intent.exists():
        data = staged_intent.read_bytes()
    else:
        conductor_copy = assert_scoped(paths.root, request.intent.path)
        if conductor_copy.exists():
            data = conductor_copy.read_bytes()
            staged_intent.write_bytes(data)

    if data is None:
        raise PreconditionError(
            "blocked",
            "INTENT_NOT_STAGED",
            "No frozen intent is available in the workspace; the Conductor must stage intent.md before Spec & Design",
        )

    return PreparedWorkspace(
        paths=paths,
        intent_path=staged_intent,
        frozen_artifact_sha256=sha256_bytes(data),
        head_commit=head,
    )


# Re-exported for callers that want the raw string form.
def rel_to_root(root: Path, path: Path) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")
