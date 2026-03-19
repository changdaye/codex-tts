import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from codex_tts.cli import build_codex_command, build_parser, main, merge_config
from codex_tts.config import AppConfig
from codex_tts.service import run_session
from codex_tts.tts import build_backend


def insert_thread_record(
    db_path: Path,
    *,
    thread_id: str,
    rollout_path: Path,
    created_at: int,
    updated_at: int,
    cwd: str,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        insert into threads (id, rollout_path, created_at, updated_at, cwd)
        values (?, ?, ?, ?, ?)
        """,
        (thread_id, str(rollout_path), created_at, updated_at, cwd),
    )
    conn.commit()
    conn.close()


def test_parser_accepts_passthrough_args():
    parser = build_parser()
    args = parser.parse_args(["--", "--no-alt-screen"])
    assert args.codex_args == ["--no-alt-screen"]


def test_parser_rejects_rate_and_speed_together():
    parser = build_parser()
    try:
        parser.parse_args(["--rate", "220", "--speed", "1.5"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected parser to reject --rate with --speed")


def test_parser_rejects_preset_with_speed():
    parser = build_parser()
    try:
        parser.parse_args(["--preset", "ultra", "--speed", "1.5"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected parser to reject --preset with --speed")


def test_parser_accepts_verbose_flag():
    parser = build_parser()
    args = parser.parse_args(["--verbose", "--", "--no-alt-screen"])
    assert args.verbose is True
    assert args.codex_args == ["--no-alt-screen"]


def test_build_backend_returns_say_backend():
    backend = build_backend("say")
    assert backend.__class__.__name__ == "SayBackend"


def test_build_codex_command_prefixes_real_codex_binary():
    command = build_codex_command(["--no-alt-screen"], codex_binary="/usr/local/bin/codex")
    assert command == ["/usr/local/bin/codex", "--no-alt-screen"]


def test_merge_config_applies_cli_voice_and_speed_overrides():
    parser = build_parser()
    args = parser.parse_args(["--voice", "Mei-Jia", "--speed", "1.5", "--", "--no-alt-screen"])

    config = merge_config(AppConfig(voice="Tingting", rate=180), args)

    assert config.voice == "Mei-Jia"
    assert config.rate == 270


def test_merge_config_applies_absolute_rate_override():
    parser = build_parser()
    args = parser.parse_args(["--rate", "240"])

    config = merge_config(AppConfig(rate=180), args)

    assert config.rate == 240


def test_merge_config_applies_preset_rate_override():
    parser = build_parser()
    args = parser.parse_args(["--preset", "ultra"])

    config = merge_config(AppConfig(rate=180), args)

    assert config.rate == 540


def test_main_invokes_service_with_loaded_config(monkeypatch, tmp_path):
    captured = {}
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: "/usr/local/bin/codex")
    monkeypatch.setattr(
        "codex_tts.cli.load_config",
        lambda path: AppConfig() if path == config_path else None,
    )
    monkeypatch.setattr(
        "codex_tts.cli.run_session",
        lambda cmd, config, state_db, home_dir, cwd: captured.update(
            {
                "cmd": cmd,
                "config": config,
                "state_db": state_db,
                "home_dir": home_dir,
                "cwd": cwd,
            }
        )
        or 0,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--config", str(config_path), "--", "--no-alt-screen"])

    assert exit_code == 0
    assert captured["cmd"] == ["/usr/local/bin/codex", "--no-alt-screen"]
    assert captured["config"] == AppConfig()
    assert captured["state_db"].name == "state_5.sqlite"


def test_main_invokes_service_with_preset_override(monkeypatch, tmp_path):
    captured = {}
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: "/usr/local/bin/codex")
    monkeypatch.setattr(
        "codex_tts.cli.load_config",
        lambda path: AppConfig(rate=180) if path == config_path else None,
    )
    monkeypatch.setattr(
        "codex_tts.cli.run_session",
        lambda cmd, config, state_db, home_dir, cwd: captured.update(
            {
                "cmd": cmd,
                "config": config,
                "state_db": state_db,
                "home_dir": home_dir,
                "cwd": cwd,
            }
        )
        or 0,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--config", str(config_path), "--preset", "faster", "--", "--no-alt-screen"])

    assert exit_code == 0
    assert captured["config"].rate == 360


def test_main_lists_voices_without_starting_codex(monkeypatch, capsys):
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: "/usr/local/bin/codex")
    monkeypatch.setattr("codex_tts.cli.load_config", lambda path: AppConfig())
    monkeypatch.setattr("codex_tts.cli.list_voices", lambda backend_name: ["Tingting", "Mei-Jia"])
    monkeypatch.setattr(
        "codex_tts.cli.run_session",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("run_session should not be called")),
    )

    exit_code = main(["--list-voices"])

    assert exit_code == 0
    assert capsys.readouterr().out == "Tingting\nMei-Jia\n"


def test_main_prints_invalid_config_errors(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    config_path.write_text("rate = 0\n", encoding="utf-8")
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: "/usr/local/bin/codex")

    exit_code = main(["--config", str(config_path)])

    assert exit_code == 2
    assert capsys.readouterr().err == "codex-tts: invalid config: rate must be greater than 0\n"


@dataclass
class FakeEnvironment:
    codex_cmd: list[str]
    config: AppConfig
    state_db: Path
    home_dir: Path
    cwd: Path

    @classmethod
    def create(
        cls,
        tmp_path: Path,
        *,
        final_text: str = "final reply",
    ) -> "FakeEnvironment":
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        cwd = tmp_path / "workspace"
        cwd.mkdir()
        state_db = tmp_path / "state.sqlite"
        rollout_path = tmp_path / "rollout.jsonl"

        conn = sqlite3.connect(state_db)
        conn.execute(
            """
            create table threads (
                id text primary key,
                rollout_path text not null,
                created_at integer not null,
                updated_at integer not null,
                cwd text not null
            )
            """
        )
        conn.commit()
        conn.close()

        fake_script = Path(__file__).parent / "fixtures" / "fake_codex.py"
        codex_cmd = [
            sys.executable,
            str(fake_script),
            str(state_db),
            str(rollout_path),
            str(cwd),
            "thread-1",
            final_text,
        ]
        return cls(
            codex_cmd=codex_cmd,
            config=AppConfig(),
            state_db=state_db,
            home_dir=home_dir,
            cwd=cwd,
        )

    @classmethod
    def without_matching_thread(cls, tmp_path: Path) -> "FakeEnvironment":
        fake = cls.create(tmp_path)
        fake.cwd = tmp_path / "other-workspace"
        fake.cwd.mkdir()
        return fake


def test_run_session_speaks_final_answer_once(tmp_path, monkeypatch):
    fake = FakeEnvironment.create(tmp_path)
    spoken: list[str] = []
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )
    exit_code = run_session(fake.codex_cmd, fake.config, fake.state_db, fake.home_dir, fake.cwd)
    assert exit_code == 0
    assert spoken == ["final reply"]


def test_run_session_speaks_sanitized_final_answer(tmp_path, monkeypatch):
    fake = FakeEnvironment.create(
        tmp_path,
        final_text="Read [the docs](https://example.com/docs). More info: https://openai.com/test",
    )
    spoken: list[str] = []
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )

    exit_code = run_session(fake.codex_cmd, fake.config, fake.state_db, fake.home_dir, fake.cwd)

    assert exit_code == 0
    assert spoken == ["Read the docs. More info:"]


def test_run_session_skips_speech_when_sanitized_text_is_empty(tmp_path, monkeypatch):
    fake = FakeEnvironment.create(
        tmp_path,
        final_text="https://example.com/docs",
    )
    spoken: list[str] = []
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )

    exit_code = run_session(fake.codex_cmd, fake.config, fake.state_db, fake.home_dir, fake.cwd)

    assert exit_code == 0
    assert spoken == []


def test_run_session_logs_why_speech_was_skipped(monkeypatch, tmp_path, capsys):
    fake = FakeEnvironment.create(
        tmp_path,
        final_text="https://example.com/docs",
    )
    spoken: list[str] = []
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )

    exit_code = run_session(
        fake.codex_cmd,
        AppConfig(verbose=True),
        fake.state_db,
        fake.home_dir,
        fake.cwd,
    )

    assert exit_code == 0
    assert spoken == []
    assert "codex-tts: sanitized final message was empty; skipping speech" in capsys.readouterr().err


def test_run_session_skips_speech_when_no_thread_matches(tmp_path, monkeypatch):
    fake = FakeEnvironment.without_matching_thread(tmp_path)
    spoken: list[str] = []
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )
    exit_code = run_session(fake.codex_cmd, fake.config, fake.state_db, fake.home_dir, fake.cwd)
    assert exit_code == 0
    assert spoken == []


def test_run_session_skips_speech_when_thread_candidates_are_ambiguous(tmp_path, monkeypatch):
    fake = FakeEnvironment.create(tmp_path)
    rollout_one = tmp_path / "ambiguous-1.jsonl"
    rollout_two = tmp_path / "ambiguous-2.jsonl"
    rollout_one.write_text(
        '{"type":"response_item","payload":{"type":"message","role":"assistant","phase":"final_answer","content":[{"type":"output_text","text":"wrong one"}]}}\n',
        encoding="utf-8",
    )
    rollout_two.write_text(
        '{"type":"response_item","payload":{"type":"message","role":"assistant","phase":"final_answer","content":[{"type":"output_text","text":"wrong two"}]}}\n',
        encoding="utf-8",
    )
    insert_thread_record(
        fake.state_db,
        thread_id="thread-a",
        rollout_path=rollout_one,
        created_at=1001,
        updated_at=1002,
        cwd=str(fake.cwd),
    )
    insert_thread_record(
        fake.state_db,
        thread_id="thread-b",
        rollout_path=rollout_two,
        created_at=1001,
        updated_at=1002,
        cwd=str(fake.cwd),
    )

    spoken: list[str] = []
    monkeypatch.setattr("codex_tts.service.list_thread_ids", lambda path: set())
    monkeypatch.setattr("codex_tts.service.time.time", lambda: 1000)
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )

    exit_code = run_session(
        [sys.executable, "-c", "import time; time.sleep(0.01)"],
        fake.config,
        fake.state_db,
        fake.home_dir,
        fake.cwd,
    )

    assert exit_code == 0
    assert spoken == []


def test_run_session_ignores_speech_backend_failures(tmp_path, monkeypatch):
    fake = FakeEnvironment.create(tmp_path)
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: (_ for _ in ()).throw(RuntimeError("speaker failed")),
    )
    exit_code = run_session(fake.codex_cmd, fake.config, fake.state_db, fake.home_dir, fake.cwd)
    assert exit_code == 0


def test_run_session_waits_for_delayed_final_answer(tmp_path, monkeypatch):
    fake = FakeEnvironment.create(
        tmp_path,
        final_text='[{"delay": 5.2, "text": "delayed reply"}]',
    )
    spoken: list[str] = []
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )

    exit_code = run_session(fake.codex_cmd, fake.config, fake.state_db, fake.home_dir, fake.cwd)

    assert exit_code == 0
    assert spoken == ["delayed reply"]


def test_run_session_speaks_each_new_final_answer(tmp_path, monkeypatch):
    fake = FakeEnvironment.create(
        tmp_path,
        final_text='[{"delay": 0.0, "text": "first reply"}, {"delay": 0.1, "text": "second reply"}]',
    )
    spoken: list[str] = []
    monkeypatch.setattr(
        "codex_tts.service.speak_text",
        lambda text, config: spoken.append(text),
    )

    exit_code = run_session(fake.codex_cmd, fake.config, fake.state_db, fake.home_dir, fake.cwd)

    assert exit_code == 0
    assert spoken == ["first reply", "second reply"]
