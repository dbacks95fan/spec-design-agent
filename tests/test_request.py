import pytest
from conftest import valid_request

from spec_design_agent.request import SUPPORTED_REQUEST_VERSION, parse_request
from spec_design_agent.types import PreconditionError, RequestValidationError


def test_accepts_a_well_formed_request():
    assert parse_request(valid_request()).work_item == "INT-MF-0042"


def test_rejects_missing_required_fields():
    bad = valid_request()
    del bad["approval"]
    with pytest.raises(RequestValidationError):
        parse_request(bad)


def test_rejects_malformed_commit_sha():
    bad = valid_request()
    bad["intent"]["commit"] = "not-a-sha"
    with pytest.raises(RequestValidationError):
        parse_request(bad)


def test_blocks_unsupported_request_version():
    bad = valid_request(requestVersion=SUPPORTED_REQUEST_VERSION + 1)
    with pytest.raises(PreconditionError) as exc:
        parse_request(bad)
    assert exc.value.code == "UNSUPPORTED_REQUEST_VERSION"


def test_blocks_when_approval_absent():
    bad = valid_request()
    bad["approval"]["readyForPlanning"] = False
    with pytest.raises(PreconditionError) as exc:
        parse_request(bad)
    assert exc.value.code == "APPROVAL_MISSING"


def test_blocks_branch_that_does_not_name_work_item():
    bad = valid_request()
    bad["target"]["branch"] = "work/INT-XX-0001"
    with pytest.raises(PreconditionError) as exc:
        parse_request(bad)
    assert exc.value.code == "BRANCH_MISMATCH"


def test_blocks_intent_path_that_does_not_reference_work_item():
    bad = valid_request()
    bad["intent"]["path"] = "products/mealflow/intents/other/intent.md"
    with pytest.raises(PreconditionError) as exc:
        parse_request(bad)
    assert exc.value.code == "INTENT_PATH_MISMATCH"
