# ABOUTME: Shared deterministic fixtures for the test suite: a canonical frozen intent, a
# ABOUTME: matching valid work request, and throwaway Git repositories.

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

FORTY_HEX = "a" * 40
BASE_HEX = "b" * 40
PROFILE_TEXT = """# Policy & Compliance Profile

Profile ID: MF-DEFAULT
Version: 1

## Controls

| Control ID | Required agent action | Required evidence | Escalation trigger |
| --- | --- | --- | --- |
| SEC-BASE-001 | Do not expose or hardcode secrets. | Secret scan or equivalent deterministic check. | A secret is needed. |
"""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_exact(path: Path, text: str) -> None:
    """Write text as exact UTF-8 bytes, with no OS newline translation.

    The Conductor stages the frozen intent byte-for-byte; tests must do the same
    or the agent's integrity check will (correctly) reject a translated copy.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def canonical_intent(*, status: str = "Frozen", open_decisions: list[str] | None = None, intent_id: str = "INT-MF-0042") -> str:
    open_decisions = open_decisions or []
    open_block = "\n".join(f"- {d}" for d in open_decisions) if open_decisions else "- none"
    return f"""---
intent_id: {intent_id}
product_id: MF
product_name: MealFlow
trello_card_id: card-123
trello_card_url: https://trello.test/card-123
intent_version: 5
status: {status}
intent_commit: {FORTY_HEX}
intent_hash: sha256:deadbeef
frozen_commit: {FORTY_HEX}
frozen_at: 2026-09-06T12:00:00Z
---

# Intent: Weekly meal plan export

## Problem

Households cannot take their plan outside the app.

## Desired outcome

A household can export the current week's plan as a portable file.

## Evidence of success

Export completes in under 2 seconds for a 7-day plan.

## Constraints

Must not change the existing plan data model.

## Assumptions

Households have at most one active plan per week.

## Options

CSV, PDF, or ICS.

## Recommended direction

CSV first.

## Priority profile

Near-term, medium effort.

## Scope and non-goals

In scope: current-week export. Non-goal: historical plans.

## Acceptance criteria

- A logged-in household can download the current week's plan as CSV.
- The CSV lists one row per planned meal with date, meal slot, and recipe name.

## Open decisions

{open_block}

## Traceability and handoff
- Trello card: https://trello.test/card-123
- Canonical revision: https://github.test/intent-backlog
- Next stage: Engineering execution
"""


def valid_request(**overrides) -> dict:
    intent_text = canonical_intent()
    intent_path = "products/mealflow/intents/INT-MF-0042/intent.md"
    request = {
        "requestVersion": 2,
        "runId": "11111111-1111-1111-1111-111111111111",
        "invocationId": "invoke-INT-MF-0042",
        "triggerEventId": "event-123",
        "stage": "spec_design",
        "workItem": "INT-MF-0042",
        "productId": "MF",
        "intentContentSha256": sha256("canonical:" + intent_text),
        "freezeActivation": {
            "schema_version": "1.0",
            "event_id": "freeze-123",
            "event_type": "activated",
            "work_item": {"product_id": "MF", "intent_id": "INT-MF-0042", "intent_version": 5, "trello_card_id": "card-123"},
            "intent": {
                "repository": "https://github.com/dbacks95fan/intent-backlog",
                "commit_sha": FORTY_HEX,
                "path": intent_path,
                "sha256": sha256(intent_text),
            },
            "policy_profile_id": "MF-DEFAULT",
            "policy_profile_version": "1",
            "policy_profile": {
                "repository": "https://github.com/dbacks95fan/intent-backlog",
                "commit_sha": FORTY_HEX,
                "path": "products/mealflow/policy-profiles/MF-DEFAULT.md",
                "sha256": sha256(PROFILE_TEXT),
            },
            "authorized_by": "owner-1",
            "recorded_at": "2026-09-06T12:30:00Z",
        },
        "target": {
            "repository": "https://github.com/dbacks95fan/mealflow",
            "baseCommit": BASE_HEX,
            "branch": "work/INT-MF-0042",
            "workspace": "/work/INT-MF-0042",
        },
        "readPaths": ["."],
        "writePaths": [".agent/work/INT-MF-0042"],
    }
    request.update(overrides)
    return request


def _git(cwd: Path, args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True).stdout.strip()


def make_temp_repo(base: Path, work_item: str = "INT-MF-0042", files: dict[str, str] | None = None):
    files = files or {"README.md": "# fixture repo\n"}
    root = base / "repo"
    root.mkdir()
    _git(root, ["init", "--quiet"])
    _git(root, ["config", "user.email", "test@example.test"])
    _git(root, ["config", "user.name", "Spec Design Agent Test"])
    _git(root, ["config", "commit.gpgsign", "false"])
    for rel, contents in files.items():
        write_exact(root / rel, contents)
    _git(root, ["add", "-A"])
    _git(root, ["commit", "--quiet", "-m", "seed"])
    base_commit = _git(root, ["rev-parse", "HEAD"])
    branch = f"work/{work_item}"
    _git(root, ["checkout", "--quiet", "-b", branch])
    return root, base_commit, branch


@pytest.fixture
def temp_repo(tmp_path):
    return make_temp_repo(tmp_path)


@pytest.fixture
def staged_repo_and_request(tmp_path):
    """A temp repo on a work branch with the frozen intent staged by the "Conductor",
    plus a request whose intent hash matches those bytes."""
    work_item = "INT-MF-0042"
    intent_text = canonical_intent(intent_id=work_item)
    intent_path = f"products/mealflow/intents/{work_item}/intent.md"
    root, base_commit, branch = make_temp_repo(
        tmp_path,
        work_item,
        {
            "README.md": "# fixture product\n",
            "package.json": '{"name": "fixture", "scripts": {"test": "pytest"}}',
            "src/index.py": "def noop():\n    return None\n",
            intent_path: intent_text,
            f".agent/inputs/invoke-{work_item}/intent.md": intent_text,
            f".agent/inputs/invoke-{work_item}/policy-profile.md": PROFILE_TEXT,
        },
    )
    request = {
        "requestVersion": 2,
        "runId": f"run-{work_item}",
        "invocationId": f"invoke-{work_item}",
        "triggerEventId": "event-123",
        "stage": "spec_design",
        "workItem": work_item,
        "productId": "MF",
        "intentContentSha256": sha256("canonical:" + intent_text),
        "freezeActivation": {
            "schema_version": "1.0",
            "event_id": "freeze-123",
            "event_type": "activated",
            "work_item": {"product_id": "MF", "intent_id": work_item, "intent_version": 5, "trello_card_id": "card-123"},
            "intent": {
                "repository": "https://github.com/dbacks95fan/intent-backlog",
                "commit_sha": FORTY_HEX,
                "path": intent_path,
                "sha256": sha256(intent_text),
            },
            "policy_profile_id": "MF-DEFAULT",
            "policy_profile_version": "1",
            "policy_profile": {
                "repository": "https://github.com/dbacks95fan/intent-backlog",
                "commit_sha": FORTY_HEX,
                "path": "products/mealflow/policy-profiles/MF-DEFAULT.md",
                "sha256": sha256(PROFILE_TEXT),
            },
            "authorized_by": "owner-1",
            "recorded_at": "2026-09-06T12:30:00Z",
        },
        "target": {
            "repository": "https://github.com/dbacks95fan/mealflow",
            "baseCommit": base_commit,
            "branch": branch,
            "workspace": str(root),
        },
        "readPaths": ["."],
        "writePaths": [f".agent/work/{work_item}"],
    }
    return root, request, intent_text, intent_path
