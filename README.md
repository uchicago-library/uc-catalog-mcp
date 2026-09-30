# uc-catalog-mcp

MCP server for the [University of Chicago Library catalog](https://catalog.lib.uchicago.edu/vufind)
(VuFind Search & Record API). Exposes two tools over **stdio**: `search` and
`get_record`.

## Catalog access / VPN

The Search & Record API is typically reachable only from **campus network or
University VPN**. Off-network callers may receive a bot-check page or HTTP
`403` instead of JSON. This server fails soft in those cases and does not invent
holdings.

Override the API base with `UC_CATALOG_BASE` (default
`https://catalog.lib.uchicago.edu/vufind`).

## Install

Clone this repository, then install dependencies into that checkout (editable
install is enough for local MCP use):

```bash
cd /path/to/uc-catalog-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires [uv](https://docs.astral.sh/uv/) on your `PATH` for the Claude config
below (`uv run` uses the project environment).

## Claude / MCP host config

Point Claude Desktop (or another stdio MCP host) at the checkout with
`uv run --directory`. Replace `/path/to/uc-catalog-mcp` with your clone path:

```json
{
  "mcpServers": {
    "uc-catalog": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/uc-catalog-mcp",
        "python",
        "-m",
        "uc_catalog_mcp"
      ],
      "env": {
        "UC_CATALOG_BASE": "https://catalog.lib.uchicago.edu/vufind"
      }
    }
  }
}
```

Do **not** rely on `"command": "python"` plus `"cwd"` alone — that form often
fails to resolve the package in Claude’s MCP launcher. `uv run --directory`
keeps the working tree and environment explicit.

After an editable install you can also run the console script
`uc-catalog-mcp` from a shell for a quick smoke check.

## Tools

### `search`

| Argument | Notes |
|---|---|
| `lookfor` | Query string (required) |
| `type` | `AllFields` (default), `Title`, `Author`, `Subject`, `ISN`, … |
| `filter` | Repeatable VuFind filters, e.g. `format:"Book"`, `building:"Regenstein Library"` |
| `facet` | Repeatable facet fields, e.g. `format`, `building` |
| `limit` | Page size (default 10, max 100) |
| `page` | Result page (default 1) |
| `sort` | Optional VuFind sort |

Returns `resultCount`, `records` (`id`, `title`, `authors`, `formats`,
`buildings`, `callNumbers` when present, record `permalink`), `facets` when
requested, and a human catalog `searchUrl` for the same query.

`buildings` comes from the Solr **building** field; `callNumbers` from
**callnumber-raw** (indexed holdings metadata, **not** live circulation).

### `get_record`

| Argument | Notes |
|---|---|
| `id` | Single catalog record id (required; no batch) |

Same core fields as search records, plus permalink / buildings / callNumbers.

## What this does **not** do

- Enrichment (WikiData, Internet Archive, PubMed, HathiTrust, …)
- Live FOLIO availability / circulation status
- MyAccount, holds, or patron actions
- A separate `list_facets` tool (request facets via `search`)

## Development

```bash
pytest
```

Unit tests mock HTTP. Live checks against the catalog require campus network or
University VPN.

## License

MIT
