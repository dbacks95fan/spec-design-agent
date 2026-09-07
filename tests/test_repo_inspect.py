from dataclasses import replace

from conftest import make_temp_repo

from spec_design_agent.repo_inspect import DEFAULT_LIMITS, inspect_repository


def test_collects_instructions_and_language_facts_without_writing(tmp_path):
    root, _base, _branch = make_temp_repo(
        tmp_path,
        "INT-MF-0042",
        {
            "CLAUDE.md": "# house rules\nUse Python.\n",
            "package.json": '{"scripts": {"test": "pytest"}}',
            "src/index.py": "x = 1\n",
            "src/test_index.py": "def test_x():\n    pass\n",
        },
    )
    before = sorted(p.name for p in root.iterdir())
    facts = inspect_repository(root)

    assert any(f.path == "CLAUDE.md" and "house rules" in f.excerpt for f in facts.instruction_files)
    assert facts.language_histogram[".py"] == 2
    assert any("npm test" in s for s in facts.test_signals)
    assert "colocated unit tests present" in facts.test_signals

    assert sorted(p.name for p in root.iterdir()) == before


def test_stops_at_max_files_bound(tmp_path):
    files = {"README.md": "x"}
    files.update({f"f{i}.txt": "x" for i in range(20)})
    root, _base, _branch = make_temp_repo(tmp_path, "INT-MF-0042", files)
    facts = inspect_repository(root, replace(DEFAULT_LIMITS, max_files=5))
    assert facts.limit_hit == "maxFiles"
    assert facts.files_scanned <= 6


def test_truncates_oversized_instruction_files(tmp_path):
    root, _base, _branch = make_temp_repo(tmp_path, "INT-MF-0042", {"AGENTS.md": "A" * 5000})
    facts = inspect_repository(root, replace(DEFAULT_LIMITS, max_bytes_per_file=1000))
    agents = next(f for f in facts.instruction_files if f.path == "AGENTS.md")
    assert agents.truncated is True
    assert len(agents.excerpt) == 1000
