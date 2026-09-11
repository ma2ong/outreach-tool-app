"""Harvest company domains from a directory-style page.

Point it at a competitor's "where to buy / distributors" page or a trade-show
exhibitor listing (ISE / InfoComm / LED China) and it pulls every outbound company
domain, which then flows through the same enrich pipeline as keyword search. This
turns two LED-specific high-value buyer pools into candidates without a browser.
"""
import re
import urllib.parse
from typing import Callable

from app.jina import fetch as jina_fetch

# Hosts that are never a prospect's own site.
_SKIP = (
    "duckduckgo.com", "jina.ai", "wikipedia.org", "w3.org", "schema.org",
    "google.com", "bing.com", "youtube.com", "youtu.be", "vimeo.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "t.me", "wa.me", "whatsapp.com", "pinterest.com", "tiktok.com",
    "gstatic.com", "googleapis.com", "cloudflare.com", "gravatar.com",
    "apple.com", "microsoft.com", "adobe.com", "wordpress.org", "gmpg.org",
)
_URL = re.compile(r'https?://[^\s"\'<>\)\]]+', re.I)


def host_of(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_prospect_host(host: str, self_host: str = "") -> bool:
    """False for the page's own host, a platform/CDN, localhost and IP literals.

    Shared with the browser route (docs/124 R1): a second, slightly different copy of
    this list is how one of the two channels quietly starts importing facebook.com.
    """
    if not host or "." not in host:
        return False
    if host.split(":")[0] == "localhost" or host.replace(".", "").replace(":", "").isdigit():
        return False
    return host != self_host and not any(s in host for s in _SKIP)


def harvest_domains(url: str, limit: int = 40,
                    fetch: Callable[[str], str] = jina_fetch) -> list[str]:
    """Return distinct external company domains linked from `url`, in page order."""
    text = fetch(url)
    self_host = host_of(url)
    out: list[str] = []
    seen: set[str] = set()
    for m in _URL.finditer(text):
        host = host_of(m.group(0))
        if host in seen or not is_prospect_host(host, self_host):
            continue
        seen.add(host)
        out.append(host)
        if len(out) >= limit:
            break
    return out
