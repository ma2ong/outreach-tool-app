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
import subprocess
import urllib.parse
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


def harvest_with_browser(url: str, limit: int = 40, run=None) -> list[str]:
    """Return distinct company domains listed on `url`, same shape as `harvest_domains`.

    Whatever goes wrong out there — a captcha the browser cannot pass, a step budget
    spent on the wrong tab, Chrome dying — comes back as a short list or an empty one.
    Getting fewer than the page holds is acceptable (docs/124 R6); the caller reviews
    what came back before anything is imported.
    """
    reason = unavailable()
    if reason:
        raise Unavailable(reason)
    argv = [str(VENV_PYTHON), str(RUNNER), "--url", url,
            "--max-steps", str(MAX_STEPS), "--limit", str(limit),
            "--profile-dir", str(PROFILE_DIR)]
    for domain in allowed_domains_for(url):
        argv += ["--allow", domain]
    try:
        raw = (run or _subprocess_run)(argv, RUN_TIMEOUT)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return []
    try:
        companies = json.loads(raw).get("companies") or []
    except (ValueError, AttributeError):
        return []
    self_host = harvest.host_of(url)
    out: list[str] = []
    seen: set[str] = set()
    for company in companies:
        # docs/124 R1: one field crosses this line. Everything else the model said
        # about this company stays on the other side of the subprocess.
        host = _host_of(company.get("domain") if isinstance(company, dict) else "")
        if host in seen or not harvest.is_prospect_host(host, self_host):
            continue
        seen.add(host)
        out.append(host)
        if len(out) >= max(1, limit):
            break
    return out
