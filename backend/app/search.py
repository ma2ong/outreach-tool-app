import re
import urllib.parse
from typing import Callable

from app.jina import fetch as jina_fetch

_SKIP = ("duckduckgo.com", "jina.ai", "wikipedia.org", "w3.org", "schema.org", "google.com", "bing.com")


def search_urls(query: str, limit: int = 10,
                fetch: Callable[[str], str] = jina_fetch,
                allowed_domain: str | None = None) -> list[str]:
    """Return exact public result URLs from DuckDuckGo, preserving order.

    Decision-maker research needs the page URL, not just its host. `allowed_domain`
    keeps targeted account research on the customer's own public website; it is not a
    general people scraper and never follows arbitrary third-party profiles here.
    """
    enc = urllib.parse.quote(query)
    text = fetch(f"https://html.duckduckgo.com/html/?q={enc}")
    allowed = (allowed_domain or "").lower().removeprefix("www.").strip()
    out: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r'uddg=([^&"\)\s]+)', text):
        target = urllib.parse.unquote(m.group(1)).rstrip("/.,)")
        parsed = urllib.parse.urlparse(target)
        host = parsed.netloc.lower().removeprefix("www.")
        if not host or any(s in host for s in _SKIP):
            continue
        if allowed and not (host == allowed or host.endswith("." + allowed)):
            continue
        if target in seen:
            continue
        seen.add(target)
        out.append(target)
        if len(out) >= max(1, limit):
            break
    return out


def search_domains(query: str, limit: int = 10,
                   fetch: Callable[[str], str] = jina_fetch) -> list[dict]:
    seen: dict[str, dict] = {}
    # Pull a few extra URLs because several results may point to different pages of the
    # same company; the public discovery contract remains unique domains.
    for target in search_urls(query, limit=max(limit * 3, limit), fetch=fetch):
        host = urllib.parse.urlparse(target).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host not in seen:
            seen[host] = {"domain": host, "title": ""}
        if len(seen) >= limit:
            break
    return list(seen.values())
