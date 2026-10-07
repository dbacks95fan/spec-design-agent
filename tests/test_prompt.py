from conftest import canonical_intent

from spec_design_agent.prompt import SPEC_SECTIONS, SYSTEM_RULES, SpecPromptInput, build_spec_prompt
from spec_design_agent.intent import parse_intent
from spec_design_agent.repo_inspect import InstructionFile, RepoFacts

FACTS = RepoFacts(
    instruction_files=[InstructionFile(path="CLAUDE.md", excerpt="use Python", truncated=False)],
    language_histogram={".py": 12, ".md": 3},
    test_signals=["python: pytest"],
    top_level_entries=["src/", "pyproject.toml"],
    files_scanned=15,
    limit_hit=None,
)


def _input():
    return SpecPromptInput(
        work_item="INT-MF-0042", product_id="MF", intent=parse_intent(canonical_intent()),
        policy_profile="Profile ID: MEALFLOW-DEFAULT\nVersion: 1\n", repo_facts=FACTS
    )


def test_prompt_embeds_verbatim_intent_and_all_sections():
    system, user = build_spec_prompt(_input())
    assert system == SYSTEM_RULES
    assert "Weekly meal plan export" in user
    assert "=== END FROZEN INTENT ===" in user
    assert "=== FROZEN POLICY & COMPLIANCE PROFILE" in user
    assert "Profile ID: MEALFLOW-DEFAULT" in user
    for section in SPEC_SECTIONS:
        assert f"## {section}" in user


def test_prompt_carries_repo_facts_and_needs_decision_hatch():
    _system, user = build_spec_prompt(_input())
    assert "use Python" in user
    assert ".py=12" in user
    assert '"needsDecision"' in user
