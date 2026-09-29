"""Normalize VuFind Search & Record API payloads into the MCP response shape."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit


DEFAULT_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "authors",
    "formats",
    "buildings",
    "callNumbers",
    "recordPage",
)


def catalog_origin(base_url: str) -> str:
    """Return scheme+host for permalinks (recordPage already includes /vufind)."""
    parts = urlsplit(base_url.rstrip("/"))
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def flatten_authors(authors: Any) -> list[str]:
    """Flatten VuFind authors.primary|secondary|corporate into ordered names."""
    if not authors:
        return []
    if isinstance(authors, list):
        return [str(a) for a in authors if a]
    if isinstance(authors, str):
        return [authors] if authors else []
    if not isinstance(authors, dict):
        return []

    names: list[str] = []
    seen: set[str] = set()
    for bucket in ("primary", "secondary", "corporate"):
        value = authors.get(bucket)
        if value is None:
            continue
        if isinstance(value, dict):
            candidates = list(value.keys())
        elif isinstance(value, list):
            candidates = [str(v) for v in value]
        elif isinstance(value, str):
            candidates = [value]
        else:
            continue
        for name in candidates:
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return names


def normalize_record(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """Map one VuFind record dict to the MCP record schema."""
    record_page = raw.get("recordPage") or ""
    permalink = f"{origin}{record_page}" if record_page else None
    out: dict[str, Any] = {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "authors": flatten_authors(raw.get("authors")),
        "formats": list(raw.get("formats") or []),
        "permalink": permalink,
    }
    if "buildings" in raw and raw["buildings"] is not None:
        out["buildings"] = list(raw["buildings"])
    if "callNumbers" in raw and raw["callNumbers"] is not None:
        out["callNumbers"] = list(raw["callNumbers"])
    return out


def normalize_facets(facets: Any) -> dict[str, list[dict[str, Any]]] | None:
    """Parse VuFind facets into {field: [{value, count}, ...]}."""
    if not isinstance(facets, dict) or not facets:
        return None
    out: dict[str, list[dict[str, Any]]] = {}
    for field, entries in facets.items():
        if not isinstance(entries, list):
            continue
        normalized: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            value = entry.get("value")
            if value is None:
                continue
            item: dict[str, Any] = {"value": value}
            if "count" in entry:
                item["count"] = entry["count"]
            normalized.append(item)
        if normalized:
            out[field] = normalized
    return out or None


def build_search_url(
    base_url: str,
    *,
    lookfor: str,
    type_: str,
    filters: list[str] | None = None,
    sort: str | None = None,
) -> str:
    """Human Results page URL mirroring the API query (same lookfor/type/filters)."""
    base = base_url.rstrip("/")
    params: list[tuple[str, str]] = [
        ("lookfor", lookfor),
        ("type", type_),
    ]
    for f in filters or []:
        params.append(("filter[]", f))
    if sort:
        params.append(("sort", sort))
    return f"{base}/Search/Results?{urlencode(params)}"
