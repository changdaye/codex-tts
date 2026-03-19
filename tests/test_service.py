import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from codex_tts.cli import build_codex_command, build_parser, main
from codex_tts.config import AppConfig
from codex_tts.service import run_session
from codex_tts.tts import build_backend


def test_parser_accepts_passthrough_args():
    parser = build_parser()
    args = parser.parse_args(["--", "--no-alt-screen"])
    assert args.codex_args == ["--no-alt-screen"]


def test_build_backend_returns_say_backend():
    backend = build_backend("say")
    assert backend.__class__.__name__ == "SayBackend"


def test_build_codex_command_prefixes_real_codex_binary():
    command = build_codex_command(["--no-alt-screen"], codex_binary="/usr/local/bin/codex")
    assert command == ["/usr/local/bin/codex", "--no-alt-screen"]


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
