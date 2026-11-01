# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Tests the Codex generator's Responses API loop with a stand-in transport, and its HTTP
# ABOUTME: transport against a local server: tool calls, stateless replay, usage, failures, and retries.

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from conftest import PROFILE_TEXT, canonical_intent, valid_request

from spec_design_agent.generators.base import SpecGenerationInput
from spec_design_agent.generators.codex import (
    DEFAULT_MODEL,
    CodexGenerator,
    _http_transport,
)
from spec_design_agent.intent import parse_intent
from spec_design_agent.policy_profile import parse_policy_profile
from spec_design_agent.repo_inspect import RepoFacts
from spec_design_agent.types import SpecRequest

SPEC_JSON = json.dumps(
    {"specMarkdown": "## Intent fidelity\n\nThe weekly plan is saved."}
)


def _input(repo_root, cancel=None):
    return SpecGenerationInput(
        work_item="INT-MF-0042",
        product_id="MF",
        intent=parse_intent(canonical_intent()),
        policy_profile=parse_policy_profile(
            PROFILE_TEXT, SpecRequest.from_dict(valid_request())
        ),
        repo_facts=RepoFacts(top_level_entries=["src/"], files_scanned=1),
        repo_root=str(repo_root),
        cancel=cancel,
    )


def message(text):
    return {
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text}],
    }


def completed(*output, input_tokens=100, cached=0, output_tokens=20):
    return {
        "status": "completed",
        "output": list(output),
        "usage": {
            "input_tokens": input_tokens,
            "input_tokens_details": {"cached_tokens": cached},
            "output_tokens": output_tokens,
        },
    }


class Scripted:
    """A stand-in transport that replays canned responses and records every request body."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, body):
        # Deep copy, since the generator keeps appending to the same conversation list.
        self.requests.append(json.loads(json.dumps(body)))
        return self.responses.pop(0)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "planner.py").write_bytes(b"WEEK = 7\n")
    return tmp_path


def test_reads_the_repository_through_tools_then_returns_the_spec(repo, monkeypatch):
    monkeypatch.delenv("SPEC_AGENT_MODEL", raising=False)
    monkeypatch.setenv("SPEC_AGENT_REASONING_EFFORT", "high")
    reasoning = {
        "type": "reasoning",
        "id": "rs_1",
        "encrypted_content": "opaque",
        "summary": [],
    }
    call = {
        "type": "function_call",
        "call_id": "call_1",
        "name": "read_file",
        "arguments": json.dumps({"path": "src/planner.py", "offset": None}),
    }
    transport = Scripted(
        completed(reasoning, call, input_tokens=1000, cached=0, output_tokens=50),
        completed(message(SPEC_JSON), input_tokens=1200, cached=900, output_tokens=400),
    )

    out = CodexGenerator(transport=transport).generate(_input(repo))

    assert out.spec_body == "## Intent fidelity\n\nThe weekly plan is saved."
    assert (out.model_provider, out.model) == ("codex", DEFAULT_MODEL)
    first, second = transport.requests
    for body in (first, second):
        assert body["store"] is False
        assert body["include"] == ["reasoning.encrypted_content"]
        assert body["reasoning"] == {"effort": "high"}
        assert [t["name"] for t in body["tools"]] == [
            "list_directory",
            "read_file",
            "search_files",
        ]
        assert "Spec & Design Agent" in body["instructions"]
    assert (
        first["input"][0]["role"] == "user"
        and "INT-MF-0042" in first["input"][0]["content"]
    )
    # The reasoning item and the call are replayed, followed by the tool's result.
    assert second["input"][1:] == [
        reasoning,
        call,
        {"type": "function_call_output", "call_id": "call_1", "output": "WEEK = 7\n"},
    ]
    assert out.usage.input_tokens == 1300
    assert out.usage.cache_read_tokens == 900
    assert out.usage.output_tokens == 450
    assert out.usage.turns == 2
    assert out.usage.cost_usd is None


def test_a_needs_decision_answer_routes_as_a_decision(repo):
    decision = '```json\n{"needsDecision":[{"question":"Which week start?","impact":"data","minimumAuthority":"product owner"}]}\n```'
    out = CodexGenerator(transport=Scripted(completed(message(decision)))).generate(
        _input(repo)
    )
    assert out.spec_body == ""
    assert out.human_decisions[0].question == "Which week start?"


def test_model_comes_from_the_environment_when_set(repo, monkeypatch):
    monkeypatch.setenv("SPEC_AGENT_MODEL", "gpt-6-sol")
    transport = Scripted(completed(message(SPEC_JSON)))
    assert (
        CodexGenerator(transport=transport).generate(_input(repo)).model == "gpt-6-sol"
    )
    assert transport.requests[0]["model"] == "gpt-6-sol"
    assert "reasoning" not in transport.requests[0]


def test_requires_an_api_key_without_calling_anything(repo, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="requires OPENAI_API_KEY"):
        CodexGenerator().generate(_input(repo))


@pytest.mark.parametrize(
    ("response", "message_pattern"),
    [
        (
            {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [],
            },
            "max_output_tokens",
        ),
        (
            {"status": "failed", "error": {"code": "server_error"}, "output": []},
            "server_error",
        ),
        (
            completed(
                {"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}
            ),
            "refused",
        ),
        (completed(message("   ")), "no final message"),
        (completed(message("not json")), "must be a JSON object"),
    ],
)
def test_unusable_responses_fail_the_generation(repo, response, message_pattern):
    with pytest.raises((RuntimeError, ValueError), match=message_pattern):
        CodexGenerator(transport=Scripted(response)).generate(_input(repo))


def test_stops_after_the_turn_limit(repo):
    call = {
        "type": "function_call",
        "call_id": "c",
        "name": "list_directory",
        "arguments": '{"path": "."}',
    }
    transport = Scripted(*[completed(call) for _ in range(3)])
    with pytest.raises(RuntimeError, match="within 3 turns"):
        CodexGenerator(max_turns=3, transport=transport).generate(_input(repo))
    assert len(transport.requests) == 3


def test_a_cancelled_generation_makes_no_further_requests(repo):
    cancel = threading.Event()
    cancel.set()
    transport = Scripted()
    with pytest.raises(RuntimeError, match="cancelled"):
        CodexGenerator(transport=transport).generate(_input(repo, cancel=cancel))
    assert transport.requests == []


class _Server:
    """A local HTTP server answering with a scripted list of (status, body) pairs."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                server.seen.append(
                    (dict(self.headers), json.loads(self.rfile.read(length)))
                )
                status, body = server.replies.pop(0)
                payload = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/v1/responses"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def test_http_transport_sends_the_bearer_key_and_retries_a_server_error():
    server = _Server(
        [
            (503, {"error": {"message": "overloaded"}}),
            (200, {"status": "completed", "output": []}),
        ]
    )
    waits = []
    try:
        send = _http_transport("sk-test-key-123", server.url, 5, sleep=waits.append)
        assert send({"model": "m"}) == {"status": "completed", "output": []}
    finally:
        server.close()
    assert waits == [2]
    assert len(server.seen) == 2
    headers, body = server.seen[1]
    assert headers["Authorization"] == "Bearer sk-test-key-123"
    assert body == {"model": "m"}


def test_http_transport_reports_a_rejected_key_without_echoing_it():
    server = _Server([(401, {"error": {"message": "Incorrect API key provided."}})])
    try:
        send = _http_transport("sk-test-key-123", server.url, 5, sleep=lambda _: None)
        with pytest.raises(RuntimeError) as raised:
            send({"model": "m"})
    finally:
        server.close()
    assert (
        str(raised.value) == "OpenAI API returned HTTP 401: Incorrect API key provided."
    )
    assert "sk-test-key-123" not in str(raised.value)
