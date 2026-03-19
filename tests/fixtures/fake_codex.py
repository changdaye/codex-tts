import json
import sqlite3
import sys
import time
from pathlib import Path


def build_events(raw_value: str) -> list[dict[str, float | str]]:
    if not raw_value.startswith("["):
        return [{"delay": 0.0, "text": raw_value}]

    rows = json.loads(raw_value)
    return [
        {
            "delay": float(row["delay"]),
            "text": str(row["text"]),
        }
        for row in rows
    ]


def main() -> int:
    state_db = Path(sys.argv[1])
    rollout_path = Path(sys.argv[2])
    cwd = sys.argv[3]
    thread_id = sys.argv[4]
    final_text = sys.argv[5]
    events = build_events(final_text)

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

    rollout_path.write_text("", encoding="utf-8")
    for event in events:
        time.sleep(event["delay"])
        payload = {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "final_answer",
                "content": [{"type": "output_text", "text": event["text"]}],
            },
        }
        with rollout_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
