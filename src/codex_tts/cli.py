import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from codex_tts.config import AppConfig, daemon_socket_path, daemon_state_path, default_config_path, load_config
from codex_tts.daemon import CodexTTSDaemon
from codex_tts.ipc import call_daemon
from codex_tts.service import run_session
from codex_tts.session_store import list_thread_ids
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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug diagnostics about thread selection and skipped speech.",
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
    if args.verbose:
        merged = replace(merged, verbose=True)
    return merged


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"launch", "status", "focus", "mute", "unmute", "enable", "disable", "daemon"}:
        return run_command(argv)

    args = build_parser().parse_args(argv)
    try:
        config = merge_config(load_config(args.config), args)
    except ValueError as exc:
        print(f"codex-tts: invalid config: {exc}", file=sys.stderr)
        return 2
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
    return launch_codex_session(codex_cmd, config, state_db, home_dir, Path.cwd())


def run_command(argv: list[str]) -> int:
    command = argv[0]
    if command == "launch":
        return main(argv[1:])
    if command == "status":
        return _run_status_command(argv[1:])
    if command == "focus":
        return _run_session_id_command(argv[1:], daemon_command="set_focus")
    if command == "mute":
        return _run_session_id_command(argv[1:], daemon_command="mute_session")
    if command == "unmute":
        return _run_session_id_command(argv[1:], daemon_command="unmute_session")
    if command == "enable":
        return _set_global_enabled(True)
    if command == "disable":
        return _set_global_enabled(False)
    if command == "daemon":
        return _run_daemon_command(argv[1:])
    raise RuntimeError(f"unknown command: {command}")


def launch_codex_session(
    codex_cmd: list[str],
    config: AppConfig,
    state_db: Path,
    home_dir: Path,
    cwd: Path,
) -> int:
    try:
        call_daemon(daemon_socket_path(), {"command": "ping"})
    except OSError:
        return run_session(codex_cmd, config, state_db, home_dir, cwd)

    started_at = int(time.time())
    known_thread_ids = sorted(list_thread_ids(state_db))
    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    process = subprocess.Popen(codex_cmd, cwd=str(cwd), env=env)
    call_daemon(
        daemon_socket_path(),
        {
            "command": "register_launch",
            "session_id": uuid.uuid4().hex,
            "cwd": str(cwd),
            "started_at": started_at,
            "launcher_pid": os.getpid(),
            "codex_pid": process.pid,
            "known_thread_ids": known_thread_ids,
        },
    )
    return process.wait()


def _run_status_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="codex-tts status")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    response = call_daemon(daemon_socket_path(), {"command": "status"})
    snapshot = response["snapshot"]
    if args.json:
        print(json.dumps(snapshot))
    else:
        print(
            f"focus={snapshot['focus_session_id']} sessions={len(snapshot['sessions'])} enabled={snapshot['global_enabled']}"
        )
    return 0


def _run_session_id_command(argv: list[str], *, daemon_command: str) -> int:
    parser = argparse.ArgumentParser(prog=f"codex-tts {daemon_command}")
    parser.add_argument("session_id")
    args = parser.parse_args(argv)
    call_daemon(
        daemon_socket_path(),
        {
            "command": daemon_command,
            "session_id": args.session_id,
        },
    )
    return 0


def _set_global_enabled(enabled: bool) -> int:
    call_daemon(
        daemon_socket_path(),
        {
            "command": "set_global_enabled",
            "enabled": enabled,
        },
    )
    return 0


def _run_daemon_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="codex-tts daemon")
    parser.add_argument("action", choices=["run"])
    parser.add_argument("--config", type=Path, default=default_config_path())
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ValueError as exc:
        print(f"codex-tts: invalid config: {exc}", file=sys.stderr)
        return 2

    daemon = CodexTTSDaemon(
        config=config,
        state_db=Path.home() / ".codex" / "state_5.sqlite",
        socket_path=daemon_socket_path(),
        settings_path=daemon_state_path(),
    )
    daemon.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
