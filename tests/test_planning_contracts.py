from dataclasses import asdict

from app.core.types import Concern, Obligation


def test_obligation_and_concern_are_distinct_serializable_contracts():
    obligation = Obligation(
        obligation_id="REQ-1",
        description="Preserve the requested error-response requirement.",
    )
    concern = Concern(
        concern_id="CONCERN-1",
        description="Check that the error response is actionable.",
        domain="api_architecture",
    )

    assert asdict(obligation) == {
        "obligation_id": "REQ-1",
        "description": "Preserve the requested error-response requirement.",
        "required": True,
    }
    assert asdict(concern) == {
        "concern_id": "CONCERN-1",
        "description": "Check that the error response is actionable.",
        "domain": "api_architecture",
    }
