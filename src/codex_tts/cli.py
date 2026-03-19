import argparse
from pathlib import Path
import shutil

from codex_tts.config import default_config_path, load_config
from codex_tts.service import run_session


class CodexTTSArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args=args, namespace=namespace)
        if parsed.codex_args and parsed.codex_args[0] == "--":
            parsed.codex_args = parsed.codex_args[1:]
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = CodexTTSArgumentParser(prog="codex-tts")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path(),
        help="Path to the codex-tts config file.",
    )
    parser.add_argument("codex_args", nargs=argparse.REMAINDER)
    return parser


def build_codex_command(codex_args: list[str], *, codex_binary: str) -> list[str]:
    return [codex_binary, *codex_args]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    codex_binary = shutil.which("codex")
    if codex_binary is None:
        raise RuntimeError("Could not find `codex` in PATH.")

    config = load_config(args.config)
    home_dir = Path.home()
    state_db = home_dir / ".codex" / "state_5.sqlite"
    codex_cmd = build_codex_command(args.codex_args, codex_binary=codex_binary)
    return run_session(codex_cmd, config, state_db, home_dir, Path.cwd())


if __name__ == "__main__":
    raise SystemExit(main())
