# ABOUTME: Claude generator. Runs the Claude Agent SDK with read-only tools over the workspace
# ABOUTME: checkout and returns the spec body (or a needs-decision block) as text.

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from ..prompt import SpecPromptInput, build_spec_prompt
from .base import SpecGenerationInput, SpecGenerationOutput, TokenUsage
from .parse import decode_generator_output

_READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]
_DISALLOWED_TOOLS = ["Write", "Edit", "NotebookEdit", "Bash", "WebFetch", "WebSearch"]
DEFAULT_MODEL = "claude-opus-5"


def _usage_from_result(message: object) -> TokenUsage | None:
    """Reads the SDK ResultMessage's usage totals. Field names follow the API's
    usage block; anything absent counts as zero rather than failing the run."""
    raw = getattr(message, "usage", None)
    cost = getattr(message, "total_cost_usd", None)
    turns = getattr(message, "num_turns", 0)
    if not isinstance(raw, dict) and cost is None:
        return None
    usage = raw if isinstance(raw, dict) else {}

    def count(*names: str) -> int:
        for name in names:
            value = usage.get(name)
            if isinstance(value, (int, float)):
                return int(value)
        return 0

    return TokenUsage(
        input_tokens=count("input_tokens", "inputTokens"),
        output_tokens=count("output_tokens", "outputTokens"),
        cache_read_tokens=count("cache_read_input_tokens", "cacheReadInputTokens"),
        cache_creation_tokens=count("cache_creation_input_tokens", "cacheCreationInputTokens"),
        turns=int(turns) if isinstance(turns, (int, float)) else 0,
        cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
    )


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

        model = self.model or os.environ.get("SPEC_AGENT_MODEL") or DEFAULT_MODEL
        system, user = build_spec_prompt(
            SpecPromptInput(
                work_item=data.work_item,
                product_id=data.product_id,
                intent=data.intent,
                policy_profile=data.policy_profile,
                repo_facts=data.repo_facts,
            )
        )

        async def _run() -> tuple[str, TokenUsage | None]:
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
            usage: TokenUsage | None = None
            async for message in query(prompt=user, options=options):
                result = getattr(message, "result", None)
                if isinstance(result, str) and result:
                    final_text = result
                    usage = _usage_from_result(message)
                if data.cancel is not None and data.cancel.is_set():
                    raise RuntimeError("generation cancelled by caller")
            return final_text, usage

        final_text, usage = asyncio.run(_run())
        if not final_text:
            raise RuntimeError("Claude generator returned no final message")
        return decode_generator_output(final_text, "claude", model, usage)
