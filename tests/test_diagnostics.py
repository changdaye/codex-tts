from codex_tts.diagnostics import DebugLogger


def test_debug_logger_writes_prefixed_messages(capsys):
    logger = DebugLogger(enabled=True)

    logger.log("watching rollout")

    assert capsys.readouterr().err == "codex-tts: watching rollout\n"
