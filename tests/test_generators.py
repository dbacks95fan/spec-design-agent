import pytest
from conftest import canonical_intent

from spec_design_agent.generators import create_generator
from spec_design_agent.generators.base import SpecGenerationInput, TokenUsage
from spec_design_agent.generators.claude import DEFAULT_MODEL, ClaudeGenerator, _usage_from_result
from spec_design_agent.generators.mock import MockGenerator
from spec_design_agent.generators.parse import decode_generator_output
from spec_design_agent.intent import parse_intent
from spec_design_agent.prompt import SPEC_SECTIONS
from spec_design_agent.repo_inspect import RepoFacts
from spec_design_agent.types import HumanDecision

FACTS = RepoFacts(top_level_entries=["src/"], language_histogram={".py": 3}, files_scanned=3)


def _input():
    return SpecGenerationInput(
        work_item="INT-MF-0042",
        product_id="MF",
        intent=parse_intent(canonical_intent()),
        policy_profile="Profile ID: MEALFLOW-DEFAULT\nVersion: 1\n",
        repo_facts=FACTS,
        repo_root=".",
    )


def test_create_generator_selects_by_explicit_provider():
    assert create_generator(provider="mock").name == "mock"
    assert create_generator(provider="claude").name == "claude"
    assert create_generator(provider="codex").name == "codex"


def test_create_generator_honours_env(monkeypatch):
    monkeypatch.setenv("SPEC_AGENT_PROVIDER", "mock")
    assert create_generator().name == "mock"


def test_create_generator_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown SPEC_AGENT_PROVIDER"):
        create_generator(provider="gpt4all")


def test_mock_generator_emits_every_required_section():
    out = MockGenerator().generate(_input())
    for section in SPEC_SECTIONS:
        assert f"## {section}" in out.spec_body
    assert out.human_decisions == []
    assert out.model_provider == "mock"


def test_mock_generator_can_force_a_material_decision():
    out = MockGenerator(
        force_decisions=[HumanDecision(question="Which delimiter?", impact="data contract", minimum_authority="product owner")]
    ).generate(_input())
    assert out.spec_body == ""
    assert len(out.human_decisions) == 1


def test_decode_recognises_fenced_needs_decision_block():
    raw = 'preamble\n```json\n{"needsDecision":[{"question":"q","impact":"i","minimumAuthority":"product owner"}]}\n```'
    out = decode_generator_output(raw, "claude", "claude-sonnet-5")
    assert len(out.human_decisions) == 1
    assert out.spec_body == ""


def test_decode_strips_frontmatter_and_fences_from_spec_body():
    raw = "```markdown\n---\nwork_item: X\n---\n## Intent fidelity\n\ntext\n```"
    out = decode_generator_output(raw, "codex", "gpt-5-codex")
    assert out.human_decisions == []
    assert out.spec_body.startswith("## Intent fidelity")


def test_token_usage_totals_and_json_shape():
    usage = TokenUsage(
        input_tokens=1000, output_tokens=250, cache_read_tokens=40, cache_creation_tokens=10, turns=3, cost_usd=0.0412
    )
    assert usage.total_tokens == 1300
    assert usage.to_json() == {
        "inputTokens": 1000,
        "outputTokens": 250,
        "cacheReadTokens": 40,
        "cacheCreationTokens": 10,
        "totalTokens": 1300,
        "turns": 3,
        "costUsd": 0.0412,
    }


def test_token_usage_omits_cost_when_provider_does_not_report_it():
    assert "costUsd" not in TokenUsage(input_tokens=5, output_tokens=5).to_json()


class _FakeResultMessage:
    def __init__(self, usage, cost=None, turns=0):
        self.usage = usage
        self.total_cost_usd = cost
        self.num_turns = turns


def test_reads_usage_from_the_sdk_result_message():
    usage = _usage_from_result(
        _FakeResultMessage(
            {
                "input_tokens": 12000,
                "output_tokens": 3400,
                "cache_read_input_tokens": 800,
                "cache_creation_input_tokens": 200,
            },
            cost=0.1875,
            turns=4,
        )
    )
    assert usage is not None
    assert (usage.input_tokens, usage.output_tokens) == (12000, 3400)
    assert (usage.cache_read_tokens, usage.cache_creation_tokens) == (800, 200)
    assert usage.total_tokens == 16400
    assert usage.turns == 4
    assert usage.cost_usd == 0.1875


def test_missing_usage_fields_count_as_zero_rather_than_failing():
    usage = _usage_from_result(_FakeResultMessage({"input_tokens": 10}, cost=None, turns=1))
    assert usage is not None
    assert usage.output_tokens == 0
    assert usage.cost_usd is None


def test_no_usage_reported_yields_none():
    assert _usage_from_result(_FakeResultMessage(None)) is None


def test_claude_generator_defaults_to_opus(monkeypatch):
    monkeypatch.delenv("SPEC_AGENT_MODEL", raising=False)
    assert DEFAULT_MODEL == "claude-opus-5"
    assert ClaudeGenerator().model is None  # resolved at call time from DEFAULT_MODEL


def test_decode_generator_output_carries_usage_through():
    usage = TokenUsage(input_tokens=1, output_tokens=2)
    out = decode_generator_output("## Intent fidelity\n\nbody", "claude", "claude-opus-5", usage)
    assert out.usage is usage
    decision = decode_generator_output(
        '```json\n{"needsDecision":[{"question":"q","impact":"i","minimumAuthority":"a"}]}\n```',
        "claude",
        "claude-opus-5",
        usage,
    )
    assert decision.usage is usage
