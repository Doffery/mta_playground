"""Web search backend using DuckDuckGo (no API key required)."""

from typing import Callable

Searcher = Callable[[str], str]


def web_search(query: str, max_results: int = 5) -> str:
    """Return a formatted string of search results for *query*."""
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        return f"Search error: {exc}"

    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "").strip()
        url = r.get("href", "").strip()
        snippet = r.get("body", "").strip()
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    return "\n\n".join(lines)
