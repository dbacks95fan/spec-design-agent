# ABOUTME: Claude generator. Runs the Claude Agent SDK with read-only tools over the workspace
# ABOUTME: checkout and returns the spec body (or a needs-decision block) as text.

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from ..prompt import SpecPromptInput, build_spec_prompt
from .base import SpecGenerationInput, SpecGenerationOutput
from .parse import decode_generator_output

_READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]
_DISALLOWED_TOOLS = ["Write", "Edit", "NotebookEdit", "Bash", "WebFetch", "WebSearch"]


@dataclass
class ClaudeGenerator:
    name: str = "claude"
    model: str | None = None
    max_turns: int = 30

    def generate(self, data: SpecGenerationInput) -> SpecGenerationOutput:
        try:
            from claude_agent_sdk import ClaudeAgentOptions, query  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise RuntimeError(
                "SPEC_AGENT_PROVIDER=claude requires the optional 'claude-agent-sdk' dependency "
                "(install with: uv sync --extra claude)"
            ) from exc

        model = self.model or os.environ.get("SPEC_AGENT_MODEL") or "claude-sonnet-5"
        system, user = build_spec_prompt(
            SpecPromptInput(
                work_item=data.work_item,
                product_id=data.product_id,
                intent=data.intent,
                repo_facts=data.repo_facts,
            )
        )

        async def _run() -> str:
            options = ClaudeAgentOptions(
                cwd=data.repo_root,
                model=model,
                system_prompt=system,
                allowed_tools=_READ_ONLY_TOOLS,
                disallowed_tools=_DISALLOWED_TOOLS,
                permission_mode="default",
                max_turns=self.max_turns,
                setting_sources=[],
            )
            final_text = ""
            async for message in query(prompt=user, options=options):
                result = getattr(message, "result", None)
                if isinstance(result, str) and result:
                    final_text = result
                if data.cancel is not None and data.cancel.is_set():
                    raise RuntimeError("generation cancelled by caller")
            return final_text

        final_text = asyncio.run(_run())
        if not final_text:
            raise RuntimeError("Claude generator returned no final message")
        return decode_generator_output(final_text, "claude", model)
