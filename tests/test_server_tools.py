import json
from pathlib import Path

import httpx

from uc_catalog_mcp import server as server_mod
from uc_catalog_mcp.client import CatalogClient

FIXTURES = Path(__file__).parent / "fixtures"


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/api/v1/search"):
        body = (FIXTURES / "search_tolkien.json").read_text()
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})
    if request.url.path.endswith("/api/v1/record"):
        body = (FIXTURES / "record_12899207.json").read_text()
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})
    return httpx.Response(404, text="missing")


class FakeClient(CatalogClient):
    def __init__(self) -> None:
        super().__init__(transport=httpx.MockTransport(_handler))


def test_search_tool(monkeypatch):
    monkeypatch.setattr(server_mod, "CatalogClient", FakeClient)
    result = server_mod.search(
        lookfor="tolkien",
        type="Author",
        facet=["format", "building"],
        limit=2,
    )
    assert result["ok"] is True
    assert result["resultCount"] == 118
    assert result["records"][0]["id"] == "12899207"
    assert "searchUrl" in result
    assert "facets" in result
    assert result["records"][0]["permalink"].endswith("/vufind/Record/12899207")


def test_get_record_tool(monkeypatch):
    monkeypatch.setattr(server_mod, "CatalogClient", FakeClient)
    result = server_mod.get_record(id="12899207")
    assert result["ok"] is True
    assert result["record"]["id"] == "12899207"
    assert result["record"]["buildings"] == ["Internet"]


def test_search_empty_lookfor():
    result = server_mod.search(lookfor="  ")
    assert result["ok"] is False
