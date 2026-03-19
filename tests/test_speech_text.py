from codex_tts.speech_text import sanitize_for_speech


def test_sanitize_for_speech_removes_bare_urls_and_markdown_targets():
    text = "Read [the docs](https://example.com/docs).\nMore info: https://openai.com/test"

    assert sanitize_for_speech(text) == "Read the docs.\nMore info:"


def test_sanitize_for_speech_collapses_empty_lines_after_url_removal():
    text = "First line\n\nhttps://example.com\n\nSecond line"

    assert sanitize_for_speech(text) == "First line\nSecond line"


def test_sanitize_for_speech_returns_empty_when_only_urls_remain():
    assert sanitize_for_speech("https://example.com/docs") == ""
