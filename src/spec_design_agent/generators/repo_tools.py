# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Read-only repository tools a model may call while drafting a spec: list a directory,
# ABOUTME: read a file, and search text. Every path is confined to the workspace checkout.

from __future__ import annotations

import json
import os
from pathlib import Path

MAX_LIST_ENTRIES = 500
MAX_READ_BYTES = 64 * 1024
MAX_SEARCH_MATCHES = 100
MAX_SEARCH_FILES = 4000
MAX_SEARCH_FILE_BYTES = 1024 * 1024

# Skipped when walking for search; still readable by explicit path, except .git.
_WALK_SKIP = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "out",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "target",
    "coverage",
}

TOOL_DEFINITIONS: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "list_directory",
        "description": "List the entries of a directory in the product repository. Directories end with '/'.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Repository-relative path; '.' for the root.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": f"Read a UTF-8 text file from the product repository, up to {MAX_READ_BYTES} bytes from a byte offset.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Repository-relative file path.",
                },
                "offset": {
                    "type": ["integer", "null"],
                    "description": "Byte offset to start from; null for 0.",
                },
            },
            "required": ["path", "offset"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_files",
        "description": f"Case-insensitive literal text search across repository files. Returns up to {MAX_SEARCH_MATCHES} 'path:line: text' matches.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Literal text to find."},
                "path": {
                    "type": ["string", "null"],
                    "description": "Repository-relative directory to search; null for the root.",
                },
            },
            "required": ["text", "path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class ToolError(Exception):
    """A refused or failed tool call, reported back to the model rather than ending the run."""


def _resolve(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ToolError("path must be a non-empty repository-relative path")
    if Path(relative).is_absolute() or relative.startswith(("/", "\\")):
        raise ToolError("path must be repository-relative")
    target = (root / relative).resolve()
    # resolve() follows symlinks, so a link pointing outside the checkout is caught here too.
    if target != root and root not in target.parents:
        raise ToolError("path is outside the repository")
    if ".git" in target.relative_to(root).parts:
        raise ToolError("the .git directory is not readable")
    return target


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def list_directory(root: Path, path: str) -> str:
    target = _resolve(root, path)
    if not target.is_dir():
        raise ToolError(f"{path} is not a directory")
    entries = sorted(
        (entry.name + "/" if entry.is_dir() else entry.name)
        for entry in target.iterdir()
        if entry.name != ".git"
    )
    shown = entries[:MAX_LIST_ENTRIES]
    suffix = (
        [f"... {len(entries) - len(shown)} more entries not shown"]
        if len(entries) > len(shown)
        else []
    )
    return "\n".join(shown + suffix) or "(empty directory)"


def read_file(root: Path, path: str, offset: int | None) -> str:
    target = _resolve(root, path)
    if not target.is_file():
        raise ToolError(f"{path} is not a file")
    start = offset or 0
    if start < 0:
        raise ToolError("offset must not be negative")
    size = target.stat().st_size
    with target.open("rb") as handle:
        handle.seek(start)
        data = handle.read(MAX_READ_BYTES)
    if b"\x00" in data:
        raise ToolError(f"{path} looks binary and was not read")
    text = data.decode("utf-8", errors="replace")
    end = start + len(data)
    if end < size:
        text += f"\n... truncated at byte {end} of {size}; call again with offset {end} to continue"
    return text


def search_files(root: Path, text: str, path: str | None) -> str:
    if not isinstance(text, str) or not text:
        raise ToolError("text must be a non-empty string")
    base = _resolve(root, path or ".")
    if not base.is_dir():
        raise ToolError(f"{path} is not a directory")
    needle = text.lower()
    matches: list[str] = []
    scanned = 0
    for directory, subdirs, files in os.walk(base):
        subdirs[:] = sorted(d for d in subdirs if d not in _WALK_SKIP)
        for name in sorted(files):
            scanned += 1
            if scanned > MAX_SEARCH_FILES:
                matches.append(f"... stopped after {MAX_SEARCH_FILES} files")
                return "\n".join(matches)
            file_path = Path(directory) / name
            try:
                if (
                    file_path.is_symlink()
                    or file_path.stat().st_size > MAX_SEARCH_FILE_BYTES
                ):
                    continue
                data = file_path.read_bytes()
            except OSError:
                continue
            if b"\x00" in data:
                continue
            for number, line in enumerate(
                data.decode("utf-8", errors="replace").splitlines(), start=1
            ):
                if needle in line.lower():
                    matches.append(
                        f"{_relative(root, file_path)}:{number}: {line.strip()[:300]}"
                    )
                    if len(matches) >= MAX_SEARCH_MATCHES:
                        return "\n".join(matches + ["... match limit reached"])
    return "\n".join(matches) or "(no matches)"


def run_tool(root: str | Path, name: str, arguments: str) -> str:
    """Runs one model tool call. Refusals and bad arguments come back as text for the model."""
    repo = Path(root).resolve()
    try:
        args = json.loads(arguments) if arguments else {}
        if not isinstance(args, dict):
            raise ToolError("arguments must be a JSON object")
        if name == "list_directory":
            return list_directory(repo, args.get("path", "."))
        if name == "read_file":
            return read_file(repo, args.get("path", ""), args.get("offset"))
        if name == "search_files":
            return search_files(repo, args.get("text", ""), args.get("path"))
        raise ToolError(f"unknown tool {name!r}")
    except json.JSONDecodeError:
        return "error: arguments were not valid JSON"
    except ToolError as exc:
        return f"error: {exc}"
