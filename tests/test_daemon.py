import sqlite3
from pathlib import Path

from codex_tts.config import AppConfig
from codex_tts.daemon import CodexTTSDaemon


def create_threads_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        create table threads (
            id text primary key,
            rollout_path text not null,
            created_at integer not null,
            updated_at integer not null,
            cwd text not null
        )
        """
    )
    conn.commit()
    conn.close()


def test_daemon_status_reports_registered_session(tmp_path):
    state_db = tmp_path / "state.sqlite"
    create_threads_db(state_db)
    daemon = CodexTTSDaemon(
        config=AppConfig(),
        state_db=state_db,
        socket_path=tmp_path / "daemon.sock",
        settings_path=tmp_path / "daemon-state.json",
    )

    register = daemon.handle_request(
        {
            "command": "register_launch",
            "session_id": "session-1",
            "cwd": str(tmp_path / "workspace"),
            "started_at": 100,
            "known_thread_ids": [],
        }
    )
    status = daemon.handle_request({"command": "status"})

    assert register["ok"] is True
    assert status["ok"] is True
    assert status["snapshot"]["sessions"][0]["session_id"] == "session-1"
    assert status["snapshot"]["snapshot_version"] == 1


def test_daemon_set_focus_updates_snapshot(tmp_path):
    state_db = tmp_path / "state.sqlite"
    create_threads_db(state_db)
    daemon = CodexTTSDaemon(
        config=AppConfig(),
        state_db=state_db,
        socket_path=tmp_path / "daemon.sock",
        settings_path=tmp_path / "daemon-state.json",
    )
    daemon.handle_request(
        {
            "command": "register_launch",
            "session_id": "session-1",
            "cwd": str(tmp_path / "workspace"),
            "started_at": 100,
            "known_thread_ids": [],
        }
    )

    response = daemon.handle_request({"command": "set_focus", "session_id": "session-1"})

    assert response["ok"] is True
    assert response["snapshot"]["focus_session_id"] == "session-1"
