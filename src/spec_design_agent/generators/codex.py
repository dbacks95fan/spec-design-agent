# ABOUTME: Codex generator. Runs `codex exec` in a read-only sandbox from the workspace
# ABOUTME: checkout and returns the last message as the spec body (or a needs-decision block).

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..prompt import SpecPromptInput, build_spec_prompt
from .base import SpecGenerationInput, SpecGenerationOutput
from .parse import decode_generator_output


@dataclass
class CodexGenerator:
    name: str = "codex"
    model: str | None = None

    def generate(self, data: SpecGenerationInput) -> SpecGenerationOutput:
        model = self.model or os.environ.get("SPEC_AGENT_MODEL") or "gpt-5-codex"
        system, user = build_spec_prompt(
            SpecPromptInput(
                work_item=data.work_item,
                product_id=data.product_id,
                intent=data.intent,
                policy_profile=data.policy_profile,
                repo_facts=data.repo_facts,
            )
        )
        prompt = f"{system}\n\n{user}"

        with tempfile.TemporaryDirectory(prefix="spec-design-agent-") as tmp:
            output_file = Path(tmp) / "last-message.txt"
            args = [
                "codex", "exec", "--ephemeral",
                "--sandbox", "read-only",
                "--model", model,
                "--output-last-message", str(output_file),
                "-C", data.repo_root,
                prompt,
            ]
            try:
                subprocess.run(
                    args,
                    cwd=data.repo_root,
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("SPEC_AGENT_PROVIDER=codex requires the Codex CLI on PATH") from exc
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"codex exec exited {exc.returncode}: {(exc.stderr or '')[-2000:]}") from exc
            return decode_generator_output(output_file.read_text(encoding="utf-8"), "codex", model)
