from pathlib import Path

from codex_tts.config import daemon_root_path, daemon_socket_path, daemon_state_path, load_config
from codex_tts.models import DaemonSettings, DaemonStatusSnapshot, ManagedSessionSnapshot


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    config = load_config(tmp_path / "missing.toml")
    assert config.backend == "say"
    assert config.voice == "Tingting"
    assert config.rate == 180
    assert config.speak_phase == "final_only"


def test_load_config_rejects_unknown_backend(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('backend = "other"\n', encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "backend must be one of: say"
    else:
        raise AssertionError("expected load_config to reject an unknown backend")


def test_load_config_rejects_non_positive_rate(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("rate = 0\n", encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "rate must be greater than 0"
    else:
        raise AssertionError("expected load_config to reject a non-positive rate")


def test_load_config_rejects_boolean_rate(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("rate = true\n", encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "rate must be greater than 0"
    else:
        raise AssertionError("expected load_config to reject a boolean rate")


def test_load_config_rejects_non_numeric_rate(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('rate = "fast"\n', encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "rate must be greater than 0"
    else:
        raise AssertionError("expected load_config to reject a non-numeric rate")


def test_load_config_rejects_empty_voice(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('voice = "   "\n', encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "voice must not be empty"
    else:
        raise AssertionError("expected load_config to reject an empty voice")


def test_load_config_rejects_unsupported_speak_phase(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('speak_phase = "commentary"\n', encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "speak_phase must be one of: final_only"
    else:
        raise AssertionError("expected load_config to reject an unsupported speak_phase")


def test_load_config_rejects_non_string_backend(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("backend = 3\n", encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "backend must not be empty"
    else:
        raise AssertionError("expected load_config to reject a non-string backend")


def test_load_config_rejects_non_boolean_verbose(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('verbose = "yes"\n', encoding="utf-8")

    try:
        load_config(config_path)
    except ValueError as exc:
        assert str(exc) == "verbose must be true or false"
    else:
        raise AssertionError("expected load_config to reject a non-boolean verbose flag")


def test_load_config_normalizes_voice_and_verbose_flag(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('voice = " Tingting "\nverbose = true\n', encoding="utf-8")

    config = load_config(config_path)

    assert config.voice == "Tingting"
    assert config.verbose is True


def test_daemon_root_and_paths_default_under_codex_tts_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert daemon_root_path() == tmp_path / ".codex-tts"
    assert daemon_socket_path() == tmp_path / ".codex-tts" / "daemon.sock"
    assert daemon_state_path() == tmp_path / ".codex-tts" / "daemon-state.json"


def test_daemon_status_snapshot_defaults_to_enabled_with_no_sessions():
    snapshot = DaemonStatusSnapshot()

    assert snapshot.global_enabled is True
    assert snapshot.sessions == []
    assert snapshot.focus_session_id is None


def test_managed_session_snapshot_defaults_are_unfocused_and_unmuted(tmp_path):
    session = ManagedSessionSnapshot(
        session_id="session-1",
        cwd=str(tmp_path),
        started_at=123,
    )

    assert session.status == "pending_bind"
    assert session.is_focus is False
    assert session.is_muted is False
    assert session.thread_id is None
    assert session.rollout_path is None


def test_daemon_settings_defaults_to_global_enabled():
    settings = DaemonSettings()

    assert settings.global_enabled is True
    assert settings.updated_at is None
