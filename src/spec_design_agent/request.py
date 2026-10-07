# ABOUTME: Parses and validates the Conductor work request before any artifact work begins.
# ABOUTME: Rejects incompatible request versions and missing approval rather than inferring intent.

from __future__ import annotations

from typing import Any

from .schema import validate
from .types import (
    SUPPORTED_REQUEST_VERSION,
    PreconditionError,
    RequestValidationError,
    SpecRequest,
)


def validate_request_shape(value: Any) -> SpecRequest:
    """Structural validation only. Raises RequestValidationError (a usage error) on a shape problem."""
    errors = validate("spec-request.schema.json", value)
    if errors:
        raise RequestValidationError(errors)
    return SpecRequest.from_dict(value)


def check_request_preconditions(request: SpecRequest) -> None:
    """Semantic preconditions the Conductor must satisfy. Raises PreconditionError."""
    if request.request_version != SUPPORTED_REQUEST_VERSION:
        raise PreconditionError(
            "blocked",
            "UNSUPPORTED_REQUEST_VERSION",
            f"Request version {request.request_version} is not supported; "
            f"this agent implements version {SUPPORTED_REQUEST_VERSION}",
        )
    if request.approval.prioritized is not True:
        raise PreconditionError(
            "blocked",
            "APPROVAL_MISSING",
            "A valid Prioritized freeze is not present on the request",
        )
    # Cross-field consistency: branch and frozen-intent path must both name this work
    # item, so a mis-routed request cannot start work.
    if not request.target.branch.endswith(request.work_item):
        raise PreconditionError(
            "blocked",
            "BRANCH_MISMATCH",
            f"Target branch '{request.target.branch}' does not name work item '{request.work_item}'",
        )
    if request.work_item not in request.intent.path:
        raise PreconditionError(
            "blocked",
            "INTENT_PATH_MISMATCH",
            f"Intent path '{request.intent.path}' does not reference work item '{request.work_item}'",
        )
    if request.policy_profile.repository != request.intent.repository or request.policy_profile.commit != request.intent.commit:
        raise PreconditionError(
            "blocked",
            "POLICY_PROFILE_SOURCE_MISMATCH",
            "Frozen intent and policy profile must come from the same pinned intent-backlog repository commit",
        )


def parse_request(value: Any) -> SpecRequest:
    """Shape + preconditions in one call (used by tests)."""
    request = validate_request_shape(value)
    check_request_preconditions(request)
    return request
