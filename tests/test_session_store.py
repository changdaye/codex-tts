import sqlite3
from pathlib import Path

from codex_tts.diagnostics import DebugLogger
from codex_tts.models import ThreadCandidate
from codex_tts.session_store import build_thread_candidate, candidate_sort_key, resolve_active_thread


def build_state_db(tmp_path: Path) -> Path:
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
    conn.commit()
    conn.close()
    return db_path


def insert_thread(
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


def test_resolve_active_thread_matches_new_thread_by_cwd_and_time(tmp_path):
    db_path = build_state_db(tmp_path)
    rollout_path = tmp_path / "rollout-1.jsonl"
    rollout_path.write_text("", encoding="utf-8")
    insert_thread(
        db_path,
        thread_id="old-thread",
        rollout_path=tmp_path / "old.jsonl",
        created_at=900,
        updated_at=950,
        cwd="/tmp/project",
    )
    insert_thread(
        db_path,
        thread_id="thread-1",
        rollout_path=rollout_path,
        created_at=1005,
        updated_at=1010,
        cwd="/tmp/project",
    )
    thread = resolve_active_thread(
        db_path,
        cwd="/tmp/project",
        started_at=1000,
        known_thread_ids=set(),
    )
    assert thread.thread_id == "thread-1"
    assert thread.rollout_path.name == "rollout-1.jsonl"


def test_resolve_active_thread_prefers_newest_candidate_with_rollout_path(tmp_path):
    db_path = build_state_db(tmp_path)
    newer_rollout = tmp_path / "rollout-newer.jsonl"
    newer_rollout.write_text('{"event":"recent"}\n', encoding="utf-8")
    older_rollout = tmp_path / "rollout-older.jsonl"
    older_rollout.write_text('{"event":"older"}\n', encoding="utf-8")

    insert_thread(
        db_path,
        thread_id="missing-rollout",
        rollout_path=tmp_path / "missing.jsonl",
        created_at=1020,
        updated_at=1030,
        cwd="/tmp/project",
    )
    insert_thread(
        db_path,
        thread_id="older-rollout",
        rollout_path=older_rollout,
        created_at=1005,
        updated_at=1010,
        cwd="/tmp/project",
    )
    insert_thread(
        db_path,
        thread_id="newer-rollout",
        rollout_path=newer_rollout,
        created_at=1015,
        updated_at=1025,
        cwd="/tmp/project",
    )

    thread = resolve_active_thread(
        db_path,
        cwd="/tmp/project",
        started_at=1000,
        known_thread_ids=set(),
    )

    assert thread is not None
    assert thread.thread_id == "newer-rollout"
    assert thread.rollout_path == newer_rollout


def test_resolve_active_thread_skips_threads_without_existing_rollout(tmp_path):
    db_path = build_state_db(tmp_path)
    insert_thread(
        db_path,
        thread_id="missing-rollout",
        rollout_path=tmp_path / "missing.jsonl",
        created_at=1005,
        updated_at=1010,
        cwd="/tmp/project",
    )

    thread = resolve_active_thread(
        db_path,
        cwd="/tmp/project",
        started_at=1000,
        known_thread_ids=set(),
    )

    assert thread is None


def test_resolve_active_thread_logs_when_no_reliable_rollout_exists(tmp_path, capsys):
    db_path = build_state_db(tmp_path)
    insert_thread(
        db_path,
        thread_id="missing-rollout",
        rollout_path=tmp_path / "missing.jsonl",
        created_at=1005,
        updated_at=1010,
        cwd="/tmp/project",
    )

    thread = resolve_active_thread(
        db_path,
        cwd="/tmp/project",
        started_at=1000,
        known_thread_ids=set(),
        logger=DebugLogger(enabled=True),
    )

    assert thread is None
    assert "codex-tts: no reliable thread candidate had an existing rollout file" in capsys.readouterr().err


def test_build_thread_candidate_skips_known_thread_and_logs(tmp_path, capsys):
    candidate = build_thread_candidate(
        thread_id="thread-1",
        rollout_path=tmp_path / "rollout.jsonl",
        created_at=1005,
        updated_at=1010,
        started_at=1000,
        known_thread_ids={"thread-1"},
        logger=DebugLogger(enabled=True),
    )

    assert candidate is None
    assert "codex-tts: skipping known thread thread-1" in capsys.readouterr().err


def test_build_thread_candidate_skips_stale_thread_and_logs(tmp_path, capsys):
    candidate = build_thread_candidate(
        thread_id="thread-1",
        rollout_path=tmp_path / "rollout.jsonl",
        created_at=900,
        updated_at=950,
        started_at=1000,
        known_thread_ids=set(),
        logger=DebugLogger(enabled=True),
    )

    assert candidate is None
    assert "codex-tts: skipping stale thread thread-1" in capsys.readouterr().err


def test_candidate_sort_key_orders_by_score_then_timestamps():
    candidate = ThreadCandidate(
        thread_id="thread-1",
        rollout_path=Path("/tmp/rollout.jsonl"),
        created_at=11,
        updated_at=12,
        score=(1, 0),
    )

    assert candidate_sort_key(candidate) == (1, 0, 12, 11)
