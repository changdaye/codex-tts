from codex_tts.config import load_config


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
