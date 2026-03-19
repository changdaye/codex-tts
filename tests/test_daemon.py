import sqlite3
from pathlib import Path
import subprocess
import sys
import threading
import time

from codex_tts.config import AppConfig
from codex_tts.daemon import CodexTTSDaemon
from codex_tts.ipc import call_daemon


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


def test_daemon_ping_and_unknown_command_responses(tmp_path):
    state_db = tmp_path / "state.sqlite"
    create_threads_db(state_db)
    daemon = CodexTTSDaemon(
        config=AppConfig(),
        state_db=state_db,
        socket_path=tmp_path / "daemon.sock",
        settings_path=tmp_path / "daemon-state.json",
    )

    assert daemon.handle_request({"command": "ping"}) == {"ok": True}
    assert daemon.handle_request({"command": "mystery"}) == {
        "ok": False,
        "error": "unknown command: mystery",
    }


def test_daemon_can_mute_unmute_clear_focus_and_toggle_global_enabled(tmp_path, monkeypatch):
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
    daemon.handle_request({"command": "set_focus", "session_id": "session-1"})
    monkeypatch.setattr("codex_tts.daemon.time.time", lambda: 456)

    muted = daemon.handle_request({"command": "mute_session", "session_id": "session-1"})
    unmuted = daemon.handle_request({"command": "unmute_session", "session_id": "session-1"})
    disabled = daemon.handle_request({"command": "set_global_enabled", "enabled": False})
    cleared = daemon.handle_request({"command": "set_focus"})

    assert muted["session"]["is_muted"] is True
    assert unmuted["session"]["is_muted"] is False
    assert disabled["snapshot"]["global_enabled"] is False
    assert cleared["snapshot"]["focus_session_id"] is None
    assert daemon.store.load().global_enabled is False
    assert daemon.store.load().updated_at == 456


def test_daemon_ignores_missing_bind_target_and_missing_active_watcher(tmp_path):
    state_db = tmp_path / "state.sqlite"
    create_threads_db(state_db)
    daemon = CodexTTSDaemon(
        config=AppConfig(),
        state_db=state_db,
        socket_path=tmp_path / "daemon.sock",
        settings_path=tmp_path / "daemon-state.json",
    )
    daemon.session_manager.register_launch(
        session_id="session-1",
        cwd=str(tmp_path / "workspace"),
        started_at=100,
    )
    daemon.session_manager.bind_session(
        "session-1",
        thread_id="thread-1",
        rollout_path=tmp_path / "thread-1.jsonl",
    )

    daemon._attempt_bind("missing")
    daemon._poll_active_session("session-1")

    assert daemon.session_manager.status_snapshot().sessions[0].session_id == "session-1"


def test_daemon_tracks_two_sessions_but_only_speaks_focused_one(tmp_path, monkeypatch):
    state_db = tmp_path / "state.sqlite"
    create_threads_db(state_db)
    spoken: list[str] = []
    daemon = CodexTTSDaemon(
        config=AppConfig(),
        state_db=state_db,
        socket_path=tmp_path / "daemon.sock",
        settings_path=tmp_path / "daemon-state.json",
    )
    monkeypatch.setattr("codex_tts.service.speak_text", lambda text, config: spoken.append(text))

    worker = threading.Thread(target=daemon.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    fake_script = Path(__file__).parent / "fixtures" / "fake_codex.py"
    started_at_one = int(time.time())

    process_one = subprocess.Popen(
        [
            sys.executable,
            str(fake_script),
                str(state_db),
                str(tmp_path / "one.jsonl"),
                str(tmp_path / "workspace-one"),
                "thread-1",
                '[{"delay": 0.20, "text": "first reply"}]',
            ]
        )
    started_at_two = int(time.time())
    process_two = subprocess.Popen(
        [
            sys.executable,
            str(fake_script),
                str(state_db),
                str(tmp_path / "two.jsonl"),
                str(tmp_path / "workspace-two"),
                "thread-2",
                '[{"delay": 0.40, "text": "second reply"}]',
            ]
        )

    try:
        call_daemon(
            tmp_path / "daemon.sock",
                {
                    "command": "register_launch",
                    "session_id": "session-1",
                    "cwd": str(tmp_path / "workspace-one"),
                    "started_at": started_at_one,
                    "codex_pid": process_one.pid,
                    "known_thread_ids": [],
                },
            )
        call_daemon(
            tmp_path / "daemon.sock",
                {
                    "command": "register_launch",
                    "session_id": "session-2",
                    "cwd": str(tmp_path / "workspace-two"),
                    "started_at": started_at_two,
                    "codex_pid": process_two.pid,
                    "known_thread_ids": [],
                },
            )

        assert process_one.wait(timeout=5) == 0
        assert process_two.wait(timeout=5) == 0

        deadline = time.time() + 2
        while time.time() < deadline and spoken != ["first reply"]:
            time.sleep(0.02)
    finally:
        daemon.stop()
        worker.join(timeout=2)

    assert spoken == ["first reply"]


def test_focus_change_allows_new_session_to_speak(tmp_path, monkeypatch):
    state_db = tmp_path / "state.sqlite"
    create_threads_db(state_db)
    spoken: list[str] = []
    daemon = CodexTTSDaemon(
        config=AppConfig(),
        state_db=state_db,
        socket_path=tmp_path / "daemon.sock",
        settings_path=tmp_path / "daemon-state.json",
    )
    monkeypatch.setattr("codex_tts.service.speak_text", lambda text, config: spoken.append(text))

    worker = threading.Thread(target=daemon.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    fake_script = Path(__file__).parent / "fixtures" / "fake_codex.py"
    started_at_one = int(time.time())

    process_one = subprocess.Popen(
        [
            sys.executable,
            str(fake_script),
                str(state_db),
                str(tmp_path / "one.jsonl"),
                str(tmp_path / "workspace-one"),
                "thread-1",
                '[{"delay": 0.20, "text": "first reply"}]',
            ]
        )
    started_at_two = int(time.time())
    process_two = subprocess.Popen(
        [
            sys.executable,
            str(fake_script),
                str(state_db),
                str(tmp_path / "two.jsonl"),
                str(tmp_path / "workspace-two"),
                "thread-2",
                '[{"delay": 0.50, "text": "second reply"}]',
            ]
        )

    try:
        call_daemon(
            tmp_path / "daemon.sock",
                {
                    "command": "register_launch",
                    "session_id": "session-1",
                    "cwd": str(tmp_path / "workspace-one"),
                    "started_at": started_at_one,
                    "codex_pid": process_one.pid,
                    "known_thread_ids": [],
                },
            )
        call_daemon(
            tmp_path / "daemon.sock",
                {
                    "command": "register_launch",
                    "session_id": "session-2",
                    "cwd": str(tmp_path / "workspace-two"),
                    "started_at": started_at_two,
                    "codex_pid": process_two.pid,
                    "known_thread_ids": [],
                },
            )

        deadline = time.time() + 2
        while time.time() < deadline and spoken != ["first reply"]:
            time.sleep(0.02)

        call_daemon(
            tmp_path / "daemon.sock",
            {
                "command": "set_focus",
                "session_id": "session-2",
            },
        )

        assert process_one.wait(timeout=5) == 0
        assert process_two.wait(timeout=5) == 0

        deadline = time.time() + 2
        while time.time() < deadline and spoken != ["first reply", "second reply"]:
            time.sleep(0.02)
    finally:
        daemon.stop()
        worker.join(timeout=2)

    assert spoken == ["first reply", "second reply"]
