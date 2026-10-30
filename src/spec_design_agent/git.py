# ABOUTME: Minimal Git wrappers used for workspace verification and the single agent-owned
# ABOUTME: artifact commit. All calls use argument lists (no shell).

from __future__ import annotations

import subprocess
import os
from pathlib import Path


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    if env.get("GITHUB_TOKEN") and not env.get("GIT_CONFIG_COUNT"):
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "credential.helper"
        env["GIT_CONFIG_VALUE_0"] = '!f(){ echo username=x-access-token; echo "password=$GITHUB_TOKEN"; };f'
    return env


def _git(cwd: str | Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        env=_git_env(),
    )
    return result.stdout.strip()


def is_inside_work_tree(cwd: str | Path) -> bool:
    if not Path(cwd).exists():
        return False
    try:
        return _git(cwd, ["rev-parse", "--is-inside-work-tree"]) == "true"
    except (OSError, subprocess.CalledProcessError):
        return False


def head_commit(cwd: str | Path) -> str:
    return _git(cwd, ["rev-parse", "HEAD"])


def current_branch(cwd: str | Path) -> str:
    return _git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"])


def clone_repository(repository: str, destination: str | Path) -> None:
    _git(Path(destination).parent, ["clone", "--no-hardlinks", "--no-checkout", repository, str(destination)])


def checkout_detached(cwd: str | Path, revision: str) -> None:
    _git(cwd, ["checkout", "--detach", revision])


def remote_branch_exists(cwd: str | Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=_git_env(),
    )
    if result.returncode == 0:
        return bool(result.stdout.strip())
    if result.returncode == 2:
        return False
    raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)


def checkout_work_branch(cwd: str | Path, branch: str, base_commit: str) -> None:
    if remote_branch_exists(cwd, branch):
        _git(cwd, ["fetch", "origin", f"{branch}:refs/remotes/origin/{branch}"])
        _git(cwd, ["checkout", "-B", branch, f"origin/{branch}"])
        if not is_ancestor(cwd, base_commit, head_commit(cwd)):
            raise RuntimeError("The existing remote work branch does not contain the assigned base commit.")
    else:
        _git(cwd, ["checkout", "-b", branch, base_commit])


def is_ancestor(cwd: str | Path, ancestor: str, descendant: str) -> bool:
    try:
        _git(cwd, ["merge-base", "--is-ancestor", ancestor, descendant])
        return True
    except subprocess.CalledProcessError:
        return False


def stage_and_commit(cwd: str | Path, paths: list[str], message: str) -> str:
    _git(cwd, ["add", "--force", "--", *paths])
    _git(cwd, ["commit", "-m", message])
    return head_commit(cwd)


def push_branch(cwd: str | Path, branch: str) -> None:
    _git(cwd, ["push", "--set-upstream", "origin", branch])
