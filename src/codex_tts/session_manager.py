from dataclasses import replace
from pathlib import Path

from codex_tts.models import DaemonStatusSnapshot, ManagedSessionSnapshot


class SessionManager:
    def __init__(self, *, global_enabled: bool = True) -> None:
        self._global_enabled = global_enabled
        self._focus_session_id: str | None = None
        self._sessions: dict[str, ManagedSessionSnapshot] = {}

    def register_launch(
        self,
        *,
        session_id: str,
        cwd: str,
        started_at: int,
        launcher_pid: int | None = None,
        codex_pid: int | None = None,
    ) -> ManagedSessionSnapshot:
        session = ManagedSessionSnapshot(
            session_id=session_id,
            cwd=cwd,
            started_at=started_at,
            launcher_pid=launcher_pid,
            codex_pid=codex_pid,
        )
        self._sessions[session_id] = session
        return session

    def bind_session(
        self,
        session_id: str,
        *,
        thread_id: str,
        rollout_path: Path,
    ) -> ManagedSessionSnapshot:
        session = self._require_session(session_id)
        session = replace(
            session,
            status="active",
            thread_id=thread_id,
            rollout_path=str(rollout_path),
        )
        self._sessions[session_id] = session
        if self._focus_session_id is None:
            return self.set_focus(session_id)
        return session

    def set_focus(self, session_id: str | None) -> ManagedSessionSnapshot | None:
        current_focus = self._focus_session_id
        if current_focus is not None and current_focus in self._sessions:
            self._sessions[current_focus] = replace(self._sessions[current_focus], is_focus=False)

        self._focus_session_id = None
        if session_id is None:
            return None

        session = self._require_session(session_id)
        session = replace(session, is_focus=True)
        self._sessions[session_id] = session
        self._focus_session_id = session_id
        return session

    def set_muted(self, session_id: str, *, muted: bool) -> ManagedSessionSnapshot:
        session = self._require_session(session_id)
        session = replace(session, is_muted=muted)
        self._sessions[session_id] = session
        return session

    def set_global_enabled(self, enabled: bool) -> None:
        self._global_enabled = enabled

    def mark_session_exited(self, session_id: str) -> ManagedSessionSnapshot:
        session = self._require_session(session_id)
        session = replace(session, status="exited", is_focus=False)
        self._sessions[session_id] = session
        if self._focus_session_id == session_id:
            self._focus_session_id = None
        return session

    def should_speak(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        return (
            self._global_enabled
            and session.status == "active"
            and session.is_focus
            and not session.is_muted
        )

    def status_snapshot(self) -> DaemonStatusSnapshot:
        sessions = sorted(
            self._sessions.values(),
            key=lambda session: (session.last_event_at or session.started_at, session.session_id),
            reverse=True,
        )
        return DaemonStatusSnapshot(
            global_enabled=self._global_enabled,
            focus_session_id=self._focus_session_id,
            sessions=sessions,
        )

    def _require_session(self, session_id: str) -> ManagedSessionSnapshot:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"unknown session: {session_id}") from exc
