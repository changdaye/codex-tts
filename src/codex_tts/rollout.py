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


def read_new_events(
    path: Path,
    *,
    start_line: int = 0,
) -> tuple[list[ParsedRolloutEvent], int]:
    if not path.exists():
        return [], start_line

    lines = path.read_text(encoding="utf-8").splitlines()
    if start_line > len(lines):
        start_line = 0

    events = [parse_rollout_line(line) for line in lines[start_line:]]
    return events, len(lines)


class FinalAnswerWatcher:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._line_index = 0

    def poll(self) -> list[ParsedRolloutEvent]:
        events, self._line_index = read_new_events(
            self.path,
            start_line=self._line_index,
        )
        return [
            event
            for event in events
            if event.kind == "final_message" and event.text.strip()
        ]


def read_final_answer(path: Path) -> str:
    if not path.exists():
        return ""

    for line in path.read_text(encoding="utf-8").splitlines():
        event = parse_rollout_line(line)
        if event.kind == "final_message" and event.text.strip():
            return event.text.strip()

    return ""


def wait_for_final_answer(path: Path, *, timeout: float = 5.0, poll_interval: float = 0.05) -> str:
    watcher = FinalAnswerWatcher(path)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in watcher.poll():
            if event.text.strip():
                return event.text.strip()
        time.sleep(poll_interval)
    return ""
