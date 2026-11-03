import pytest

from app.research.registry import profile


@pytest.mark.parametrize("domain", ["security", "database", "api_architecture"])
def test_known_task_domains_have_profiles(domain):
    assert profile(domain)


def test_unknown_task_domain_does_not_fallback_to_api_profile():
    with pytest.raises(ValueError, match="Unknown task domain: billing"):
        profile("billing")
