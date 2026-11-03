from __future__ import annotations

REGISTRY = {
    "security": {
        "name": "Security Analyst",
        "capabilities": ["authentication", "authorization", "JWT", "security review"],
        "scope": "Security requirements and access-control concerns",
        "exclusions": ["SQL tuning", "API response design unless security-related"],
    },
    "database": {
        "name": "Database Analyst",
        "capabilities": ["schema", "query", "transaction", "data consistency"],
        "scope": "Database and data-access concerns",
        "exclusions": ["authentication policy", "general UI review"],
    },
    "api_architecture": {
        "name": "API/Architecture Analyst",
        "capabilities": ["API", "endpoint", "architecture", "integration"],
        "scope": "API and system-architecture concerns",
        "exclusions": ["deep database tuning", "security policy ownership"],
    },
}


def validate_domain(domain: str) -> None:
    if domain not in REGISTRY:
        raise ValueError(f"Unknown task domain: {domain}")


def profile(domain: str) -> dict:
    validate_domain(domain)
    return REGISTRY[domain]
