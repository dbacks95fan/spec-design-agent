from conftest import canonical_intent

from spec_design_agent.generators.base import SpecGenerationInput
from spec_design_agent.generators.mock import MockGenerator
from spec_design_agent.intent import parse_intent
from spec_design_agent.repo_inspect import RepoFacts
from spec_design_agent.spec import SpecFrontmatter, assemble_spec, validate_spec

FM = SpecFrontmatter(
    work_item="INT-MF-0042",
    product_id="MF",
    intent_commit="a" * 40,
    frozen_artifact_sha256="b" * 64,
    intent_content_sha256="e" * 64,
    base_commit="c" * 40,
    spec_version=1,
)


def _gen_input():
    return SpecGenerationInput(
        work_item="INT-MF-0042",
        product_id="MF",
        intent=parse_intent(canonical_intent()),
        repo_facts=RepoFacts(),
        repo_root=".",
    )


def test_assemble_spec_prepends_authoritative_frontmatter():
    md = assemble_spec("## Intent fidelity\n\nok", FM)
    assert md.startswith("---\n")
    assert "frozen_artifact_sha256: " + "b" * 64 in md
    assert "intent_content_sha256: " + "e" * 64 in md
    assert "status: draft" in md


def test_mock_generated_spec_passes_structural_validation():
    body = MockGenerator().generate(_gen_input()).spec_body
    result = validate_spec(assemble_spec(body, FM))
    assert result.missing_sections == []
    assert result.ok is True


def test_flags_missing_required_section():
    body = MockGenerator(omit_sections={"Validation strategy"}).generate(_gen_input()).spec_body
    result = validate_spec(assemble_spec(body, FM))
    assert result.missing_sections == ["Validation strategy"]
    assert result.ok is False


def test_flags_unresolved_todo_marker():
    md = assemble_spec("## Intent fidelity\n\nTODO decide scope", FM)
    assert "Intent fidelity" in validate_spec(md).unresolved_markers


def test_flags_not_relevant_without_rationale():
    sections = [
        "Intent fidelity",
        "Confirmed repository context",
        "User and system-observable outcomes",
        "Functional requirements and acceptance criteria",
        "Non-functional requirements",
        "Design and affected boundaries",
        "Data, security, privacy, and compliance considerations",
        "Error handling and operational behavior",
        "Validation strategy",
        "Dependencies, assumptions, and non-goals",
        "Risks and unresolved decisions",
        "Traceability to frozen intent",
    ]
    body = "\n\n".join(
        f"## {s}\n\n{'Not relevant.' if s == 'Non-functional requirements' else 'content with AC-1 observable'}"
        for s in sections
    )
    result = validate_spec(assemble_spec(body, FM))
    assert result.not_relevant_without_rationale == ["Non-functional requirements"]
    assert result.ok is False
