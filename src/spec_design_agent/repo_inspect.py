# ABOUTME: Bounded, read-only inspection of the target repository. Gathers repo-local
# ABOUTME: instructions and structural facts for the spec prompt without modifying source.

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class InspectionLimits:
    max_files: int = 4000
    max_bytes_per_file: int = 64 * 1024
    max_depth: int = 6
    deadline_ms: int = 20_000


DEFAULT_LIMITS = InspectionLimits()


@dataclass
class InstructionFile:
    path: str
    excerpt: str
    truncated: bool


@dataclass
class RepoFacts:
    instruction_files: list[InstructionFile] = field(default_factory=list)
    language_histogram: dict[str, int] = field(default_factory=dict)
    test_signals: list[str] = field(default_factory=list)
    top_level_entries: list[str] = field(default_factory=list)
    files_scanned: int = 0
    limit_hit: str | None = None


_IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "out", ".agent", ".venv", "venv",
    "__pycache__", ".next", "target", "coverage", ".idea", ".vscode",
}
_INSTRUCTION_FILES = [
    "CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules",
    "CONTRIBUTING.md", "README.md", "ARCHITECTURE.md",
]
_TEST_MARKERS = [
    ("pytest.ini", "python: pytest"),
    ("tox.ini", "python: tox"),
    ("go.mod", "go: go test"),
    ("Cargo.toml", "rust: cargo test"),
    ("vitest.config.ts", "js: vitest"),
    ("jest.config.js", "js: jest"),
    ("playwright.config.ts", "js: playwright"),
]
_TEST_FILE = re.compile(r"\.(test|spec)\.[jt]sx?$|^test_.*\.py$")


def _read_excerpt(path: Path, max_bytes: int) -> tuple[str, bool]:
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    return data[:max_bytes].decode("utf-8", errors="replace"), truncated


def inspect_repository(root: str | Path, limits: InspectionLimits = DEFAULT_LIMITS) -> RepoFacts:
    root = Path(root)
    deadline = time.monotonic() + limits.deadline_ms / 1000
    facts = RepoFacts()
    test_signals: set[str] = set()

    facts.top_level_entries = sorted(
        (f"{e.name}/" if e.is_dir() else e.name) for e in root.iterdir()
    )

    for name in _INSTRUCTION_FILES:
        p = root / name
        if p.is_file():
            excerpt, truncated = _read_excerpt(p, limits.max_bytes_per_file)
            facts.instruction_files.append(InstructionFile(path=name, excerpt=excerpt, truncated=truncated))

    for marker, signal in _TEST_MARKERS:
        if (root / marker).is_file():
            test_signals.add(signal)
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
            if scripts.get("test"):
                test_signals.add(f"js: npm test -> {scripts['test']}")
        except (json.JSONDecodeError, OSError):
            pass

    def walk(directory: Path, depth: int) -> None:
        if facts.limit_hit:
            return
        if time.monotonic() > deadline:
            facts.limit_hit = "deadline"
            return
        if depth > limits.max_depth:
            facts.limit_hit = facts.limit_hit or "maxDepth"
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda e: e.name)
        except OSError:
            return
        for entry in entries:
            if facts.limit_hit:
                return
            if entry.is_dir():
                if entry.name in _IGNORED_DIRS or entry.name.startswith("."):
                    continue
                walk(entry, depth + 1)
            elif entry.is_file():
                facts.files_scanned += 1
                if facts.files_scanned > limits.max_files:
                    facts.limit_hit = "maxFiles"
                    return
                ext = entry.suffix.lower() or entry.name
                facts.language_histogram[ext] = facts.language_histogram.get(ext, 0) + 1
                if _TEST_FILE.search(entry.name):
                    test_signals.add("colocated unit tests present")

    walk(root, 1)
    facts.test_signals = sorted(test_signals)
    return facts
