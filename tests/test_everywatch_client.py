"""Everywatch URL helpers (no live HTTP)."""

from watchfinder.services.everywatch_client import (
    candidate_model_urls,
    guess_site_search_urls,
    reference_alnum,
    slugify_segment,
)


def test_slugify_segment() -> None:
    assert slugify_segment("Omega") == "omega"
    assert slugify_segment("A. Lange & Söhne").startswith("a-lange")


def test_reference_alnum() -> None:
    assert reference_alnum("210.30.42.20.03.001") == "21030422003001"


def test_candidate_model_urls_order() -> None:
    u = candidate_model_urls("Omega", "210.30.42.20.03.001", "Seamaster")
    assert u[0] == "https://everywatch.com/omega/21030422003001"
    assert "seamaster" in u[1]


def test_guess_site_search_urls_nonempty() -> None:
    g = guess_site_search_urls("Rolex Sub")
    assert len(g) >= 2
    assert all(x.startswith("https://everywatch.com") for x in g)
