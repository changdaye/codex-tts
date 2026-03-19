import sqlite3
from pathlib import Path

from codex_tts.models import ThreadCandidate, ThreadRecord


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

    candidates: list[ThreadCandidate] = []
    for thread_id, rollout_path, created_at, updated_at in rows:
        candidate = build_thread_candidate(
            thread_id=thread_id,
            rollout_path=Path(rollout_path),
            created_at=created_at,
            updated_at=updated_at,
            started_at=started_at,
            known_thread_ids=known_thread_ids,
        )
        if candidate is not None:
            candidates.append(candidate)

    candidates.sort(key=candidate_sort_key, reverse=True)
    if not candidates:
        return None

    winner = candidates[0]
    if winner.score[0] == 0:
        return None
    if len(candidates) > 1 and candidate_sort_key(winner) == candidate_sort_key(candidates[1]):
        return None

    return ThreadRecord(
        thread_id=winner.thread_id,
        rollout_path=winner.rollout_path,
        created_at=winner.created_at,
        updated_at=winner.updated_at,
    )


def build_thread_candidate(
    *,
    thread_id: str,
    rollout_path: Path,
    created_at: int,
    updated_at: int,
    started_at: int,
    known_thread_ids: set[str],
) -> ThreadCandidate | None:
    if thread_id in known_thread_ids:
        return None
    if updated_at < started_at and created_at < started_at:
        return None

    rollout_exists = rollout_path.exists()
    has_activity = False
    if rollout_exists:
        stat = rollout_path.stat()
        has_activity = stat.st_size > 0 or int(stat.st_mtime) >= started_at

    return ThreadCandidate(
        thread_id=thread_id,
        rollout_path=rollout_path,
        created_at=created_at,
        updated_at=updated_at,
        score=(int(rollout_exists), int(has_activity)),
    )


def candidate_sort_key(candidate: ThreadCandidate) -> tuple[int, int, int, int]:
    return (
        candidate.score[0],
        candidate.score[1],
        candidate.updated_at,
        candidate.created_at,
    )
