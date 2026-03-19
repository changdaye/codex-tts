import argparse
from dataclasses import replace
from pathlib import Path
import shutil

from codex_tts.config import default_config_path, load_config
from codex_tts.service import run_session
from codex_tts.tts import list_voices

PRESET_RATES = {
    "normal": 180,
    "fast": 270,
    "faster": 360,
    "ultra": 540,
}


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


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
    parser.add_argument(
        "--voice",
        help="Override the configured system voice for this run.",
    )
    speed_group = parser.add_mutually_exclusive_group()
    speed_group.add_argument(
        "--rate",
        type=positive_int,
        help="Set the absolute speech rate for this run.",
    )
    speed_group.add_argument(
        "--speed",
        type=positive_float,
        help="Multiply the configured speech rate for this run.",
    )
    speed_group.add_argument(
        "--preset",
        choices=sorted(PRESET_RATES),
        help="Apply a named speech-rate preset for this run.",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available system voices for the current backend and exit.",
    )
    parser.add_argument("codex_args", nargs=argparse.REMAINDER)
    return parser


def build_codex_command(codex_args: list[str], *, codex_binary: str) -> list[str]:
    return [codex_binary, *codex_args]


def merge_config(config, args):
    merged = config
    if args.voice:
        merged = replace(merged, voice=args.voice)
    if args.rate is not None:
        merged = replace(merged, rate=args.rate)
    elif args.preset is not None:
        merged = replace(merged, rate=PRESET_RATES[args.preset])
    elif args.speed is not None:
        merged = replace(merged, rate=max(1, round(merged.rate * args.speed)))
    return merged


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = merge_config(load_config(args.config), args)
    if args.list_voices:
        for voice in list_voices(config.backend):
            print(voice)
        return 0

    codex_binary = shutil.which("codex")
    if codex_binary is None:
        raise RuntimeError("Could not find `codex` in PATH.")

    home_dir = Path.home()
    state_db = home_dir / ".codex" / "state_5.sqlite"
    codex_cmd = build_codex_command(args.codex_args, codex_binary=codex_binary)
    return run_session(codex_cmd, config, state_db, home_dir, Path.cwd())


if __name__ == "__main__":
    raise SystemExit(main())
