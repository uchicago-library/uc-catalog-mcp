"""stdio MCP server exposing UChicago Library catalog search and get_record."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .client import CatalogClient, CatalogError
from .normalize import build_search_url, catalog_origin, normalize_facets, normalize_record

SEARCH_DESCRIPTION = (
    "Search the University of Chicago Library catalog (VuFind). "
    "Supports lookfor, type (AllFields, Title, Author, Subject, ISN, …), "
    "filter[] (including building/place), facet[] (format, building, …), "
    "limit, page, and sort. "
    "buildings come from the Solr building field; callNumbers from "
    "callnumber-raw (indexed holdings metadata, not live circulation). "
    "Returns resultCount, records, optional facets, and a catalog searchUrl. "
    "Catalog access typically requires campus network or University VPN."
)

GET_RECORD_DESCRIPTION = (
    "Fetch a single University of Chicago Library catalog record by id. "
    "Returns id, title, authors, formats, buildings, callNumbers when present, "
    "and a record permalink. "
    "buildings come from the Solr building field; callNumbers from "
    "callnumber-raw (indexed holdings metadata, not live circulation). "
    "Does not support batch ids. "
    "Catalog access typically requires campus network or University VPN."
)

mcp = MCPServer(
    "uc-catalog-mcp",
    version="0.1.0",
    instructions=(
        "Search and fetch records from the University of Chicago Library "
        "catalog. Does not provide enrichment, live FOLIO availability, "
        "or MyAccount/holds."
    ),
)


def _error_payload(exc: CatalogError) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": exc.message}
    if exc.status_code is not None:
        out["statusCode"] = exc.status_code
    return out


@mcp.tool(name="search", description=SEARCH_DESCRIPTION)
def search(
    lookfor: str,
    type: str = "AllFields",
    filter: list[str] | None = None,
    facet: list[str] | None = None,
    limit: int = 10,
    page: int = 1,
    sort: str | None = None,
) -> dict[str, Any]:
    """Search the catalog and return normalized records plus searchUrl."""
    if not lookfor or not str(lookfor).strip():
        return {"ok": False, "error": "lookfor is required."}
    limit = max(1, min(int(limit), 100))
    page = max(1, int(page))

    with CatalogClient() as client:
        try:
            raw = client.search(
                lookfor.strip(),
                type_=type,
                limit=limit,
                page=page,
                sort=sort,
                filters=filter,
                facets=facet,
            )
        except CatalogError as exc:
            return _error_payload(exc)

        origin = catalog_origin(client.base_url)
        records = [
            normalize_record(r, origin)
            for r in (raw.get("records") or [])
            if isinstance(r, dict)
        ]
        result: dict[str, Any] = {
            "ok": True,
            "query": lookfor.strip(),
            "type": type,
            "resultCount": raw.get("resultCount", 0),
            "searchUrl": build_search_url(
                client.base_url,
                lookfor=lookfor.strip(),
                type_=type,
                filters=filter,
                sort=sort,
            ),
            "records": records,
        }
        facets = normalize_facets(raw.get("facets"))
        if facets is not None:
            result["facets"] = facets
        return result


@mcp.tool(name="get_record", description=GET_RECORD_DESCRIPTION)
def get_record(id: str) -> dict[str, Any]:
    """Fetch one catalog record by id."""
    if not id or not str(id).strip():
        return {"ok": False, "error": "id is required."}

    with CatalogClient() as client:
        try:
            raw = client.get_record(str(id).strip())
        except CatalogError as exc:
            return _error_payload(exc)

        records = raw.get("records") or []
        if not records or not isinstance(records[0], dict):
            return {"ok": False, "error": f"Record not found: {id}"}

        origin = catalog_origin(client.base_url)
        return {"ok": True, "record": normalize_record(records[0], origin)}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
