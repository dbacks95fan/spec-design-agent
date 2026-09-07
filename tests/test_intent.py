import pytest
from conftest import canonical_intent, sha256

from spec_design_agent.intent import parse_intent


def test_parses_frontmatter_identity_and_status():
    intent = parse_intent(canonical_intent())
    assert intent.intent_id == "INT-MF-0042"
    assert intent.product_id == "MF"
    assert intent.version == 5
    assert intent.status == "Frozen"


def test_hashes_the_exact_bytes():
    raw = canonical_intent()
    assert parse_intent(raw).sha256 == sha256(raw)


def test_extracts_acceptance_criteria_bullets():
    intent = parse_intent(canonical_intent())
    assert len(intent.acceptance_criteria) == 2
    assert "download the current week" in intent.acceptance_criteria[0]


def test_none_placeholder_means_no_open_decisions():
    assert parse_intent(canonical_intent()).open_decisions == []


def test_surfaces_real_open_decisions():
    intent = parse_intent(canonical_intent(open_decisions=["Which delimiter does finance require?"]))
    assert intent.open_decisions == ["Which delimiter does finance require?"]


def test_captures_named_sections_and_title():
    intent = parse_intent(canonical_intent())
    assert intent.sections["title"] == "Weekly meal plan export"
    assert "Non-goal: historical plans" in intent.sections["scope and non-goals"]


def test_raises_when_frontmatter_missing_identity():
    with pytest.raises(ValueError, match="intent_id"):
        parse_intent("# Intent: no frontmatter\n\n## Problem\n\nx\n")
