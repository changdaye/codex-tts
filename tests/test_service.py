from codex_tts.cli import build_parser


def test_parser_accepts_passthrough_args():
    parser = build_parser()
    args = parser.parse_args(["--", "--no-alt-screen"])
    assert args.codex_args == ["--no-alt-screen"]
