"""Ordered background-cycle orchestration, separate from the FastAPI bootstrap."""
from __future__ import annotations

import time
import os
import threading
from collections.abc import Callable, Iterable

from app import runtime


DEADLINES = {
    "email_poll": 180,
    "social_scan": 300,
    "website_recheck": 600,
    "sequence_maintenance": 60,
    "email_send": 1200,
    "social_send": 900,
    "contact_names": 300,
    "agent": 900,
}


class _StageRun:
    def __init__(self, fn: Callable[[], object]):
        self._fn = fn
        self._done = threading.Event()
        self._result = None
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._target, daemon=True)

    @property
    def done(self) -> bool:
        return self._done.is_set()

    def start(self) -> None:
        self._thread.start()

    def _target(self) -> None:
        try:
            self._result = self._fn()
        except BaseException as exc:  # retained and re-raised in the scheduler thread
            self._error = exc
        finally:
            self._done.set()

    def result(self, timeout: float | None = None):
        if not self._done.wait(timeout):
            raise TimeoutError("stage deadline exceeded")
        if self._error is not None:
            raise self._error
        return self._result


_ACTIVE: dict[tuple[str, str], _StageRun] = {}
_ACTIVE_LOCK = threading.Lock()


def _stage(db_path: str, name: str, fn: Callable[[], object], deadline: float) -> dict:
    key = (os.path.abspath(db_path), name)
    with _ACTIVE_LOCK:
        running = _ACTIVE.get(key)
        if running is None:
            running = _StageRun(fn)
            _ACTIVE[key] = running
            running.start()
            fresh = True
        else:
            fresh = False

    if not fresh and not running.done:
        error = f"stalled: {name} still running after {deadline:g}s deadline; duplicate suppressed"
        runtime._capability_write(
            db_path, name, success=None, error=error, outcome="stalled")
        return {"ok": False, "status": "stalled", "error": error,
                "processed_count": 0}

    def collect():
        try:
            return running.result(deadline if fresh else 0)
        except TimeoutError:
            if running.done:
                raise
            return {"status": "stalled",
                    "error": f"stalled: {name} exceeded its {deadline:g}s deadline; still running"}

    result = runtime.run_capability(db_path, name, collect)
    if running.done:
        with _ACTIVE_LOCK:
            if _ACTIVE.get(key) is running:
                _ACTIVE.pop(key, None)
    return result


def run_cycle(db_path: str, stages: Iterable[tuple[str, Callable[[], object]]], *,
              deadlines: dict[str, float] | None = None) -> bool:
    limits = DEADLINES if deadlines is None else {**DEADLINES, **deadlines}
    results = [(name, _stage(db_path, name, run, max(0.001, limits.get(name, 300))))
               for name, run in stages]
    failed = [f"{name}: {result['error']}" for name, result in results if not result["ok"]]
    if failed:
        raise RuntimeError("background stages failed: " + ", ".join(failed))
    return True


def run_forever(db_path: str, cycle_fn: Callable[[], bool], *, poll_seconds: int,
                retry_seconds: int, sleep_fn: Callable[[float], None] = time.sleep) -> None:
    owner = runtime.owner_id("embedded")
    while True:
        try:
            result = runtime.run_leased_cycle(
                db_path, cycle_fn, owner=owner, mode="embedded", release_after=False)
        except Exception:  # noqa: BLE001 — transient runtime failure retries quickly
            delay = retry_seconds
        else:
            if not result["acquired"]:
                delay = retry_seconds
            elif result["cycle_ok"] and result["email_poll_ok"]:
                delay = poll_seconds
            else:
                delay = retry_seconds
        sleep_fn(delay)
