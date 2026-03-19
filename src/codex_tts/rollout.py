import json
import time
from pathlib import Path

from codex_tts.models import ParsedRolloutEvent


def parse_rollout_line(line: str) -> ParsedRolloutEvent:
    row = json.loads(line)
    payload = row.get("payload", {})
    if (
        row.get("type") == "response_item"
        and payload.get("type") == "message"
        and payload.get("role") == "assistant"
        and payload.get("phase") == "final_answer"
    ):
        parts = payload.get("content", [])
        text = "".join(
            part.get("text", "")
            for part in parts
            if part.get("type") == "output_text"
        )
        return ParsedRolloutEvent(kind="final_message", text=text)

    return ParsedRolloutEvent(kind="ignored")


def read_final_answer(path: Path) -> str:
    if not path.exists():
        return ""

    for line in path.read_text(encoding="utf-8").splitlines():
        event = parse_rollout_line(line)
        if event.kind == "final_message" and event.text.strip():
            return event.text.strip()

    return ""


def wait_for_final_answer(path: Path, *, timeout: float = 5.0, poll_interval: float = 0.05) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        final_text = read_final_answer(path)
        if final_text:
            return final_text
        time.sleep(poll_interval)
    return ""
