import sqlite3
from pathlib import Path

from codex_tts.session_store import resolve_active_thread


def build_state_db(tmp_path: Path, cwd: str) -> Path:
    db_path = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db_path)
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
    conn.execute(
        """
        insert into threads (id, rollout_path, created_at, updated_at, cwd)
        values (?, ?, ?, ?, ?)
        """,
        ("old-thread", str(tmp_path / "old.jsonl"), 900, 950, cwd),
    )
    conn.execute(
        """
        insert into threads (id, rollout_path, created_at, updated_at, cwd)
        values (?, ?, ?, ?, ?)
        """,
        ("thread-1", str(tmp_path / "rollout-1.jsonl"), 1005, 1010, cwd),
    )
    conn.commit()
    conn.close()
    return db_path


def test_resolve_active_thread_matches_new_thread_by_cwd_and_time(tmp_path):
    db_path = build_state_db(tmp_path, cwd="/tmp/project")
    thread = resolve_active_thread(
        db_path,
        cwd="/tmp/project",
        started_at=1000,
        known_thread_ids=set(),
    )
    assert thread.thread_id == "thread-1"
    assert thread.rollout_path.name == "rollout-1.jsonl"
