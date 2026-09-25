from oge_hse_mcp import server
from oge_hse_mcp.seed_data import seed


def _seed(monkeypatch):
    monkeypatch.setenv("HSE_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    return seed()


def test_search_procedures_includes_global_and_authorized_site(monkeypatch):
    _seed(monkeypatch)

    result = server.search_procedures(site_ids=["DEMO-GULF"])

    assert [item["id"] for item in result["procedures"]] == ["HSE-PTW-014", "HSE-GEN-001"]


def test_get_procedure_blocks_cross_site_access(monkeypatch):
    _seed(monkeypatch)

    try:
        server.get_procedure("HSE-LOTO-007", site_ids=["DEMO-GULF"])
        assert False, "Expected cross-site access to be rejected"
    except ValueError as exc:
        assert "outside the authorized site scope" in str(exc)


def test_search_incidents_only_returns_authorized_sites(monkeypatch):
    counts = _seed(monkeypatch)

    result = server.search_incidents(query="blinded line", site_ids=["DEMO-PERMIAN"])

    assert counts == {"procedures": 3, "incidents": 200}
    assert [item["id"] for item in result["incidents"]] == ["INC-2026-0061"]
    assert result["returned_count"] == 1
    assert result["total_count"] == 1


def test_search_incidents_reports_total_beyond_result_limit(monkeypatch):
    _seed(monkeypatch)

    gulf = server.search_incidents(site_ids=["DEMO-GULF"], limit=10)
    permian = server.search_incidents(site_ids=["DEMO-PERMIAN"], limit=10)

    assert gulf["returned_count"] == 10
    assert gulf["total_count"] == 100
    assert {item["site_id"] for item in gulf["incidents"]} == {"DEMO-GULF"}
    assert permian["returned_count"] == 10
    assert permian["total_count"] == 100
    assert {item["site_id"] for item in permian["incidents"]} == {"DEMO-PERMIAN"}


def test_search_hse_knowledge_returns_grounding_metadata_without_cross_site_results(monkeypatch):
    _seed(monkeypatch)

    result = server.search_hse_knowledge("blinded line", site_ids=["DEMO-PERMIAN"])

    assert [item["id"] for item in result["results"]] == ["INC-2026-0061"]
    assert result["results"][0]["source_url"].endswith("/incidents/INC-2026-0061")
