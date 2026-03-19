import sqlite3
from pathlib import Path

from codex_tts.models import ThreadRecord


def list_thread_ids(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("select id from threads").fetchall()
    finally:
        conn.close()

    return {row[0] for row in rows}


def resolve_active_thread(
    db_path: Path,
    *,
    cwd: str,
    started_at: int,
    known_thread_ids: set[str],
) -> ThreadRecord | None:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            select id, rollout_path, created_at, updated_at
            from threads
            where cwd = ?
            order by updated_at desc
            """,
            (cwd,),
        ).fetchall()
    finally:
        conn.close()

    for thread_id, rollout_path, created_at, updated_at in rows:
        if thread_id in known_thread_ids:
            continue
        if updated_at >= started_at or created_at >= started_at:
            return ThreadRecord(
                thread_id=thread_id,
                rollout_path=Path(rollout_path),
                created_at=created_at,
                updated_at=updated_at,
            )

    return None
