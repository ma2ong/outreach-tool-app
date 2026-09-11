"""Reading a directory page that a crawler cannot read (docs/124).

On 2026-09-10 four real listings — ISE and InfoComm exhibitors, Absen's distributors,
the LEDs Magazine supplier index — went through `jina.fetch` + `harvest_domains` and
produced zero companies between them. Two answered with an anti-bot wall; the other two
handed over CDN and social domains while the actual list stayed inside JavaScript. A
browser driven by a model read 66 AV distributors off the Absen page in 85 seconds.

The same run also read a company name off the string
`syscom-cloned-21865-Avientek-Logo--768x134.png`. Both facts are load-bearing, and
together they decide the interface: this module returns **domains and nothing else**.
Names, countries, emails and the ICP score come from `enrich_domain` reading each
company's own site, exactly as they do for a candidate found by keyword search. A
fabricated name has no way in, and a fabricated domain dies at enrichment.

It runs in its own virtualenv through a subprocess. `pip install browser-use` pulls in
about a hundred packages including openai 2.x, pydantic and an httpx fork; installing
that beside the server would reinstall dependencies uvicorn is running on. The shape is
the one `agent/llm.py` already uses for the Claude CLI.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse
from collections.abc import Sequence
from pathlib import Path

from app import harvest

VENV_PYTHON = Path.home() / ".outreach-tool" / "bu-venv" / "Scripts" / "python.exe"
RUNNER = Path(__file__).resolve().parent / "browser_harvest_runner.py"
PROFILE_DIR = Path.home() / ".outreach-tool" / "bu-profile"

MAX_STEPS = 12
RUN_TIMEOUT = 300              # hard ceiling; the runner stops itself before this
KEY_ENV = "OUTREACH_BU_KEY"


class Unavailable(RuntimeError):
    """The browser route is not installed or not configured — not a failure to retry."""


def _key() -> str:
    """The same deepseek key the classifier uses; read at call time, never stored."""
    from app.agent import llm

    return llm.read_key("deepseek")


def unavailable() -> str:
    """Why this cannot run right now, or "" when it can (docs/70 R4, docs/124 R5)."""
    if not Path(VENV_PYTHON).exists():
        return (f"没有安装浏览器采集环境（{VENV_PYTHON}）。"
                "建一个 Python 3.12 虚拟环境到 ~/.outreach-tool/bu-venv 并装 browser-use")
    if not _key():
        return "缺少 backend/deepseek_key.txt，浏览器采集需要它来读页面"
    return ""


def available() -> bool:
    return not unavailable()


def allowed_domains_for(url: str) -> list[str]:
    """The only domains the browser may visit: the target listing's own host.

    Deliberately not widened to the registrable domain. `exhibitors.iseurope.org` is
    one listing, not permission to walk iseurope.org, and guessing where a public
    suffix ends is how that widening goes wrong on `.co.uk`.
    """
    host = harvest.host_of(url)
    return [f"*.{host}"] if host else []


def _host_of(value: str) -> str:
    text = str(value or "").strip()
    return harvest.host_of(text if "://" in text else f"http://{text}")


def _subprocess_run(argv: list[str], timeout: int) -> str:
    # The key goes through the environment, not argv: arguments are readable in the
    # process list by anything running on this machine.
    env = {**os.environ, KEY_ENV: _key()}
    done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          env=env, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise subprocess.CalledProcessError(done.returncode, argv, stderr=done.stderr)
    return done.stdout


# The one field each task may hand back (docs/124 R1, docs/126 R2). A task that reads
# prose returns names because the companies it finds have no link to return; a name is
# then spent as a search query and never stored, which is what keeps R1 intact.
TASK_FIELD = {"directory": "domain", "search": "domain", "prose": "name",
              "social": "domain"}

MAX_NAME = 80
# A name that carries a dot, an @ or a scheme is a domain wearing a name's clothes.
# docs/126 R2 works only if the two fields cannot be swapped by the model.
_NOT_A_NAME = re.compile(r"https?://|@|\.[a-z]{2,}(?:$|[/\s])", re.I)


def read_with_browser(url: str, *, task: str = "directory", query: str = "",
                      limit: int = 40, allow: Sequence[str] | None = None,
                      profile_dir=None, run=None) -> list[str]:
    """Read one page with a real browser and return domains, or names for `prose`.

    Whatever goes wrong out there — a captcha the browser cannot pass, a step budget
    spent on the wrong tab, Chrome dying — comes back as a short list or an empty one.
    Getting fewer than the page holds is acceptable (docs/124 R6); the caller reviews
    what came back before anything is imported.

    `allow` is the browser's domain allowlist. A declared channel passes its own
    (docs/126 R3): `search.naver.com` alone would block the `blog.naver.com` posts that
    channel exists to open, and widening a host to its registrable domain by guessing
    is what docs/124 R3 refused to do. A bare page passes nothing and gets its own host.
    """
    if task not in TASK_FIELD:
        raise ValueError(f"unknown browser task: {task}")
    reason = unavailable()
    if reason:
        raise Unavailable(reason)
    # A channel with a login of its own passes its collecting profile; everything else
    # shares the anonymous one. The sending profiles are reachable from neither.
    argv = [str(VENV_PYTHON), str(RUNNER), "--url", url, "--task", task,
            "--max-steps", str(MAX_STEPS), "--limit", str(limit),
            "--profile-dir", str(profile_dir or PROFILE_DIR)]
    if query:
        argv += ["--query", query]
    # Never from the task text: an allowlist a prompt can name is not an allowlist.
    for domain in (list(allow) if allow else allowed_domains_for(url)):
        argv += ["--allow", domain]
    try:
        raw = (run or _subprocess_run)(argv, RUN_TIMEOUT)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return []
    try:
        companies = json.loads(raw).get("companies") or []
    except (ValueError, AttributeError):
        return []
    field = TASK_FIELD[task]
    self_host = harvest.host_of(url)
    out: list[str] = []
    seen: set[str] = set()
    for company in companies:
        # docs/124 R1: one field crosses this line. Everything else the model said
        # about this company stays on the other side of the subprocess.
        value = company.get(field) if isinstance(company, dict) else None
        item = _clean_name(value) if field == "name" else _host_of(value or "")
        if not item or item.lower() in seen:
            continue
        if field == "domain" and not harvest.is_prospect_host(item, self_host):
            continue
        seen.add(item.lower())
        out.append(item)
        if len(out) >= max(1, limit):
            break
    return out


def _clean_name(value) -> str:
    name = " ".join(str(value or "").split())[:MAX_NAME]
    return "" if not name or _NOT_A_NAME.search(name) else name


def harvest_with_browser(url: str, limit: int = 40, run=None) -> list[str]:
    """The docs/124 entry point: company domains off one directory page."""
    return read_with_browser(url, task="directory", limit=limit, run=run)
