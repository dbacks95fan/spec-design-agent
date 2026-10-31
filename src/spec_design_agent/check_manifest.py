# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Reads the operator-controlled check manifest that the Coding Agent also enforces, so a Work
# ABOUTME: Contract only ever names trusted, repository-approved checks with their exact commands.

from __future__ import annotations

import json
from pathlib import Path

from .types import PreconditionError


def normalize_repo_url(url: str) -> str:
    """Compares repository URLs ignoring case, a trailing slash, and a trailing ".git", like the Coding Agent."""
    value = url.strip().rstrip("/")
    if value.lower().endswith(".git"):
        value = value[:-4]
    return value.rstrip("/").lower()


def _blocked(code: str, message: str) -> PreconditionError:
    return PreconditionError("blocked", code, message)


def required_validation_for(manifest_path: str | None, repository: str) -> list[dict[str, str]]:
    """Returns the manifest's checks for `repository` as Work Contract `required_validation` entries.

    The manifest is the single source of trusted check names and commands. Nothing is inferred from
    the target repository, because a spec run must not widen what the Coding Agent will execute.
    """
    if not manifest_path:
        raise _blocked("CHECK_MANIFEST_NOT_CONFIGURED", "SPEC_AGENT_CHECK_MANIFEST is not set; the trusted check manifest is required.")
    try:
        data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except OSError as error:
        raise _blocked("CHECK_MANIFEST_UNREADABLE", f"The check manifest could not be read: {error}") from error
    except json.JSONDecodeError as error:
        raise _blocked("CHECK_MANIFEST_INVALID", f"The check manifest is not valid JSON: {error}") from error

    repositories = data.get("repositories") if isinstance(data, dict) else None
    if not isinstance(repositories, list) or not repositories:
        raise _blocked("CHECK_MANIFEST_INVALID", "The check manifest must contain a non-empty repositories array.")

    wanted = normalize_repo_url(repository)
    matches = [entry for entry in repositories if isinstance(entry, dict) and isinstance(entry.get("url"), str) and normalize_repo_url(entry["url"]) == wanted]
    if not matches:
        raise _blocked("CHECK_MANIFEST_REPOSITORY_UNKNOWN", f"The check manifest has no entry for target repository {repository}.")
    if len(matches) > 1:
        raise _blocked("CHECK_MANIFEST_INVALID", f"The check manifest lists target repository {repository} more than once.")

    checks = matches[0].get("checks")
    if not isinstance(checks, dict) or not checks:
        raise _blocked("CHECK_MANIFEST_INVALID", f"The check manifest entry for {repository} must map check names to commands.")
    validation: list[dict[str, str]] = []
    for name, command in checks.items():
        if not isinstance(name, str) or not name or not isinstance(command, str) or not command:
            raise _blocked("CHECK_MANIFEST_INVALID", f"The check manifest entry for {repository} has an empty check name or command.")
        validation.append({"name": name, "command": command})
    return validation
