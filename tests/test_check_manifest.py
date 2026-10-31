# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Verifies required validation comes only from the trusted check manifest, and that every
# ABOUTME: missing, malformed, or unknown-repository manifest blocks the run instead of guessing.

import json

import pytest

from spec_design_agent.check_manifest import normalize_repo_url, required_validation_for
from spec_design_agent.types import PreconditionError


def _manifest(tmp_path, data) -> str:
    path = tmp_path / "manifest.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return str(path)


def _blocked_code(manifest_path, repository="https://github.com/dbacks95fan/mealflow") -> str:
    with pytest.raises(PreconditionError) as caught:
        required_validation_for(manifest_path, repository)
    assert caught.value.status == "blocked"
    return caught.value.code


def test_returns_the_manifest_checks_for_the_target_repository_in_order(check_manifest):
    assert required_validation_for(str(check_manifest), "https://github.com/dbacks95fan/mealflow") == [
        {"name": "build", "command": "npm run build"},
        {"name": "automated_tests", "command": "npm run test:server"},
    ]


@pytest.mark.parametrize(
    "url",
    ["https://github.com/dbacks95fan/mealflow", "https://github.com/dbacks95fan/mealflow.git", "https://GitHub.com/dbacks95fan/MealFlow/"],
)
def test_repository_urls_match_like_the_coding_agent(url):
    assert normalize_repo_url(url) == "https://github.com/dbacks95fan/mealflow"


def test_unset_manifest_blocks():
    assert _blocked_code(None) == "CHECK_MANIFEST_NOT_CONFIGURED"


def test_missing_manifest_file_blocks(tmp_path):
    assert _blocked_code(str(tmp_path / "absent.json")) == "CHECK_MANIFEST_UNREADABLE"


def test_non_json_manifest_blocks(tmp_path):
    assert _blocked_code(_manifest(tmp_path, "{not json")) == "CHECK_MANIFEST_INVALID"


def test_manifest_without_repositories_blocks(tmp_path):
    assert _blocked_code(_manifest(tmp_path, {"repositories": []})) == "CHECK_MANIFEST_INVALID"


def test_unknown_repository_blocks(check_manifest):
    assert _blocked_code(str(check_manifest), "https://github.com/dbacks95fan/perioparrot") == "CHECK_MANIFEST_REPOSITORY_UNKNOWN"


def test_duplicate_repository_entries_block(tmp_path):
    entry = {"url": "https://github.com/dbacks95fan/mealflow", "checks": {"build": "npm run build"}}
    assert _blocked_code(_manifest(tmp_path, {"repositories": [entry, entry]})) == "CHECK_MANIFEST_INVALID"


@pytest.mark.parametrize("checks", [{}, None, {"build": ""}, {"": "npm run build"}, {"build": 7}])
def test_empty_or_malformed_checks_block(tmp_path, checks):
    manifest = {"repositories": [{"url": "https://github.com/dbacks95fan/mealflow", "checks": checks}]}
    assert _blocked_code(_manifest(tmp_path, manifest)) == "CHECK_MANIFEST_INVALID"
