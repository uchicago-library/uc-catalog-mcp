from uc_catalog_mcp.normalize import (
    build_search_url,
    catalog_origin,
    flatten_authors,
    normalize_facets,
    normalize_record,
)


def test_flatten_authors_primary_secondary():
    raw = {
        "primary": {"Tolkien, Christopher": []},
        "secondary": {
            "Tolkien, J. R. R. (John Ronald Reuel), 1892-1973": [],
            "Tolkien, J. R. R.": [],
        },
        "corporate": [],
    }
    assert flatten_authors(raw) == [
        "Tolkien, Christopher",
        "Tolkien, J. R. R. (John Ronald Reuel), 1892-1973",
        "Tolkien, J. R. R.",
    ]


def test_normalize_record_permalink_uses_origin():
    origin = catalog_origin("https://catalog.lib.uchicago.edu/vufind")
    assert origin == "https://catalog.lib.uchicago.edu"
    rec = normalize_record(
        {
            "id": "12899207",
            "title": "Sauron defeated",
            "authors": {"primary": {"Tolkien, Christopher": []}},
            "formats": ["Book"],
            "buildings": ["Internet"],
            "callNumbers": ["PR6039.O32L63743 1992"],
            "recordPage": "/vufind/Record/12899207",
        },
        origin,
    )
    assert rec["permalink"] == "https://catalog.lib.uchicago.edu/vufind/Record/12899207"
    assert rec["authors"] == ["Tolkien, Christopher"]
    assert rec["buildings"] == ["Internet"]
    assert rec["callNumbers"] == ["PR6039.O32L63743 1992"]


def test_build_search_url_includes_filters():
    url = build_search_url(
        "https://catalog.lib.uchicago.edu/vufind",
        lookfor="tolkien",
        type_="Author",
        filters=['format:"Book"', "building:Regenstein Library"],
    )
    assert url.startswith(
        "https://catalog.lib.uchicago.edu/vufind/Search/Results?"
    )
    assert "lookfor=tolkien" in url
    assert "type=Author" in url
    assert "filter" in url


def test_normalize_facets():
    facets = normalize_facets(
        {
            "format": [
                {"value": "Book", "count": 100},
                {"value": "Print", "count": 91},
            ]
        }
    )
    assert facets == {
        "format": [
            {"value": "Book", "count": 100},
            {"value": "Print", "count": 91},
        ]
    }
