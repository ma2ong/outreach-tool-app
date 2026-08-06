from typing import Callable

from app import repository as repo, screening
from app.search import search_domains
from app.enrich import enrich_domain
from app.harvest import harvest_domains


def _enrich_candidates(conn, domains: list[dict], enrich_fn: Callable,
                       source: str, on_progress: Callable[[int, int], None] | None,
                       exclude_countries: list[str] | None = None,
                       exclude_peers: bool = True) -> list[dict]:
    out = []
    total = len(domains)
    for i, d in enumerate(domains, 1):
        domain = d["domain"]
        # Screen on the domain alone first: a directory site or a .cn peer is not worth
        # the enrich fetch (that is the slow part of discovery).
        pre = screening.screen({"domain": domain}, exclude_countries, exclude_peers)
        info = {} if pre["excluded"] else enrich_fn(domain)
        cand = {
            "domain": domain,
            "title": d.get("title") or info.get("company") or domain,
            "email": info.get("email"),
            "emails": info.get("emails", []),
            "phone": info.get("phone"),
            "instagram": info.get("instagram"),
            "facebook": info.get("facebook"),
            "linkedin": info.get("linkedin"),
            "icp_type": info.get("icp_type", "unknown"),
            "fit_score": info.get("fit_score", 0),
            "brief": info.get("brief") or None,
            "hook": info.get("hook") or None,
            "email_source": info.get("email_source"),
            "source": source,
        }
        # Re-screen with the enriched phone/email: +86 in the contact details is the
        # strongest peer signal and only shows up after enrich.
        post = pre if pre["excluded"] else screening.screen(cand, exclude_countries, exclude_peers)
        cand.update(post)
        cand["duplicate_of"] = repo.find_duplicate(conn, website=domain,
                                                   instagram=cand["instagram"])
        out.append(cand)
        if on_progress:
            on_progress(i, total)
    return out


def run_discovery(conn, query: str, limit: int = 10,
                  search_fn: Callable = None, enrich_fn: Callable = None,
                  on_progress: Callable[[int, int], None] | None = None,
                  exclude_countries: list[str] | None = None,
                  exclude_peers: bool = True) -> list[dict]:
    search_fn = search_fn or (lambda q, lim: search_domains(q, lim))
    enrich_fn = enrich_fn or (lambda d: enrich_domain(d))
    domains = search_fn(query, limit)
    return _enrich_candidates(conn, domains, enrich_fn, "搜索", on_progress,
                              exclude_countries, exclude_peers)


def run_page_discovery(conn, url: str, limit: int = 40,
                       harvest_fn: Callable = None, enrich_fn: Callable = None,
                       on_progress: Callable[[int, int], None] | None = None,
                       exclude_countries: list[str] | None = None,
                       exclude_peers: bool = True) -> list[dict]:
    """Harvest company domains from a directory/distributor page, then enrich each."""
    harvest_fn = harvest_fn or (lambda u, lim: harvest_domains(u, lim))
    enrich_fn = enrich_fn or (lambda d: enrich_domain(d))
    domains = [{"domain": h, "title": ""} for h in harvest_fn(url, limit)]
    return _enrich_candidates(conn, domains, enrich_fn, "名录/经销商页", on_progress,
                              exclude_countries, exclude_peers)
