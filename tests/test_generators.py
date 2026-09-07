import pytest
from conftest import canonical_intent

from spec_design_agent.generators import create_generator
from spec_design_agent.generators.base import SpecGenerationInput
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
