import pytest
from conftest import FORTY_HEX, canonical_intent, sha256, valid_request, write_exact

from spec_design_agent.integrity import sha256_file, sha256_text, verify_frozen_intent
from spec_design_agent.intent import parse_intent
from spec_design_agent.types import PreconditionError, SpecRequest


def _request_for(intent_text: str) -> SpecRequest:
    return SpecRequest.from_dict(
        valid_request(
            intent={
                "repository": "dbacks95fan/intent-backlog",
                "commit": FORTY_HEX,
                "path": "products/mealflow/intents/INT-MF-0042/intent.md",
                "frozenArtifactSha256": sha256(intent_text),
                "contentSha256": sha256("canonical:" + intent_text),
            }
        )
    )


def test_sha256_file_matches_sha256_text(tmp_path):
    path = tmp_path / "intent.md"
    text = canonical_intent()
    write_exact(path, text)
    assert sha256_file(path) == sha256_text(text)


def test_accepts_matching_bytes_and_identity():
    text = canonical_intent()
    verify_frozen_intent(_request_for(text), parse_intent(text), sha256_text(text))


def test_blocks_intent_mutated_on_hash_difference():
    text = canonical_intent()
    with pytest.raises(PreconditionError) as exc:
        verify_frozen_intent(_request_for(text), parse_intent(text), sha256_text(text + " "))
    assert exc.value.code == "INTENT_MUTATED" and exc.value.status == "blocked"


def test_blocks_identity_mismatch():
    text = canonical_intent(intent_id="INT-MF-9999")
    with pytest.raises(PreconditionError) as exc:
        verify_frozen_intent(_request_for(text), parse_intent(text), sha256_text(text))
    assert exc.value.code == "INTENT_IDENTITY_MISMATCH"


def test_admits_any_lifecycle_status():
    # The freeze protocol is still documented in agentic-sdlc/docs, but a run is
    # admitted on identity and byte integrity alone — not on lifecycle state.
    for status in ("New Ideas", "Refining", "Accepted", "Frozen"):
        text = canonical_intent(status=status)
        verify_frozen_intent(_request_for(text), parse_intent(text), sha256_text(text))


def test_relaxing_the_status_gate_does_not_relax_integrity():
    text = canonical_intent(status="New Ideas")
    with pytest.raises(PreconditionError) as exc:
        verify_frozen_intent(_request_for(text), parse_intent(text), "f" * 64)
    assert exc.value.code == "INTENT_MUTATED"


def test_open_decisions_return_needs_decision():
    text = canonical_intent(open_decisions=["Delimiter?"])
    with pytest.raises(PreconditionError) as exc:
        verify_frozen_intent(_request_for(text), parse_intent(text), sha256_text(text))
    assert exc.value.code == "INTENT_OPEN_DECISIONS" and exc.value.status == "needs_decision"
