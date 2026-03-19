from dataclasses import asdict
from pathlib import Path
import time

from codex_tts.config import AppConfig
from codex_tts.daemon_store import DaemonStore
from codex_tts.diagnostics import DebugLogger
from codex_tts.ipc import JsonSocketServer
from codex_tts.models import DaemonSettings
from codex_tts.session_manager import SessionManager


class CodexTTSDaemon:
    def __init__(
        self,
        *,
        config: AppConfig,
        state_db: Path,
        socket_path: Path,
        settings_path: Path,
    ) -> None:
        self.config = config
        self.state_db = state_db
        self.socket_path = socket_path
        self.store = DaemonStore(settings_path)
        self.logger = DebugLogger(enabled=config.verbose)
        settings = self.store.load()
        self.session_manager = SessionManager(global_enabled=settings.global_enabled)
        self.server = JsonSocketServer(socket_path, handler=self.handle_request)
        self._running = False

    def handle_request(self, request: dict[str, object]) -> dict[str, object]:
        command = request.get("command")

        if command == "ping":
            return {"ok": True}

        if command == "register_launch":
            session = self.session_manager.register_launch(
                session_id=str(request["session_id"]),
                cwd=str(request["cwd"]),
                started_at=int(request["started_at"]),
                launcher_pid=_optional_int(request.get("launcher_pid")),
                codex_pid=_optional_int(request.get("codex_pid")),
            )
            return {
                "ok": True,
                "session": asdict(session),
                "snapshot": self._snapshot_payload(),
            }

        if command == "status":
            return {"ok": True, "snapshot": self._snapshot_payload()}

        if command == "set_focus":
            self.session_manager.set_focus(_optional_str(request.get("session_id")))
            return {"ok": True, "snapshot": self._snapshot_payload()}

        if command == "mute_session":
            session = self.session_manager.set_muted(str(request["session_id"]), muted=True)
            return {"ok": True, "session": asdict(session), "snapshot": self._snapshot_payload()}

        if command == "unmute_session":
            session = self.session_manager.set_muted(str(request["session_id"]), muted=False)
            return {"ok": True, "session": asdict(session), "snapshot": self._snapshot_payload()}

        if command == "set_global_enabled":
            enabled = bool(request["enabled"])
            self.session_manager.set_global_enabled(enabled)
            self.store.save(DaemonSettings(global_enabled=enabled, updated_at=int(time.time())))
            return {"ok": True, "snapshot": self._snapshot_payload()}

        return {"ok": False, "error": f"unknown command: {command}"}

    def serve_forever(self, *, poll_interval: float = 0.1) -> None:
        self.server.start()
        self._running = True
        try:
            while self._running:
                self.server.handle_next_request(timeout=poll_interval)
        finally:
            self.server.close()

    def stop(self) -> None:
        self._running = False

    def _snapshot_payload(self) -> dict[str, object]:
        snapshot = asdict(self.session_manager.status_snapshot())
        snapshot["snapshot_version"] = 1
        return snapshot


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
