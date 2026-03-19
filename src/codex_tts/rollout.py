import json
import time
from pathlib import Path

from codex_tts.models import ParsedRolloutEvent


TAIL_CHECK_SIZE = 64


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


class RolloutCursor:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self._file_id: tuple[int, int] | None = None
        self._pending = ""
        self._tail = ""

    def read_new_lines(self) -> list[str]:
        try:
            stat = self.path.stat()
        except FileNotFoundError:
            self._reset()
            return []

        file_id = (stat.st_dev, stat.st_ino)
        if self._should_reset(file_id, stat.st_size):
            self._reset(file_id=file_id)

        with self.path.open("r", encoding="utf-8") as handle:
            handle.seek(self.offset)
            chunk = handle.read()
            self.offset = handle.tell()

        if not chunk:
            self._file_id = file_id
            return []

        self._file_id = file_id
        self._tail = (self._tail + chunk)[-TAIL_CHECK_SIZE:]
        return self._extract_complete_lines(chunk)

    def _should_reset(self, file_id: tuple[int, int], size: int) -> bool:
        if self._file_id is None:
            return False
        if file_id != self._file_id:
            return True
        if size < self.offset:
            return True
        if self.offset == 0 or not self._tail or size < len(self._tail):
            return False

        with self.path.open("r", encoding="utf-8") as handle:
            handle.seek(self.offset - len(self._tail))
            return handle.read(len(self._tail)) != self._tail

    def _extract_complete_lines(self, chunk: str) -> list[str]:
        buffer = self._pending + chunk
        complete_lines: list[str] = []
        self._pending = ""
        for part in buffer.splitlines(keepends=True):
            if part.endswith(("\n", "\r")):
                complete_lines.append(part.rstrip("\r\n"))
            else:
                self._pending = part
        return complete_lines

    def _reset(self, *, file_id: tuple[int, int] | None = None) -> None:
        self.offset = 0
        self._file_id = file_id
        self._pending = ""
        self._tail = ""


class FinalAnswerWatcher:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._cursor = RolloutCursor(path)

    def poll(self) -> list[ParsedRolloutEvent]:
        events = [parse_rollout_line(line) for line in self._cursor.read_new_lines()]
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
