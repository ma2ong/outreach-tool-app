from typing import Protocol

CHANNELS = {"whatsapp", "instagram", "facebook"}


class BrowserEngine(Protocol):
    def status(self, channel: str) -> str: ...
    def connect(self, channel: str) -> None: ...
    def qr_png(self, channel: str) -> bytes | None: ...
    def send_message(self, channel: str, target: str, message: str, image: str | None = None) -> None: ...
    def scan_threads(self, channel: str) -> list[dict]: ...


class FakeEngine:
    """In-memory engine for tests. Status: disconnected -> connecting -> connected."""

    def __init__(self):
        self._state: dict[str, str] = {}
        self.sent: list[tuple[str, str, str, str | None]] = []  # (channel, target, message, image)
        self.fail_targets: set[str] = set()
        self.threads: dict[str, list[dict]] = {}

    def status(self, channel: str) -> str:
        return self._state.get(channel, "disconnected")

    def connect(self, channel: str) -> None:
        if self._state.get(channel) != "connected":
            self._state[channel] = "connecting"

    def simulate_login(self, channel: str) -> None:
        self._state[channel] = "connected"

    def qr_png(self, channel: str) -> bytes | None:
        return b"FAKEPNG" if self._state.get(channel) == "connecting" else None

    def send_message(self, channel: str, target: str, message: str, image: str | None = None) -> None:
        if target in self.fail_targets:
            raise RuntimeError(f"send failed for {target}")
        self.sent.append((channel, target, message, image))

    def scan_threads(self, channel: str) -> list[dict]:
        return self.threads.get(channel, [])
