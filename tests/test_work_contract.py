from conftest import PROFILE_TEXT, canonical_intent, valid_request

from spec_design_agent.intent import parse_intent
from spec_design_agent.policy_profile import parse_policy_profile
from spec_design_agent.schema import validate
from spec_design_agent.types import PreconditionError, SpecRequest
from spec_design_agent.work_contract import build_work_contract, render_work_contract

CHECKS = [{"name": "build", "command": "npm run build"}, {"name": "automated_tests", "command": "npm run test:server"}]


def test_builds_v3_contract_from_verified_freeze_intent_profile_and_trusted_checks():
    request = SpecRequest.from_dict(valid_request())
    intent = parse_intent(canonical_intent())
    profile = parse_policy_profile(PROFILE_TEXT, request)

    contract = build_work_contract(request, intent, profile, CHECKS)

    assert contract["schema_version"] == 3
    assert contract["work_item"]["intent_version"] == 5
    assert contract["intent"]["sha256"] == request.intent.frozen_artifact_sha256
    assert contract["policy_profile"]["sha256"] == request.policy_profile.frozen_artifact_sha256
    assert contract["policy_controls"][0]["control_id"] == "SEC-BASE-001"
    assert contract["required_validation"] == CHECKS
    assert contract["required_validation"] is not CHECKS
    assert validate("work-contract.schema.json", contract) == []
    assert "schema_version: 3" in render_work_contract(contract)


def test_missing_acceptance_criteria_requires_a_human_decision():
    request = SpecRequest.from_dict(valid_request())
    intent = parse_intent(canonical_intent().replace("## Acceptance criteria\n\n- A logged-in household can download the current week's plan as CSV.\n- The CSV lists one row per planned meal with date, meal slot, and recipe name.\n", "## Acceptance criteria\n\n- none\n"))
    profile = parse_policy_profile(PROFILE_TEXT, request)
    try:
        build_work_contract(request, intent, profile, CHECKS)
        assert False, "expected a human decision"
    except PreconditionError as error:
        assert error.status == "needs_decision"
        assert error.code == "ACCEPTANCE_CRITERIA_MISSING"


def test_policy_profile_identity_must_match_freeze_record():
    request = SpecRequest.from_dict(valid_request())
    wrong_profile = PROFILE_TEXT.replace("MF-DEFAULT", "OTHER")
    try:
        parse_policy_profile(wrong_profile, request)
        assert False, "expected an identity mismatch"
    except PreconditionError as error:
        assert error.code == "POLICY_PROFILE_IDENTITY_MISMATCH"
