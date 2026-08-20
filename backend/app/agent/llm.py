"""Model access for the sales agent: three backends, routed per task.

Why per task and not one global switch (Spec 22 section 8): classification is the
high-volume, low-difficulty job — running it on Allen's Claude Code subscription would
eat the quota he needs for his own work, and an eight-way choice does not need a
frontier model. Drafting is the opposite: small volume, free inside the subscription he
already pays for, and the only output a real customer ever reads. "Never invent a price
or a lead time" is a negative constraint, which is exactly where instruction-following
quality decides whether a fabricated delivery date reaches a customer.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

from app import settings

BACKENDS = ("cli", "deepseek", "api")
TASKS = ("classify", "draft")

_DEFAULT_BACKEND = {"classify": "deepseek", "draft": "cli"}
_K_BACKEND = "agent_llm_backend_%s"
_K_CALLS = "agent_call_stats"
_K_CLI_LIMIT = "agent_daily_call_limit"

CLI_DAILY_LIMIT = 200          # protects Allen's own Claude Code quota
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

_KEY_FILES = {
    "deepseek": "deepseek_key.txt",
    "api": "agent_key.txt",
}


class LLMUnavailable(RuntimeError):
    """No usable backend for this task — callers stay silent rather than guess."""


class LLMError(RuntimeError):
    """The backend was reachable but the call failed."""


def _backend_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_key(backend: str) -> str:
    name = _KEY_FILES.get(backend)
    if not name:
        return ""
    try:
        with open(os.path.join(_backend_dir(), name), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def cli_available() -> bool:
    """Usable only when installed AND still logged in. A silent credential expiry is
    the failure mode worth naming loudly, so this checks credentials, not just PATH."""
    from shutil import which
    if not which("claude"):
        return False
    return os.path.exists(os.path.expanduser("~/.claude/.credentials.json"))


def available(backend: str) -> bool:
    if backend == "cli":
        return cli_available()
    return bool(read_key(backend))


def backend_for(conn, task: str) -> str:
    return settings.get(conn, _K_BACKEND % task, _DEFAULT_BACKEND.get(task, "cli"))


def set_backend(conn, task: str, backend: str) -> None:
    if task not in TASKS or backend not in BACKENDS:
        raise ValueError("unknown task or backend")
    settings.set_value(conn, _K_BACKEND % task, backend)


# ---------------------------------------------------------------- call accounting

def _stats(conn) -> dict:
    today = dt.date.today().isoformat()
    try:
        data = json.loads(settings.get(conn, _K_CALLS) or "{}")
    except json.JSONDecodeError:
        data = {}
    if data.get("date") != today:
        data = {"date": today}
    return data


def cli_limit(conn) -> int:
    try:
        return int(settings.get(conn, _K_CLI_LIMIT) or CLI_DAILY_LIMIT)
    except ValueError:
        return CLI_DAILY_LIMIT


def call_stats(conn) -> dict:
    data = _stats(conn)
    data["cli_limit"] = cli_limit(conn)
    return data


def _record(conn, backend: str) -> None:
    data = _stats(conn)
    data[backend] = int(data.get(backend, 0)) + 1
    settings.set_value(conn, _K_CALLS, json.dumps(data))


# ---------------------------------------------------------------- JSON extraction

_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.S)


def extract_json(text: str) -> dict:
    """Models wrap JSON in prose or fences often enough that a bare json.loads would
    make the agent look broken when the answer was right there."""
    raw = (text or "").strip()
    if not raw:
        raise LLMError("模型返回空内容")
    m = _FENCE.search(raw)
    if m:
        raw = m.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"模型返回的不是 JSON：{raw[:160]}") from exc
    raise LLMError(f"模型返回的不是 JSON：{raw[:160]}")


# ---------------------------------------------------------------- backends

def _post_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise LLMError(f"HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LLMError(f"网络不可达：{exc}") from exc


def _call_deepseek(system: str, user: str, timeout: int) -> str:
    key = read_key("deepseek")
    if not key:
        raise LLMUnavailable("缺少 backend/deepseek_key.txt")
    data = _post_json(DEEPSEEK_URL, {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }, {"Authorization": f"Bearer {key}"}, timeout)
    return data["choices"][0]["message"]["content"]


def _call_api(system: str, user: str, timeout: int, model: str) -> str:
    key = read_key("api")
    if not key:
        raise LLMUnavailable("缺少 backend/agent_key.txt")
    data = _post_json(ANTHROPIC_URL, {
        "model": model,
        "max_tokens": 2000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }, {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout)
    return "".join(b.get("text", "") for b in data.get("content", []))


def _call_cli(system: str, user: str, timeout: int, model: str) -> str:
    """Headless Claude Code, reusing the subscription login. MCP servers are stripped:
    the agent needs a text answer, and every extra tool definition is prompt overhead
    charged against the same quota."""
    if not cli_available():
        raise LLMUnavailable("Claude Code CLI 不可用或登录已过期")
    cmd = ["claude", "-p", user, "--output-format", "json", "--model", model,
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--append-system-prompt", system]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        raise LLMError(f"CLI 调用超时（{timeout}s）") from exc
    if proc.returncode != 0:
        raise LLMError(f"CLI 退出码 {proc.returncode}：{(proc.stderr or '')[:200]}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise LLMError(f"CLI 输出不是 JSON：{proc.stdout[:200]}") from exc
    if payload.get("is_error"):
        raise LLMError(f"CLI 报错：{str(payload.get('result'))[:200]}")
    return payload.get("result") or ""


_CLI_MODEL = {"classify": "haiku", "draft": "opus"}
_API_MODEL = {"classify": "claude-haiku-4-5-20251001", "draft": "claude-opus-5"}


def _call_backend(conn, backend: str, task: str, system: str, user: str,
                  timeout: int) -> str:
    if backend == "cli":
        if _stats(conn).get("cli", 0) >= cli_limit(conn):
            raise LLMUnavailable(
                f"今日 Claude Code 调用已达上限 {cli_limit(conn)} 次，明天恢复")
        return _call_cli(system, user, timeout, _CLI_MODEL.get(task, "opus"))
    if backend == "deepseek":
        return _call_deepseek(system, user, timeout)
    if backend == "api":
        return _call_api(system, user, timeout, _API_MODEL.get(task, "claude-opus-5"))
    raise LLMUnavailable(f"未知后端 {backend}")


def _backend_chain(task: str, primary: str) -> list[str]:
    # Classification must not silently consume Allen's Claude Code subscription. Draft
    # and planning prefer Claude, but DeepSeek keeps replies moving during its reset
    # windows. Explicitly configured primaries always stay first.
    order = ("cli", "deepseek", "api") if task == "draft" else ("deepseek", "api")
    return list(dict.fromkeys((primary, *order)))


def complete_json(conn, task: str, system: str, user: str, timeout: int = 180) -> dict:
    """Run one task on its configured backend and return parsed JSON.

    LLMUnavailable = not set up, caller stays silent. LLMError = the call failed,
    caller surfaces the reason.
    """
    if task not in TASKS:
        raise ValueError(f"unknown task {task}")
    primary = backend_for(conn, task)
    failures: list[tuple[str, Exception]] = []
    for index, backend in enumerate(_backend_chain(task, primary)):
        if index and not available(backend):
            continue
        try:
            data = extract_json(_call_backend(conn, backend, task, system, user, timeout))
        except (LLMUnavailable, LLMError) as exc:
            failures.append((backend, exc))
            continue
        _record(conn, backend)
        data["_llm_backend"] = backend
        if backend != primary:
            data["_llm_fallback_from"] = primary
        return data
    detail = "；".join(f"{backend}: {exc}" for backend, exc in failures)
    if failures and all(isinstance(exc, LLMUnavailable) for _, exc in failures):
        raise LLMUnavailable(detail)
    raise LLMError(detail or f"没有可用的 {task} 模型后端")


def status(conn) -> dict:
    """For the readiness centre: which task can run right now, and why not."""
    out = {"calls": call_stats(conn), "tasks": {}}
    for task in TASKS:
        backend = backend_for(conn, task)
        ok = available(backend)
        reason = ""
        if not ok:
            reason = ("Claude Code 未安装或登录已过期，请在终端运行 claude 重新登录"
                      if backend == "cli"
                      else f"缺少 backend/{_KEY_FILES.get(backend, '?')}")
        fallbacks = [item for item in _backend_chain(task, backend)[1:] if available(item)]
        out["tasks"][task] = {"backend": backend, "ok": ok, "reason": reason,
                              "fallbacks": fallbacks}
    return out
