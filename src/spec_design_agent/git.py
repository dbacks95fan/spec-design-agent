# ABOUTME: Minimal Git wrappers used for workspace verification and the single agent-owned
# ABOUTME: artifact commit. All calls use argument lists (no shell).

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(cwd: str | Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def is_inside_work_tree(cwd: str | Path) -> bool:
    try:
        return _git(cwd, ["rev-parse", "--is-inside-work-tree"]) == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def head_commit(cwd: str | Path) -> str:
    return _git(cwd, ["rev-parse", "HEAD"])


def current_branch(cwd: str | Path) -> str:
    return _git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"])


def is_ancestor(cwd: str | Path, ancestor: str, descendant: str) -> bool:
    try:
        _git(cwd, ["merge-base", "--is-ancestor", ancestor, descendant])
        return True
    except subprocess.CalledProcessError:
        return False


def stage_and_commit(cwd: str | Path, paths: list[str], message: str) -> str:
    _git(cwd, ["add", "--", *paths])
    _git(cwd, ["commit", "-m", message])
    return head_commit(cwd)
