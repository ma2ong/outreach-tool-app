"""Runs inside ~/.outreach-tool/bu-venv, never inside the server's interpreter.

`browser_harvest.py` launches this file with that virtualenv's python (docs/124 R2).
Nothing in the server imports it, and it imports nothing from `app` — the two sides
share a command line and a line of JSON, which is the whole point of the separation.

Two settings here are not preferences. `headless=False` with `channel="chrome"`:
headless Chromium sat on Absen's Cloudflare Turnstile for five waits, a click and two
reloads and never got the page, while real Chrome passed it first try. `allowed_domains`
is the mechanical half of "only reads the target" — in the same probe the model went
looking for DuckDuckGo, Bing and Google when the page stalled, and was refused each
time.
"""
import argparse
import asyncio
import json
import os
import re
import sys

# browser-use logs at INFO through the root logger. Send anything the libraries print
# to stderr and keep the real stdout for the one line the caller parses. This must
# happen before browser_use is imported, so its handlers bind to the redirected stream.
_STDOUT = sys.stdout
sys.stdout = sys.stderr

KEY_ENV = "OUTREACH_BU_KEY"
INNER_TIMEOUT = 240            # below browser_harvest.RUN_TIMEOUT, so we stop ourselves

TASK = """Open {url}

This page lists companies — distributors, partners, resellers or exhibitors.
Collect the WEBSITE DOMAIN of every company listed. Expand, scroll or page through the
listing as needed to reach the rest of the list.

Rules:
- Only report a domain you actually saw on the page as that company's own website link.
- If a company has no website link shown, skip it. Do not derive a domain from a logo
  filename, an email address, or the company's name.
- Never log in, never submit a form, never send a message.

Return only JSON: {{"companies": [{{"domain": "example.com"}}]}}
"""


def _extract(text: str) -> list[dict]:
    """Pull the JSON object out of whatever the model wrapped it in."""
    for match in re.finditer(r"\{.*\}", text or "", re.S):
        try:
            payload = json.loads(match.group(0))
        except ValueError:
            continue
        companies = payload.get("companies")
        if isinstance(companies, list):
            return [c for c in companies if isinstance(c, dict)]
    return []


async def _harvest(args) -> list[dict]:
    from browser_use import Agent, BrowserProfile, ChatOpenAI

    llm = ChatOpenAI(
        model="deepseek-chat", base_url="https://api.deepseek.com",
        api_key=os.environ.get(KEY_ENV, ""), temperature=0,
        # deepseek answers a json_schema response_format with "This response_format type
        # is unavailable now", which browser-use reads as six failed steps in a row.
        dont_force_structured_output=True, add_schema_to_system_prompt=True)
    profile = BrowserProfile(
        headless=False, channel="chrome", user_data_dir=args.profile_dir,
        allowed_domains=args.allow or [])
    agent = Agent(task=TASK.format(url=args.url), llm=llm, browser_profile=profile,
                  use_vision=False, step_timeout=90)
    try:
        history = await asyncio.wait_for(agent.run(max_steps=args.max_steps),
                                         timeout=INNER_TIMEOUT)
        return _extract(history.final_result() or "")
    except asyncio.TimeoutError:
        # Whatever it had reached is still worth returning; a partial list is the
        # expected outcome of a step budget (docs/124 R6).
        return _extract(getattr(agent, "history", None) and
                        (agent.history.final_result() or "") or "")
    finally:
        try:
            await agent.browser_session.kill()
        except Exception:      # noqa: BLE001 — closing a dead browser is not an error
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--allow", action="append", default=[])
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--profile-dir", required=True)
    args = parser.parse_args()
    try:
        companies = asyncio.run(_harvest(args))
    except Exception as exc:  # noqa: BLE001 — the caller reads JSON, not a traceback
        print(f"browser harvest failed: {exc}", file=sys.stderr)
        companies = []
    print(json.dumps({"companies": companies[:args.limit]}), file=_STDOUT)


if __name__ == "__main__":
    main()
