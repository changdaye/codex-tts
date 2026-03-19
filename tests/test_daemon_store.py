from codex_tts.daemon_store import DaemonStore
from codex_tts.models import DaemonSettings


def test_daemon_store_returns_default_settings_when_file_missing(tmp_path):
    store = DaemonStore(tmp_path / "daemon-state.json")

    settings = store.load()

    assert settings == DaemonSettings()


def test_daemon_store_persists_global_enabled(tmp_path):
    store = DaemonStore(tmp_path / "daemon-state.json")
    settings = DaemonSettings(global_enabled=False, updated_at=456)

    store.save(settings)

    assert store.load() == settings
