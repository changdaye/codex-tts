import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from codex_tts.cli import build_parser
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


@dataclass
class FakeEnvironment:
    codex_cmd: list[str]
    config: AppConfig
    state_db: Path
    home_dir: Path
    cwd: Path

    @classmethod
    def create(cls, tmp_path: Path) -> "FakeEnvironment":
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
            "final reply",
        ]
        return cls(
            codex_cmd=codex_cmd,
            config=AppConfig(),
            state_db=state_db,
            home_dir=home_dir,
            cwd=cwd,
        )


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
