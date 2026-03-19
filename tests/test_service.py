from codex_tts.cli import build_parser
from codex_tts.tts import build_backend


def test_parser_accepts_passthrough_args():
    parser = build_parser()
    args = parser.parse_args(["--", "--no-alt-screen"])
    assert args.codex_args == ["--no-alt-screen"]


def test_build_backend_returns_say_backend():
    backend = build_backend("say")
    assert backend.__class__.__name__ == "SayBackend"
