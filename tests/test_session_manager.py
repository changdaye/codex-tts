from pathlib import Path

import pytest

from codex_tts.session_manager import SessionManager


def test_first_active_session_auto_focuses(tmp_path):
    manager = SessionManager()
    manager.register_launch(session_id="session-1", cwd=str(tmp_path / "one"), started_at=100)

    session = manager.bind_session(
        "session-1",
        thread_id="thread-1",
        rollout_path=tmp_path / "one.jsonl",
    )

    assert session.is_focus is True
    assert manager.status_snapshot().focus_session_id == "session-1"


def test_new_active_session_does_not_steal_focus(tmp_path):
    manager = SessionManager()
    manager.register_launch(session_id="session-1", cwd=str(tmp_path / "one"), started_at=100)
    manager.bind_session("session-1", thread_id="thread-1", rollout_path=tmp_path / "one.jsonl")

    manager.register_launch(session_id="session-2", cwd=str(tmp_path / "two"), started_at=101)
    session = manager.bind_session(
        "session-2",
        thread_id="thread-2",
        rollout_path=tmp_path / "two.jsonl",
    )

    assert session.is_focus is False
    assert manager.status_snapshot().focus_session_id == "session-1"


def test_exiting_focus_clears_focus_without_reassigning(tmp_path):
    manager = SessionManager()
    manager.register_launch(session_id="session-1", cwd=str(tmp_path / "one"), started_at=100)
    manager.bind_session("session-1", thread_id="thread-1", rollout_path=tmp_path / "one.jsonl")
    manager.register_launch(session_id="session-2", cwd=str(tmp_path / "two"), started_at=101)
    manager.bind_session("session-2", thread_id="thread-2", rollout_path=tmp_path / "two.jsonl")

    session = manager.mark_session_exited("session-1")
    snapshot = manager.status_snapshot()

    assert session.status == "exited"
    assert session.is_focus is False
    assert snapshot.focus_session_id is None
    assert [item.session_id for item in snapshot.sessions if item.is_focus] == []


def test_only_focused_session_is_allowed_to_speak(tmp_path):
    manager = SessionManager()
    manager.register_launch(session_id="session-1", cwd=str(tmp_path / "one"), started_at=100)
    manager.bind_session("session-1", thread_id="thread-1", rollout_path=tmp_path / "one.jsonl")
    manager.register_launch(session_id="session-2", cwd=str(tmp_path / "two"), started_at=101)
    manager.bind_session("session-2", thread_id="thread-2", rollout_path=tmp_path / "two.jsonl")

    assert manager.should_speak("session-1") is True
    assert manager.should_speak("session-2") is False


def test_muted_session_cannot_speak_even_when_focused(tmp_path):
    manager = SessionManager()
    manager.register_launch(session_id="session-1", cwd=str(tmp_path / "one"), started_at=100)
    manager.bind_session("session-1", thread_id="thread-1", rollout_path=tmp_path / "one.jsonl")

    manager.set_muted("session-1", muted=True)

    assert manager.should_speak("session-1") is False


def test_focus_can_be_cleared_explicitly(tmp_path):
    manager = SessionManager()
    manager.register_launch(session_id="session-1", cwd=str(tmp_path / "one"), started_at=100)
    manager.bind_session("session-1", thread_id="thread-1", rollout_path=tmp_path / "one.jsonl")

    cleared = manager.set_focus(None)

    assert cleared is None
    assert manager.status_snapshot().focus_session_id is None


def test_global_disable_prevents_speech_for_focused_session(tmp_path):
    manager = SessionManager()
    manager.register_launch(session_id="session-1", cwd=str(tmp_path / "one"), started_at=100)
    manager.bind_session("session-1", thread_id="thread-1", rollout_path=tmp_path / "one.jsonl")

    manager.set_global_enabled(False)

    assert manager.should_speak("session-1") is False


def test_unknown_session_never_speaks():
    manager = SessionManager()

    assert manager.should_speak("missing") is False


def test_muting_unknown_session_raises_clear_error():
    manager = SessionManager()

    with pytest.raises(KeyError, match="unknown session: missing"):
        manager.set_muted("missing", muted=True)
