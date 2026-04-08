"""Everywatch URL helpers (no live HTTP)."""

from types import SimpleNamespace

from watchfinder.services.everywatch_client import (
    candidate_model_urls,
    collect_everywatch_snapshot,
    guess_site_search_urls,
    guess_watch_listing_urls,
    is_everywatch_watch_detail_url,
    normalize_everywatch_watch_url,
    parse_price_container_rows,
    parse_watch_detail_hit,
    parse_watch_hits_from_html,
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
    assert "watch-listing" in g[0]


def test_guess_watch_listing_urls_keyword_tail() -> None:
    u = guess_watch_listing_urls("Omega 166.085")
    assert any("watch-listing" in x for x in u)
    assert any("keyword=166085" in x for x in u)


def test_parse_watch_hits_relative_href() -> None:
    html = '<html><body><a href="/omega/de-ville/watch-999">Omega De Ville 166.085 36mm</a></body></html>'
    hits = parse_watch_hits_from_html(html, page_url="https://everywatch.com/watch-listing?q=1")
    assert len(hits) == 1
    assert hits[0]["url"].endswith("/watch-999")
    assert "166.085" in hits[0]["label"]


def test_parse_price_container_gbp_k() -> None:
    html = """<html><body><div class="price-container">
    <h3 class="price-analysis-item"><span class="p-title">Dealers Range</span>
    <span class="price"><div><a>408 </a> - </div><div><a>1.48K GBP</a></div></span></h3>
    </div></body></html>"""
    rows = parse_price_container_rows(html)
    assert rows and rows[0].get("gbp_amounts")
    assert any(float(x) >= 1400 for x in rows[0]["gbp_amounts"])


def test_normalize_everywatch_watch_url() -> None:
    assert (
        normalize_everywatch_watch_url("https://everywatch.com/omega/watch-2364326")
        == "https://everywatch.com/omega/watch-2364326"
    )
    assert normalize_everywatch_watch_url(
        "https://everywatch.com/omega/watch-2364326?ref=1"
    ) == "https://everywatch.com/omega/watch-2364326"
    assert normalize_everywatch_watch_url("https://watchbase.com/x") is None
    assert normalize_everywatch_watch_url("https://everywatch.com/omega/seamaster") is None


def test_is_everywatch_watch_detail_url() -> None:
    assert is_everywatch_watch_detail_url("https://everywatch.com/omega/watch-2364326")
    assert not is_everywatch_watch_detail_url("https://everywatch.com/omega/21030422003001")


def test_parse_watch_detail_hit_from_title() -> None:
    html = "<html><head><title>Omega · 1,234 USD</title></head><body><h1>Omega Vintage</h1></body></html>"
    h = parse_watch_detail_hit(html, page_url="https://everywatch.com/omega/watch-9")
    assert h and h["url"].endswith("/watch-9")
    assert h["amount"] == "1234"
    assert h["currency"] == "USD"


def test_parse_watch_detail_hit_ld_json() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Product","offers":{"price":"999","priceCurrency":"EUR"}}'
        "</script><h1>X</h1>"
    )
    h = parse_watch_detail_hit(html, page_url="https://everywatch.com/x/watch-1")
    assert h["amount"] == "999"
    assert h["currency"] == "EUR"


def test_collect_everywatch_snapshot_uses_saved_url_without_brand_guess(monkeypatch) -> None:
    called: list[str] = []

    def fake_fetch(url: str, settings=None, timeout=28.0, extra_headers=None):
        called.append(url)
        if "watch-99" in url:
            return (
                '<html><head><title>T 5,000 GBP</title></head><body><h1>T</h1></body></html>',
                None,
                200,
            )
        return None, "404", 404

    monkeypatch.setattr(
        "watchfinder.services.everywatch_client.fetch_everywatch_page",
        fake_fetch,
    )
    snap = collect_everywatch_snapshot(
        "",
        None,
        None,
        settings=SimpleNamespace(watchbase_import_user_agent=None),
        everywatch_url="https://everywatch.com/omega/watch-99",
    )
    assert snap.get("error") is None
    assert snap.get("saved_watch_url_used") is True
    assert snap.get("page_kind") == "watch_detail"
    assert called and "watch-99" in called[0]
