from types import SimpleNamespace

import pytest

from codex_tts.tts import build_backend, list_voices
from codex_tts.tts.base import TTSBackend
from codex_tts.tts.say import SayBackend


def test_tts_backend_protocol_is_importable():
    assert TTSBackend.__name__ == "TTSBackend"


def test_build_backend_rejects_unsupported_backend():
    with pytest.raises(ValueError, match="Unsupported backend: other"):
        build_backend("other")


def test_list_voices_delegates_to_backend(monkeypatch):
    monkeypatch.setattr(SayBackend, "list_voices", lambda self: ["Tingting", "Mei-Jia"])

    assert list_voices("say") == ["Tingting", "Mei-Jia"]


def test_say_backend_speak_invokes_system_say(monkeypatch):
    captured = {}

    def fake_run(command, check):
        captured["command"] = command
        captured["check"] = check
        return SimpleNamespace()

    monkeypatch.setattr("codex_tts.tts.say.run", fake_run)

    SayBackend().speak("hello", voice="Tingting", rate=220)

    assert captured == {
        "command": ["say", "-v", "Tingting", "-r", "220", "hello"],
        "check": True,
    }


def test_say_backend_list_voices_parses_non_empty_lines(monkeypatch):
    def fake_run(command, check, capture_output, text):
        assert command == ["say", "-v", "?"]
        assert check is True
        assert capture_output is True
        assert text is True
        return SimpleNamespace(
            stdout="Alex                en_US    # Hello\n\nAmelie              fr_FR    # Bonjour\n"
        )

    monkeypatch.setattr("codex_tts.tts.say.run", fake_run)

    assert SayBackend().list_voices() == ["Alex", "Amelie"]
