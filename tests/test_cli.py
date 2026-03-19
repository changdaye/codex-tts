import argparse
import json
from pathlib import Path
import runpy
import sys

import pytest

from codex_tts.cli import (
    _stop_process,
    build_parser,
    launch_codex_session,
    main,
    merge_config,
    positive_float,
    positive_int,
    run_command,
)
from codex_tts.config import AppConfig


def test_positive_float_rejects_non_positive_values():
    with pytest.raises(argparse.ArgumentTypeError, match="value must be greater than 0"):
        positive_float("0")


def test_positive_int_rejects_non_positive_values():
    with pytest.raises(argparse.ArgumentTypeError, match="value must be greater than 0"):
        positive_int("-1")


def test_merge_config_enables_verbose_override():
    args = build_parser().parse_args(["--verbose"])

    merged = merge_config(AppConfig(verbose=False), args)

    assert merged.verbose is True


def test_main_raises_when_codex_binary_is_missing(monkeypatch, tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("codex_tts.cli.load_config", lambda path: AppConfig())
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="Could not find `codex` in PATH."):
        main(["--config", str(config_path)])


def test_cli_module_main_entrypoint_exits_cleanly_for_help(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["codex-tts", "--help"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("codex_tts.cli", run_name="__main__")

    assert exc.value.code == 0


def test_build_parser_keeps_default_config_path_under_codex_tts_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    args = build_parser().parse_args([])

    assert args.config == tmp_path / ".codex-tts" / "config.toml"


def test_main_launch_command_uses_launch_mode(monkeypatch, tmp_path):
    captured = {}
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: "/usr/local/bin/codex")
    monkeypatch.setattr("codex_tts.cli.load_config", lambda path: AppConfig())
    monkeypatch.setattr(
        "codex_tts.cli.launch_codex_session",
        lambda codex_cmd, config, state_db, home_dir, cwd: captured.update(
            {
                "cmd": codex_cmd,
                "config": config,
                "state_db": state_db,
                "home_dir": home_dir,
                "cwd": cwd,
            }
        )
        or 0,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["launch", "--config", str(config_path), "--", "--no-alt-screen"])

    assert exit_code == 0
    assert captured["cmd"] == ["/usr/local/bin/codex", "--no-alt-screen"]


def test_main_status_json_prints_daemon_snapshot(monkeypatch, capsys):
    monkeypatch.setattr(
        "codex_tts.cli.call_daemon",
        lambda path, request: {
            "ok": True,
            "snapshot": {
                "global_enabled": True,
                "focus_session_id": "session-1",
                "sessions": [],
            },
        },
    )

    exit_code = main(["status", "--json"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "global_enabled": True,
        "focus_session_id": "session-1",
        "sessions": [],
    }


def test_main_status_returns_clean_error_when_daemon_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(
        "codex_tts.cli.call_daemon",
        lambda path, request: (_ for _ in ()).throw(FileNotFoundError("missing socket")),
    )

    exit_code = main(["status", "--json"])

    assert exit_code == 1
    assert capsys.readouterr().err.strip() == "codex-tts: daemon is not running"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (ConnectionRefusedError("refused"), "codex-tts: daemon is not running"),
        (TimeoutError("timed out"), "codex-tts: daemon did not respond"),
        (OSError(54, "Connection reset by peer"), "codex-tts: could not reach daemon: Connection reset by peer"),
    ],
)
def test_main_status_maps_daemon_transport_errors(monkeypatch, capsys, error, message):
    monkeypatch.setattr(
        "codex_tts.cli.call_daemon",
        lambda path, request: (_ for _ in ()).throw(error),
    )

    exit_code = main(["status", "--json"])

    assert exit_code == 1
    assert capsys.readouterr().err.strip() == message


def test_main_status_plain_text_prints_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        "codex_tts.cli.call_daemon",
        lambda path, request: {
            "ok": True,
            "snapshot": {
                "global_enabled": False,
                "focus_session_id": "session-2",
                "sessions": [{"session_id": "session-1"}, {"session_id": "session-2"}],
            },
        },
    )

    exit_code = main(["status"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "focus=session-2 sessions=2 enabled=False"


def test_launch_falls_back_to_direct_mode_when_daemon_unavailable(monkeypatch, tmp_path):
    captured = {}
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: "/usr/local/bin/codex")
    monkeypatch.setattr("codex_tts.cli.load_config", lambda path: AppConfig())
    monkeypatch.setattr(
        "codex_tts.cli.call_daemon",
        lambda path, request: (_ for _ in ()).throw(FileNotFoundError("missing socket")),
    )
    monkeypatch.setattr(
        "codex_tts.cli.run_session",
        lambda codex_cmd, config, state_db, home_dir, cwd: captured.update(
            {
                "cmd": codex_cmd,
                "config": config,
                "state_db": state_db,
                "home_dir": home_dir,
                "cwd": cwd,
            }
        )
        or 0,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["launch", "--config", str(config_path), "--", "--no-alt-screen"])

    assert exit_code == 0
    assert captured["cmd"] == ["/usr/local/bin/codex", "--no-alt-screen"]


def test_main_session_commands_forward_to_daemon(monkeypatch):
    requests: list[dict[str, object]] = []

    def fake_call_daemon(path: Path, request: dict[str, object]) -> dict[str, object]:
        requests.append(request)
        return {"ok": True}

    monkeypatch.setattr("codex_tts.cli.call_daemon", fake_call_daemon)

    assert main(["focus", "session-1"]) == 0
    assert main(["mute", "session-1"]) == 0
    assert main(["unmute", "session-1"]) == 0
    assert main(["enable"]) == 0
    assert main(["disable"]) == 0

    assert requests == [
        {"command": "set_focus", "session_id": "session-1"},
        {"command": "mute_session", "session_id": "session-1"},
        {"command": "unmute_session", "session_id": "session-1"},
        {"command": "set_global_enabled", "enabled": True},
        {"command": "set_global_enabled", "enabled": False},
    ]


def test_main_session_command_returns_error_when_daemon_rejects_request(monkeypatch, capsys):
    monkeypatch.setattr(
        "codex_tts.cli.call_daemon",
        lambda path, request: {"ok": False, "error": "unknown session: missing"},
    )

    exit_code = main(["mute", "missing"])

    assert exit_code == 1
    assert capsys.readouterr().err.strip() == "codex-tts: unknown session: missing"


def test_run_command_rejects_unknown_subcommand():
    with pytest.raises(RuntimeError, match="unknown command: mystery"):
        run_command(["mystery"])


def test_launch_registers_new_session_with_daemon_when_available(monkeypatch, tmp_path):
    daemon_requests: list[tuple[Path, dict[str, object]]] = []
    popen_calls: dict[str, object] = {}

    class FakeUUID:
        hex = "session-uuid"

    class FakeProcess:
        pid = 4321

        def wait(self) -> int:
            return 7

    def fake_call_daemon(path: Path, request: dict[str, object]) -> dict[str, object]:
        daemon_requests.append((path, request))
        return {"ok": True}

    def fake_popen(cmd: list[str], *, cwd: str, env: dict[str, str]) -> FakeProcess:
        popen_calls["cmd"] = cmd
        popen_calls["cwd"] = cwd
        popen_calls["env"] = env
        return FakeProcess()

    monkeypatch.setattr("codex_tts.cli.call_daemon", fake_call_daemon)
    monkeypatch.setattr("codex_tts.cli.daemon_socket_path", lambda: tmp_path / "daemon.sock")
    monkeypatch.setattr("codex_tts.cli.list_thread_ids", lambda path: {"thread-b", "thread-a"})
    monkeypatch.setattr("codex_tts.cli.time.time", lambda: 1234.9)
    monkeypatch.setattr("codex_tts.cli.os.getpid", lambda: 99)
    monkeypatch.setattr("codex_tts.cli.uuid.uuid4", lambda: FakeUUID())
    monkeypatch.setattr("codex_tts.cli.subprocess.Popen", fake_popen)

    exit_code = launch_codex_session(
        ["codex", "--no-alt-screen"],
        AppConfig(),
        tmp_path / "state.sqlite",
        tmp_path / "home",
        tmp_path / "workspace",
    )

    assert exit_code == 7
    assert daemon_requests == [
        (tmp_path / "daemon.sock", {"command": "ping"}),
        (
            tmp_path / "daemon.sock",
            {
                "command": "register_launch",
                "session_id": "session-uuid",
                "cwd": str(tmp_path / "workspace"),
                "started_at": 1234,
                "launcher_pid": 99,
                "codex_pid": 4321,
                "known_thread_ids": ["thread-a", "thread-b"],
            },
        ),
    ]
    assert popen_calls["cmd"] == ["codex", "--no-alt-screen"]
    assert popen_calls["cwd"] == str(tmp_path / "workspace")
    assert popen_calls["env"]["HOME"] == str(tmp_path / "home")


def test_launch_falls_back_to_direct_mode_when_register_fails_after_spawn(monkeypatch, tmp_path):
    daemon_requests: list[dict[str, object]] = []
    captured = {}

    class FakeProcess:
        pid = 4321

        def __init__(self) -> None:
            self.terminated = False
            self.killed = False
            self.wait_calls: list[float | None] = []

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            return 0

    process = FakeProcess()

    def fake_call_daemon(path: Path, request: dict[str, object]) -> dict[str, object]:
        daemon_requests.append(request)
        if request["command"] == "ping":
            return {"ok": True}
        raise RuntimeError("socket closed before newline-delimited JSON message completed")

    monkeypatch.setattr("codex_tts.cli.call_daemon", fake_call_daemon)
    monkeypatch.setattr("codex_tts.cli.daemon_socket_path", lambda: tmp_path / "daemon.sock")
    monkeypatch.setattr("codex_tts.cli.list_thread_ids", lambda path: {"thread-a"})
    monkeypatch.setattr("codex_tts.cli.subprocess.Popen", lambda cmd, cwd, env: process)
    monkeypatch.setattr(
        "codex_tts.cli.run_session",
        lambda codex_cmd, config, state_db, home_dir, cwd: captured.update(
            {
                "cmd": codex_cmd,
                "config": config,
                "state_db": state_db,
                "home_dir": home_dir,
                "cwd": cwd,
            }
        )
        or 11,
    )

    exit_code = launch_codex_session(
        ["codex", "--no-alt-screen"],
        AppConfig(),
        tmp_path / "state.sqlite",
        tmp_path / "home",
        tmp_path / "workspace",
    )

    assert exit_code == 11
    assert daemon_requests[0] == {"command": "ping"}
    assert daemon_requests[1]["command"] == "register_launch"
    assert process.terminated is True
    assert process.killed is False
    assert process.wait_calls == [1.0]
    assert captured["cmd"] == ["codex", "--no-alt-screen"]
    assert captured["cwd"] == tmp_path / "workspace"


def test_stop_process_kills_when_terminate_fails():
    class FakeProcess:
        def __init__(self) -> None:
            self.calls: list[tuple[str, float | None]] = []

        def terminate(self) -> None:
            self.calls.append(("terminate", None))
            raise RuntimeError("no terminate")

        def kill(self) -> None:
            self.calls.append(("kill", None))

        def wait(self, timeout: float | None = None) -> int:
            self.calls.append(("wait", timeout))
            return 0

    process = FakeProcess()

    _stop_process(process)

    assert process.calls == [("terminate", None), ("kill", None), ("wait", 1.0)]


def test_stop_process_swallows_kill_failure():
    class FakeProcess:
        def __init__(self) -> None:
            self.calls: list[tuple[str, float | None]] = []

        def terminate(self) -> None:
            self.calls.append(("terminate", None))
            raise RuntimeError("no terminate")

        def kill(self) -> None:
            self.calls.append(("kill", None))
            raise RuntimeError("no kill")

        def wait(self, timeout: float | None = None) -> int:
            self.calls.append(("wait", timeout))
            return 0

    process = FakeProcess()

    _stop_process(process)

    assert process.calls == [("terminate", None), ("kill", None)]


def test_main_daemon_run_returns_error_for_invalid_config(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("codex_tts.cli.load_config", lambda path: (_ for _ in ()).throw(ValueError("bad config")))

    exit_code = main(["daemon", "run", "--config", str(config_path)])

    assert exit_code == 2
    assert "codex-tts: invalid config: bad config" in capsys.readouterr().err


def test_main_daemon_run_starts_daemon(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class FakeDaemon:
        def __init__(self, *, config: AppConfig, state_db: Path, socket_path: Path, settings_path: Path) -> None:
            captured["config"] = config
            captured["state_db"] = state_db
            captured["socket_path"] = socket_path
            captured["settings_path"] = settings_path

        def serve_forever(self) -> None:
            captured["served"] = True

    monkeypatch.setattr("codex_tts.cli.load_config", lambda path: AppConfig(verbose=True))
    monkeypatch.setattr("codex_tts.cli.Path.home", lambda: tmp_path)
    monkeypatch.setattr("codex_tts.cli.daemon_socket_path", lambda: tmp_path / "daemon.sock")
    monkeypatch.setattr("codex_tts.cli.daemon_state_path", lambda: tmp_path / "daemon-state.json")
    monkeypatch.setattr("codex_tts.cli.CodexTTSDaemon", FakeDaemon)

    exit_code = main(["daemon", "run", "--config", str(tmp_path / "config.toml")])

    assert exit_code == 0
    assert captured["served"] is True
    assert captured["state_db"] == tmp_path / ".codex" / "state_5.sqlite"
    assert captured["socket_path"] == tmp_path / "daemon.sock"
    assert captured["settings_path"] == tmp_path / "daemon-state.json"
