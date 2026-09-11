"""Identify what owns the local web port before starting Uvicorn."""
from __future__ import annotations

import json
import socket
import time
from urllib import request

APP_ID = "mcvisual-outreach-tool"


def port_owner(host: str = "127.0.0.1", port: int = 8000, timeout: float = 1.0) -> str:
    """Return `free`, `outreach` or `other` without killing either process."""
    try:
        with request.urlopen(
            f"http://{host}:{port}/api/runtime/identity", timeout=timeout
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return "outreach" if payload.get("app") == APP_ID else "other"
    except Exception:  # noqa: BLE001 — an occupied non-HTTP port is checked below
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return "other"
        except OSError:
            return "free"


def wait_for_outreach(timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Wait for a newly spawned server, but never wait on a foreign listener."""
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        owner = port_owner()
        if owner == "outreach":
            return True
        if owner == "other" or time.monotonic() >= deadline:
            return False
        time.sleep(max(0.01, interval))
