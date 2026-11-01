# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Codex generator. Calls the OpenAI Responses API with OPENAI_API_KEY, letting the model read
# ABOUTME: the workspace checkout through read-only tools, and returns the spec body or a needs-decision block.

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from ..prompt import SpecPromptInput, build_spec_prompt
from .base import SpecGenerationInput, SpecGenerationOutput, TokenUsage
from .parse import decode_generator_output
from .repo_tools import TOOL_DEFINITIONS, run_tool

DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_API_URL = "https://api.openai.com/v1/responses"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

Transport = Callable[[dict[str, object]], dict[str, object]]


def _http_transport(
    api_key: str,
    api_url: str,
    request_timeout_s: float,
    attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> Transport:
    """POSTs one Responses request, retrying rate limits and server errors with backoff."""

    def send(body: dict[str, object]) -> dict[str, object]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(
                api_url,
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(
                    request, timeout=request_timeout_s
                ) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code in _RETRYABLE_STATUS and attempt < attempts:
                    sleep(2**attempt)
                    continue
                raise RuntimeError(
                    f"OpenAI API returned HTTP {exc.code}: {_error_detail(exc)}"
                ) from None
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < attempts:
                    sleep(2**attempt)
                    continue
                raise RuntimeError(f"OpenAI API could not be reached: {exc}") from None
        raise AssertionError("unreachable")

    return send


def _error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(exc.read().decode("utf-8"))
        message = body.get("error", {}).get("message")
        if isinstance(message, str):
            return message[:500]
    except (ValueError, AttributeError, OSError):
        pass
    return exc.reason if isinstance(exc.reason, str) else "no detail"


def _count(source: object, *path: str) -> int:
    value = source
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return int(value) if isinstance(value, (int, float)) else 0


@dataclass
class _UsageTally:
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    turns: int = 0

    def add(self, usage: object) -> None:
        self.input_tokens += _count(usage, "input_tokens")
        self.cached_tokens += _count(usage, "input_tokens_details", "cached_tokens")
        self.output_tokens += _count(usage, "output_tokens")
        self.turns += 1

    def to_usage(self) -> TokenUsage:
        # The API counts cached tokens inside input_tokens; split them so totals are not doubled.
        return TokenUsage(
            input_tokens=self.input_tokens - self.cached_tokens,
            output_tokens=self.output_tokens,
            cache_read_tokens=self.cached_tokens,
            turns=self.turns,
        )


def _output_text(output: list[object]) -> str:
    parts: list[str] = []
    for item in output:
        if isinstance(item, dict) and item.get("type") == "message":
            for content in item.get("content") or []:
                if isinstance(content, dict) and content.get("type") == "output_text":
                    parts.append(str(content.get("text", "")))
                elif isinstance(content, dict) and content.get("type") == "refusal":
                    raise RuntimeError(
                        f"OpenAI model refused: {str(content.get('refusal', ''))[:500]}"
                    )
    return "".join(parts)


@dataclass
class CodexGenerator:
    name: str = "codex"
    model: str | None = None
    max_turns: int = 30
    request_timeout_s: float = 300.0
    # Tests inject a fake; production builds the HTTP transport from OPENAI_API_KEY.
    transport: Transport | None = field(default=None, repr=False)

    def generate(self, data: SpecGenerationInput) -> SpecGenerationOutput:
        model = self.model or os.environ.get("SPEC_AGENT_MODEL") or DEFAULT_MODEL
        send = self.transport or self._default_transport()
        system, user = build_spec_prompt(
            SpecPromptInput(
                work_item=data.work_item,
                product_id=data.product_id,
                intent=data.intent,
                policy_profile=data.policy_profile,
                repo_facts=data.repo_facts,
            )
        )
        effort = os.environ.get("SPEC_AGENT_REASONING_EFFORT") or None
        # Stateless: nothing is stored at OpenAI, so each request carries the whole exchange,
        # including encrypted reasoning items the model needs between tool calls.
        conversation: list[object] = [{"role": "user", "content": user}]
        tally = _UsageTally()
        for _ in range(self.max_turns):
            if data.cancel is not None and data.cancel.is_set():
                raise RuntimeError("generation cancelled by caller")
            body: dict[str, object] = {
                "model": model,
                "instructions": system,
                "input": conversation,
                "tools": TOOL_DEFINITIONS,
                "store": False,
                "include": ["reasoning.encrypted_content"],
            }
            if effort:
                body["reasoning"] = {"effort": effort}
            response = send(body)
            tally.add(response.get("usage"))
            status = response.get("status")
            if status != "completed":
                detail = (
                    response.get("incomplete_details")
                    or response.get("error")
                    or "no detail"
                )
                raise RuntimeError(f"OpenAI response was {status!r}: {detail}")
            output = response.get("output")
            if not isinstance(output, list):
                raise TypeError("OpenAI response had no output list")
            conversation.extend(output)
            calls = [
                item
                for item in output
                if isinstance(item, dict) and item.get("type") == "function_call"
            ]
            if not calls:
                text = _output_text(output)
                if not text.strip():
                    raise RuntimeError("Codex generator returned no final message")
                return decode_generator_output(text, "codex", model, tally.to_usage())
            for call in calls:
                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.get("call_id"),
                        "output": run_tool(
                            data.repo_root,
                            str(call.get("name")),
                            str(call.get("arguments") or ""),
                        ),
                    }
                )
        raise RuntimeError(
            f"Codex generator did not finish within {self.max_turns} turns"
        )

    def _default_transport(self) -> Transport:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("SPEC_AGENT_PROVIDER=codex requires OPENAI_API_KEY")
        return _http_transport(api_key, DEFAULT_API_URL, self.request_timeout_s)
