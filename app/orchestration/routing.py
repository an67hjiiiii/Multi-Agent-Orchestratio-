"""Runtime worker-profile routing over the existing domain registry."""

from __future__ import annotations

from app.research.registry import profile


def worker_profile(domain: str) -> dict:
    """Resolve the existing runtime worker assignment for a validated domain."""

    return profile(domain)


__all__ = ["worker_profile"]
