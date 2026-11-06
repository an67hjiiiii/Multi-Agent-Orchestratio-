import asyncio
import json

import pytest

from app.core.types import ProviderResult
from app.research.obligation_concern_extraction import (
    build_extraction_prompt,
    extract_obligations_and_concerns,
)


class ConcernProvider:
    def __init__(self, concerns):
        self.payload = {"obligations": [], "concerns": concerns}
        self.calls = 0

    async def generate_structured(self, **kwargs):
        self.calls += 1
        return ProviderResult(text=json.dumps(self.payload))


@pytest.mark.parametrize(
    "subject,domain",
    [
        ("Architecture review", "api_architecture"),
        ("API endpoint response contract", "api_architecture"),
        ("Database design", "database"),
        ("SQL transaction consistency", "database"),
        ("Security design", "security"),
        ("Authentication and permissions", "security"),
    ],
)
def test_unambiguous_subject_keeps_its_canonical_domain(subject, domain):
    concerns = [{"concern_id": "C1", "description": subject, "domain": domain}]
    result = asyncio.run(extract_obligations_and_concerns(ConcernProvider(concerns), f"Review {subject}."))
    assert result.to_dict()["concerns"] == concerns


def test_mixed_request_preserves_each_subject_domain_and_process_obligations():
    concerns = [
        {"concern_id": "C1", "description": "Architecture review", "domain": "api_architecture"},
        {"concern_id": "C2", "description": "Database review", "domain": "database"},
        {"concern_id": "C3", "description": "Security design review", "domain": "security"},
    ]
    provider = ConcernProvider(concerns)
    provider.payload["obligations"] = [
        {"obligation_id": "O1", "description": "Determine dependencies", "required": True},
        {"obligation_id": "O2", "description": "Produce a validated plan", "required": True},
    ]
    result = asyncio.run(extract_obligations_and_concerns(
        provider, "Review architecture, database and security design; determine dependencies and produce a validated plan."
    ))
    assert result.to_dict() == provider.payload


def test_architecture_mislabeled_security_fails_before_planner_without_remapping():
    provider = ConcernProvider([
        {"concern_id": "C1", "description": "Architecture review", "domain": "security"}
    ])
    with pytest.raises(ValueError, match="C1.*expected api_architecture.*received security"):
        asyncio.run(extract_obligations_and_concerns(provider, "Review architecture, database and security design."))
    assert provider.calls == 1
    assert provider.payload["concerns"][0]["domain"] == "security"


@pytest.mark.parametrize("domain", ["security", "api_architecture"])
def test_cross_domain_concern_is_not_arbitrarily_remapped(domain):
    concerns = [{"concern_id": "C1", "description": "API authorization boundary", "domain": domain}]
    result = asyncio.run(extract_obligations_and_concerns(
        ConcernProvider(concerns), "Review API authorization boundary."
    ))
    assert result.to_dict()["concerns"] == concerns


def test_unclassified_subject_is_not_invented_or_remapped():
    concerns = [{"concern_id": "C1", "description": "Operational resilience", "domain": "api_architecture"}]
    result = asyncio.run(extract_obligations_and_concerns(ConcernProvider(concerns), "Review operational resilience."))
    assert result.to_dict()["concerns"] == concerns


def test_prompt_exposes_registry_scopes_for_request_domains():
    from app.research.registry import REGISTRY

    prompt = build_extraction_prompt("Review architecture and database design.")
    assert "SUBJECT-DOMAIN GUIDANCE" in prompt
    for domain in ("database", "api_architecture"):
        assert f"{domain}: {REGISTRY[domain]['scope']}" in prompt
    assert "security: " not in prompt
