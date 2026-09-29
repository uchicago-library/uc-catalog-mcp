"""HTTP client for the UChicago VuFind Search & Record API."""

from __future__ import annotations

import os
from typing import Any

import httpx

from .normalize import DEFAULT_FIELDS

DEFAULT_BASE = "https://catalog.lib.uchicago.edu/vufind"
DEFAULT_TIMEOUT = 20.0
USER_AGENT = "uc-catalog-mcp/0.1 (University of Chicago Library)"


class CatalogError(Exception):
    """Soft failure talking to the catalog API (HTTP / non-JSON / network)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class CatalogClient:
    """Thin wrapper around VuFind `/api/v1/search` and `/api/v1/record`."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("UC_CATALOG_BASE") or DEFAULT_BASE).rstrip(
            "/"
        )
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            transport=transport,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CatalogClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, path: str, params: list[tuple[str, str]]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise CatalogError(f"Catalog request failed: {exc}") from exc

        content_type = response.headers.get("content-type", "")
        if response.status_code != 200:
            raise CatalogError(
                f"Catalog returned HTTP {response.status_code}. "
                "The Search & Record API typically requires campus network or University VPN.",
                status_code=response.status_code,
            )
        if "json" not in content_type.lower():
            # Bot-check / Anubis HTML often arrives as 200 text/html.
            raise CatalogError(
                "Catalog returned a non-JSON response (bot-check or HTML). "
                "Access typically requires campus network or University VPN.",
                status_code=response.status_code,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise CatalogError(
                "Catalog response was not valid JSON. "
                "Access typically requires campus network or University VPN.",
                status_code=response.status_code,
            ) from exc
        if not isinstance(data, dict):
            raise CatalogError("Catalog JSON was not an object.")
        return data

    def search(
        self,
        lookfor: str,
        *,
        type_: str = "AllFields",
        limit: int = 10,
        page: int = 1,
        sort: str | None = None,
        filters: list[str] | None = None,
        facets: list[str] | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        params: list[tuple[str, str]] = [
            ("lookfor", lookfor),
            ("type", type_),
            ("limit", str(limit)),
            ("page", str(page)),
        ]
        if sort:
            params.append(("sort", sort))
        for field in fields or list(DEFAULT_FIELDS):
            params.append(("field[]", field))
        for f in filters or []:
            params.append(("filter[]", f))
        for facet in facets or []:
            params.append(("facet[]", facet))
        return self._get("/api/v1/search", params)

    def get_record(
        self,
        record_id: str,
        *,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        params: list[tuple[str, str]] = [("id", record_id)]
        for field in fields or list(DEFAULT_FIELDS):
            params.append(("field[]", field))
        return self._get("/api/v1/record", params)
