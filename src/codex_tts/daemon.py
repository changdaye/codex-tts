from dataclasses import asdict
import errno
import os
from pathlib import Path
import time

from codex_tts.config import AppConfig
from codex_tts.daemon_store import DaemonStore
from codex_tts.diagnostics import DebugLogger
from codex_tts.ipc import JsonSocketServer
from codex_tts.models import DaemonSettings
from codex_tts.rollout import FinalAnswerWatcher
from codex_tts.service import emit_speech_for_event
from codex_tts.session_manager import SessionManager
from codex_tts.session_store import resolve_active_thread
from codex_tts.speech_policy import SpeechPolicy
from codex_tts.speech_text import sanitize_for_speech


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
        self._known_thread_ids: dict[str, set[str]] = {}
        self._watchers: dict[str, FinalAnswerWatcher] = {}
        self._policies: dict[str, SpeechPolicy] = {}

    def handle_request(self, request: dict[str, object]) -> dict[str, object]:
        command = request.get("command")
        try:
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
                self._known_thread_ids[session.session_id] = {
                    str(thread_id) for thread_id in request.get("known_thread_ids", [])
                }
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
        except (KeyError, TypeError, ValueError) as exc:
            return {"ok": False, "error": _error_message(exc)}

        return {"ok": False, "error": f"unknown command: {command}"}

    def serve_forever(self, *, poll_interval: float = 0.1) -> None:
        self.server.start()
        self._running = True
        try:
            while self._running:
                self.server.handle_next_request(timeout=poll_interval)
                self.poll_sessions()
        finally:
            self.server.close()

    def stop(self) -> None:
        self._running = False

    def _snapshot_payload(self) -> dict[str, object]:
        snapshot = asdict(self.session_manager.status_snapshot())
        snapshot["snapshot_version"] = 1
        return snapshot

    def poll_sessions(self) -> None:
        pending_sessions = sorted(
            self.session_manager.status_snapshot().sessions,
            key=lambda session: (session.started_at, session.session_id),
        )
        for session in pending_sessions:
            if session.status == "pending_bind":
                self._attempt_bind(session.session_id)

        for session in self.session_manager.status_snapshot().sessions:
            if session.status == "active":
                self._poll_active_session(session.session_id)
            if session.codex_pid and not _process_exists(session.codex_pid):
                self.session_manager.mark_session_exited(session.session_id)
                self._watchers.pop(session.session_id, None)
                self._policies.pop(session.session_id, None)

    def _attempt_bind(self, session_id: str) -> None:
        snapshot = next(
            (
                session
                for session in self.session_manager.status_snapshot().sessions
                if session.session_id == session_id
            ),
            None,
        )
        if snapshot is None:
            return

        thread = resolve_active_thread(
            self.state_db,
            cwd=snapshot.cwd,
            started_at=snapshot.started_at,
            known_thread_ids=self._known_thread_ids.get(session_id, set()),
            logger=self.logger,
        )
        if thread is None:
            return

        self.session_manager.bind_session(
            session_id,
            thread_id=thread.thread_id,
            rollout_path=thread.rollout_path,
        )
        self._watchers[session_id] = FinalAnswerWatcher(thread.rollout_path)
        self._policies[session_id] = SpeechPolicy()

    def _poll_active_session(self, session_id: str) -> None:
        watcher = self._watchers.get(session_id)
        policy = self._policies.get(session_id)
        if watcher is None or policy is None:
            return

        for event in watcher.poll():
            sanitized_text = sanitize_for_speech(event.text)
            if sanitized_text:
                self.session_manager.record_final_text(
                    session_id,
                    text=sanitized_text,
                    event_at=int(time.time()),
                )
            emit_speech_for_event(
                event,
                policy=policy,
                config=self.config,
                logger=self.logger,
                speech_enabled=self.session_manager.should_speak(session_id),
            )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def _error_message(exc: Exception) -> str:
    if exc.args:
        return str(exc.args[0])
    return str(exc)
