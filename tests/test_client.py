import json
from pathlib import Path

import httpx
import pytest

from uc_catalog_mcp.client import CatalogClient, CatalogError

FIXTURES = Path(__file__).parent / "fixtures"


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/api/v1/search"):
        body = (FIXTURES / "search_tolkien.json").read_text()
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})
    if request.url.path.endswith("/api/v1/record"):
        body = (FIXTURES / "record_12899207.json").read_text()
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})
    return httpx.Response(404, text="missing")


def test_search_mocked():
    transport = httpx.MockTransport(_handler)
    with CatalogClient(transport=transport) as client:
        data = client.search("tolkien", type_="Author", limit=2, facets=["format", "building"])
    assert data["resultCount"] == 118
    assert data["records"][0]["id"] == "12899207"


def test_get_record_mocked():
    transport = httpx.MockTransport(_handler)
    with CatalogClient(transport=transport) as client:
        data = client.get_record("12899207")
    assert data["records"][0]["id"] == "12899207"


def test_http_error_fails_soft():
    def boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="<html>bot check</html>", headers={"content-type": "text/html"})

    transport = httpx.MockTransport(boom)
    with CatalogClient(transport=transport) as client:
        with pytest.raises(CatalogError) as excinfo:
            client.search("tolkien")
    assert excinfo.value.status_code == 403
    assert "VPN" in excinfo.value.message or "campus" in excinfo.value.message


def test_non_json_200_fails_soft():
    def html_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html>Checking if you're a robot!</html>",
            headers={"content-type": "text/html"},
        )

    transport = httpx.MockTransport(html_ok)
    with CatalogClient(transport=transport) as client:
        with pytest.raises(CatalogError) as excinfo:
            client.search("tolkien")
    assert "non-JSON" in excinfo.value.message
