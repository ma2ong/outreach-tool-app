import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from app import repository as repo, screening
from app.search import search_domains
from app.enrich import enrich_domain
from app.harvest import harvest_domains
from app.jina import fetch as jina_fetch

AUTO_IMPORT_LIMIT = 10
MAX_ENRICH_WORKERS = 4
DISCOVERY_FETCH_TIMEOUT = 15

_COUNTRY_ALIASES = {
    "us": "usa", "u.s.": "usa", "united states": "usa", "united states of america": "usa",
    "uk": "united kingdom", "great britain": "united kingdom",
    "korea": "south korea", "republic of korea": "south korea", "kr": "south korea",
}


def _bounded_fetch(url: str) -> str:
    """Discovery favors a partial batch over waiting 45 seconds on every dead page."""
    return jina_fetch(url, timeout=DISCOVERY_FETCH_TIMEOUT)


def _country_key(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    return _COUNTRY_ALIASES.get(raw, raw)


def _name_from_domain(domain: str | None) -> str:
    host = re.sub(r"^https?://|^www\.", "", (domain or "").strip(), flags=re.I)
    label = host.split("/")[0].split(".")[0].replace("-", " ").replace("_", " ")
    return " ".join(word.capitalize() for word in label.split())


def candidate_name(candidate: dict) -> str:
    """A conservative company name for unattended imports.

    Search titles are often taglines or page labels. A domain-derived name is less
    polished but honest, which is the better failure mode for an autonomous path.
    """
    supplied = str(candidate.get("company_en") or "").strip()
    if supplied:
        return supplied
    title = re.sub(r"^contact\s+", "", str(candidate.get("title") or "").strip(),
                   flags=re.I).strip()
    generic = {"contact", "contact us", "home", "homepage", "page not found", "404"}
    if (title and title.lower() not in generic and len(title) <= 40
            and len(title.split()) <= 4):
        return title
    return _name_from_domain(candidate.get("website") or candidate.get("domain"))


def qualify_for_auto_import(candidates: list[dict], minimum_fit: int,
                            limit: int = AUTO_IMPORT_LIMIT,
                            email_classifier: Callable | None = None,
                            target_country: str | None = None,
                            ) -> tuple[list[dict], list[dict]]:
    """Separate prospects safe for unattended import from candidates needing review."""
    from app import verify
    accepted: list[dict] = []
    rejected: list[dict] = []
    for candidate in candidates:
        domain = str(candidate.get("domain") or candidate.get("website") or "").strip()
        reason = ""
        if candidate.get("excluded"):
            reason = f"已被筛选排除：{candidate.get('exclude_reason') or '非目标客户'}"
        elif candidate.get("duplicate_of"):
            reason = f"重复客户：#{candidate['duplicate_of']}"
        elif not domain:
            reason = "缺少官网域名"
        elif (target_country and candidate.get("country")
              and _country_key(candidate.get("country")) != _country_key(target_country)):
            reason = f"目标市场不符：识别为 {candidate['country']}，任务要求 {target_country}"
        else:
            if email_classifier:
                # Autonomous execution passes the real DNS-aware classifier. Direct
                # callers retain the cheap syntax-only behavior for manual review.
                status, why = email_classifier(str(candidate.get("email") or ""))
            else:
                status, why = verify.classify_email(
                    str(candidate.get("email") or ""), resolve_domain=lambda _: True)
            if status == "invalid":
                reason = f"没有可用公开邮箱（{why}）"
        try:
            fit = int(candidate.get("fit_score") or 0)
        except (TypeError, ValueError):
            fit = 0
        if not reason and (candidate.get("icp_type") in (None, "", "unknown")
                           or fit < minimum_fit):
            reason = f"ICP {fit} 低于自动导入门槛 {minimum_fit}"
        if not reason and not (candidate.get("hook") or candidate.get("brief")):
            reason = "缺少官网个性化依据"
        if reason:
            rejected.append({"domain": domain, "reason": reason})
        elif len(accepted) < limit:
            accepted.append(candidate)
        else:
            rejected.append({"domain": domain, "reason": f"超过单次自动导入上限 {limit}"})
    return accepted, rejected


# Only ever filled when blank. A phone read off a search result does not get to
# overwrite one Allen typed, and docs/45 forbids guessing either way.
_FILLABLE = ("email", "phone", "instagram", "facebook", "linkedin", "city", "country",
             "website", "brief", "hook")


def enrich_existing(conn, lead_no: int, candidate: dict) -> list[str]:
    """Fill what this company's record is missing. Returns the field names gained."""
    from app import relationship_events

    current = conn.execute("SELECT * FROM leads WHERE no=?", (lead_no,)).fetchone()
    if current is None:
        return []
    patch = {}
    for field in _FILLABLE:
        fresh = str(candidate.get(field) or "").strip()
        if not fresh:
            continue
        # str(None) is "None", which reads as a value and would block every blank field.
        held = current[field] if field in current.keys() else None
        if not str(held or "").strip():
            patch[field] = fresh
    if not patch:
        return []
    if "email" in patch and candidate.get("email_source"):
        patch["email_source"] = candidate["email_source"]
    repo.update_lead(conn, lead_no, patch)
    gained = [f for f in patch if f != "email_source"]
    relationship_events.record(
        conn, lead_no, "fact",
        "开发过程中补到：" + "、".join(gained),
        source="discovery",
        detail={"fields": {k: patch[k] for k in gained},
                "found_via": candidate.get("source") or "discovery"})
    return gained


def import_candidates(conn, candidates: list[dict], default_country: str | None = None) -> dict:
    """The one import path shared by the browser and autonomous Agent."""
    from app import blocklist, icp as icp_mod, sales_intelligence
    imported: list[int] = []
    skipped: list[dict] = []
    enriched = 0
    signals_imported = 0
    signal_errors: list[dict] = []
    for candidate in candidates:
        website = candidate.get("website") or candidate.get("domain")
        company = candidate_name(candidate)
        duplicate = repo.find_duplicate(conn, website=website,
                                        instagram=candidate.get("instagram"))
        if duplicate:
            # Not a dead end. Prospecting keeps walking into companies already in the
            # book, and what it learned about them on the way — a direct line, a new
            # contact, this year's projects — used to be thrown away because the only
            # question asked was "is this new?" (docs/68 R4.3). A fresh fact about a
            # company we have already touched is worth more than a stranger.
            gained = enrich_existing(conn, duplicate, candidate)
            skipped.append({"company_en": company, "website": website,
                            "duplicate_of": duplicate, "enriched": gained})
            enriched += len(gained)
            continue
        fit = "discovered"
        if candidate.get("icp_type") and candidate.get("icp_type") != "unknown":
            fit = f"{icp_mod.label(candidate['icp_type'])} ({candidate.get('fit_score') or 0})"
        try:
            no = repo.insert_lead(conn, {
                "company_en": company, "country": candidate.get("country") or default_country,
                "city": candidate.get("city"), "website": website,
                "email": candidate.get("email"), "phone": candidate.get("phone"),
                "instagram": candidate.get("instagram"), "facebook": candidate.get("facebook"),
                "linkedin": candidate.get("linkedin"), "target_fit": fit,
                "brief": candidate.get("brief"), "hook": candidate.get("hook"),
                "email_source": candidate.get("email_source"),
            })
        except blocklist.BlockedLead as exc:
            skipped.append({"company_en": company, "website": website,
                            "blocked_domain": exc.domain})
            continue
        if candidate.get("icp_type") and candidate.get("icp_type") != "unknown":
            icp_mod.apply_to_lead(conn, no, {
                "icp_type": candidate["icp_type"],
                "fit_score": candidate.get("fit_score") or 0,
            })
        imported.append(no)
        # Signal candidates are evidence from the same public pages already used to
        # qualify this company. Persist only after the lead exists; rejected candidates
        # therefore cannot create orphan signal rows.
        for signal in candidate.get("buying_signals") or []:
            try:
                sales_intelligence.create_signal(conn, no, signal)
                signals_imported += 1
            except (sales_intelligence.SalesIntelligenceValidation, TypeError, ValueError) as exc:
                signal_errors.append({"lead_no": no, "headline": signal.get("headline"),
                                      "error": str(exc)})
    result = {"imported": len(imported), "imported_lead_nos": imported,
              "skipped": skipped, "enriched_fields": enriched}
    if signals_imported or signal_errors:
        result["signals_imported"] = signals_imported
        result["signal_errors"] = signal_errors
    return result


def _enrich_candidates(conn, domains: list[dict], enrich_fn: Callable,
                       source: str, on_progress: Callable[[int, int], None] | None,
                       exclude_countries: list[str] | None = None,
                       exclude_peers: bool = True) -> list[dict]:
    out: list[dict] = []
    total = len(domains)

    def finish(d: dict, pre: dict, info: dict) -> dict:
        domain = d["domain"]
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
            "buying_signals": info.get("buying_signals") or [],
            "source": source,
        }
        # Re-screen with the enriched phone/email: +86 in the contact details is the
        # strongest peer signal and only shows up after enrich.
        post = pre if pre["excluded"] else screening.screen(
            {**cand, "country": info.get("country")}, exclude_countries, exclude_peers)
        cand.update(post)
        cand["duplicate_of"] = repo.find_duplicate(conn, website=domain,
                                                   instagram=cand["instagram"])
        return cand

    # Fetching one prospect can touch five pages. Four workers keep a 20-domain batch
    # bounded without opening an aggressive crawler-sized fan-out against Jina/sites.
    queued: list[tuple[dict, dict]] = []
    done = 0
    for d in domains:
        pre = screening.screen({"domain": d["domain"]}, exclude_countries, exclude_peers)
        if pre["excluded"]:
            out.append(finish(d, pre, {}))
            done += 1
            if on_progress:
                on_progress(done, total)
        else:
            queued.append((d, pre))
    if queued:
        workers = min(MAX_ENRICH_WORKERS, len(queued))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(enrich_fn, d["domain"]): (d, pre)
                       for d, pre in queued}
            for future in as_completed(futures):
                d, pre = futures[future]
                try:
                    info = future.result() or {}
                except Exception:  # one unreachable site must not sink the batch
                    info = {}
                out.append(finish(d, pre, info))
                done += 1
                if on_progress:
                    on_progress(done, total)
    return out


def run_discovery(conn, query: str, limit: int = 10,
                  search_fn: Callable = None, enrich_fn: Callable = None,
                  on_progress: Callable[[int, int], None] | None = None,
                  exclude_countries: list[str] | None = None,
                  exclude_peers: bool = True) -> list[dict]:
    search_fn = search_fn or (lambda q, lim: search_domains(q, lim, fetch=_bounded_fetch))
    enrich_fn = enrich_fn or (lambda d: enrich_domain(d, fetch=_bounded_fetch))
    domains = search_fn(query, limit)
    return _enrich_candidates(conn, domains, enrich_fn, "搜索", on_progress,
                              exclude_countries, exclude_peers)


def run_page_discovery(conn, url: str, limit: int = 40,
                       harvest_fn: Callable = None, enrich_fn: Callable = None,
                       on_progress: Callable[[int, int], None] | None = None,
                       exclude_countries: list[str] | None = None,
                       exclude_peers: bool = True) -> list[dict]:
    """Harvest company domains from a directory/distributor page, then enrich each."""
    harvest_fn = harvest_fn or (lambda u, lim: harvest_domains(u, lim, fetch=_bounded_fetch))
    enrich_fn = enrich_fn or (lambda d: enrich_domain(d, fetch=_bounded_fetch))
    domains = [{"domain": h, "title": ""} for h in harvest_fn(url, limit)]
    return _enrich_candidates(conn, domains, enrich_fn, "名录/经销商页", on_progress,
                              exclude_countries, exclude_peers)
