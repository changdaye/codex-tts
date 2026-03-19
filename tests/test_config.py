from codex_tts.config import load_config


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    config = load_config(tmp_path / "missing.toml")
    assert config.backend == "say"
    assert config.voice == "Tingting"
    assert config.rate == 180
    assert config.speak_phase == "final_only"
