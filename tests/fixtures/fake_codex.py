import json
import sqlite3
import sys
import time
from pathlib import Path


def main() -> int:
    state_db = Path(sys.argv[1])
    rollout_path = Path(sys.argv[2])
    cwd = sys.argv[3]
    thread_id = sys.argv[4]
    final_text = sys.argv[5]

    rollout_path.parent.mkdir(parents=True, exist_ok=True)
    now = int(time.time())

    conn = sqlite3.connect(state_db)
    conn.execute(
        """
        insert into threads (id, rollout_path, created_at, updated_at, cwd)
        values (?, ?, ?, ?, ?)
        """,
        (thread_id, str(rollout_path), now, now, cwd),
    )
    conn.commit()
    conn.close()

    payload = {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "assistant",
            "phase": "final_answer",
            "content": [{"type": "output_text", "text": final_text}],
        },
    }
    rollout_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
