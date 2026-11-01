# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Verifies the model's read-only repository tools stay inside the checkout, never expose
# ABOUTME: .git, cap their output, and report refusals as text instead of raising.

import json
import os

import pytest

from spec_design_agent.generators import repo_tools
from spec_design_agent.generators.repo_tools import run_tool


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text(
        "def plan_week():\n    return 'Weekly Plan'\n", encoding="utf-8"
    )
    (root / "README.md").write_text("# Product\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (root / "node_modules" / "dep").mkdir(parents=True)
    (root / "node_modules" / "dep" / "index.js").write_text(
        "weekly plan in a dependency\n", encoding="utf-8"
    )
    (root / "image.bin").write_bytes(b"\x89PNG\x00\x00")
    (tmp_path / "outside.txt").write_text(
        "secret outside the checkout\n", encoding="utf-8"
    )
    return root


def call(root, name, **args):
    return run_tool(root, name, json.dumps(args))


def test_lists_a_directory_without_git(repo):
    listing = call(repo, "list_directory", path=".")
    assert listing.splitlines() == ["README.md", "image.bin", "node_modules/", "src/"]


def test_reads_a_file_and_continues_from_an_offset(repo, monkeypatch):
    assert call(repo, "read_file", path="src/app.py", offset=None).startswith(
        "def plan_week"
    )
    monkeypatch.setattr(repo_tools, "MAX_READ_BYTES", 10)
    first = call(repo, "read_file", path="src/app.py", offset=None)
    assert first.startswith("def plan_w") and "call again with offset 10" in first
    assert call(repo, "read_file", path="src/app.py", offset=10).startswith("eek()")


def test_search_is_case_insensitive_and_skips_dependency_folders(repo):
    result = call(repo, "search_files", text="weekly plan", path=None)
    assert result == "src/app.py:2: return 'Weekly Plan'"


@pytest.mark.parametrize(
    ("name", "args", "message"),
    [
        (
            "read_file",
            {"path": "../outside.txt", "offset": None},
            "outside the repository",
        ),
        (
            "read_file",
            {"path": "/etc/passwd", "offset": None},
            "repository-relative",
        ),
        (
            "read_file",
            {"path": ".git/config", "offset": None},
            ".git directory is not readable",
        ),
        ("list_directory", {"path": ".git"}, ".git directory is not readable"),
        ("search_files", {"text": "x", "path": "src/../.."}, "outside the repository"),
        ("read_file", {"path": "image.bin", "offset": None}, "looks binary"),
        ("read_file", {"path": "src", "offset": None}, "is not a file"),
        ("read_file", {"path": "src/app.py", "offset": -1}, "must not be negative"),
        ("search_files", {"text": "", "path": None}, "non-empty"),
        ("write_file", {"path": "x"}, "unknown tool"),
    ],
)
def test_refusals_come_back_as_error_text(repo, name, args, message):
    result = call(repo, name, **args)
    assert result.startswith("error: ") and message in result


def test_a_symlink_out_of_the_checkout_is_refused(repo, tmp_path):
    try:
        os.symlink(tmp_path / "outside.txt", repo / "link.txt")
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not allow creating symlinks here")
    assert "outside the repository" in call(
        repo, "read_file", path="link.txt", offset=None
    )


def test_malformed_arguments_are_reported_not_raised(repo):
    assert (
        run_tool(repo, "read_file", "{not json")
        == "error: arguments were not valid JSON"
    )
    assert (
        run_tool(repo, "read_file", "[1]") == "error: arguments must be a JSON object"
    )
