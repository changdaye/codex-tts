import json
from pathlib import Path

from codex_tts.rollout import (
    FinalAnswerWatcher,
    RolloutCursor,
    parse_rollout_line,
    read_final_answer,
    read_new_events,
    wait_for_final_answer,
)


def build_final_answer_line(text: str) -> str:
    payload = {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "assistant",
            "phase": "final_answer",
            "content": [{"type": "output_text", "text": text}],
        },
    }
    return json.dumps(payload) + "\n"


def append_final_answer(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(build_final_answer_line(text))


def test_parse_rollout_line_extracts_final_answer():
    line = (
        '{"type":"response_item","payload":{"type":"message","role":"assistant",'
        '"phase":"final_answer","content":[{"type":"output_text","text":"done"}]}}'
    )
    event = parse_rollout_line(line)
    assert event.kind == "final_message"
    assert event.text == "done"


def test_parse_rollout_line_marks_non_final_rows_as_ignored():
    line = '{"type":"other","payload":{"type":"message","role":"assistant","phase":"commentary"}}'

    assert parse_rollout_line(line).kind == "ignored"


def test_read_new_events_returns_empty_for_missing_file(tmp_path):
    events, next_line = read_new_events(tmp_path / "missing.jsonl", start_line=3)

    assert events == []
    assert next_line == 3


def test_read_new_events_resets_when_start_line_is_past_end(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    append_final_answer(rollout_path, "first")

    events, next_line = read_new_events(rollout_path, start_line=5)

    assert [event.text for event in events] == ["first"]
    assert next_line == 1


def test_final_answer_watcher_only_returns_new_lines(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    watcher = FinalAnswerWatcher(rollout_path)

    append_final_answer(rollout_path, "first")
    assert [event.text for event in watcher.poll()] == ["first"]

    replacement_path = tmp_path / "replacement.jsonl"
    replacement_path.write_text(build_final_answer_line("second"), encoding="utf-8")
    replacement_path.replace(rollout_path)

    assert [event.text for event in watcher.poll()] == ["second"]


def test_final_answer_watcher_recovers_from_rollout_truncation(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    watcher = FinalAnswerWatcher(rollout_path)

    append_final_answer(rollout_path, "first")
    assert [event.text for event in watcher.poll()] == ["first"]

    rollout_path.write_text("", encoding="utf-8")
    append_final_answer(rollout_path, "second")

    assert [event.text for event in watcher.poll()] == ["second"]


def test_rollout_cursor_returns_no_lines_when_file_is_missing(tmp_path):
    cursor = RolloutCursor(tmp_path / "missing.jsonl")

    assert cursor.read_new_lines() == []


def test_rollout_cursor_buffers_partial_lines_until_newline(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    cursor = RolloutCursor(rollout_path)
    rollout_path.write_text(build_final_answer_line("first").rstrip("\n"), encoding="utf-8")

    assert cursor.read_new_lines() == []

    with rollout_path.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    assert cursor.read_new_lines() == [build_final_answer_line("first").rstrip("\n")]


def test_rollout_cursor_detects_truncation_when_size_is_smaller_than_offset(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    cursor = RolloutCursor(rollout_path)
    rollout_path.write_text(build_final_answer_line("first"), encoding="utf-8")
    cursor.read_new_lines()
    stat = rollout_path.stat()

    assert cursor._should_reset((stat.st_dev, stat.st_ino), size=1) is True


def test_read_final_answer_returns_first_final_message(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    append_final_answer(rollout_path, "first")
    append_final_answer(rollout_path, "second")

    assert read_final_answer(rollout_path) == "first"


def test_read_final_answer_returns_empty_when_missing(tmp_path):
    assert read_final_answer(tmp_path / "missing.jsonl") == ""


def test_read_final_answer_returns_empty_when_file_has_no_final_message(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    rollout_path.write_text('{"type":"other"}\n', encoding="utf-8")

    assert read_final_answer(rollout_path) == ""


def test_wait_for_final_answer_returns_text_when_available(tmp_path):
    rollout_path = tmp_path / "rollout.jsonl"
    append_final_answer(rollout_path, "ready")

    assert wait_for_final_answer(rollout_path, timeout=0.01) == "ready"


def test_wait_for_final_answer_times_out_when_no_event_arrives(tmp_path, monkeypatch):
    monotonic_values = iter([0.0, 0.03])
    monkeypatch.setattr("codex_tts.rollout.time.monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr("codex_tts.rollout.time.sleep", lambda interval: None)

    assert wait_for_final_answer(tmp_path / "missing.jsonl", timeout=0.01) == ""


def test_wait_for_final_answer_sleeps_between_polls_until_event_arrives(tmp_path, monkeypatch):
    sleep_calls: list[float] = []

    class FakeWatcher:
        def __init__(self, path):
            self.calls = 0

        def poll(self):
            self.calls += 1
            if self.calls == 1:
                return []
            return [parse_rollout_line(build_final_answer_line("ready").rstrip("\n"))]

    monotonic_values = iter([0.0, 0.01, 0.02])
    monkeypatch.setattr("codex_tts.rollout.FinalAnswerWatcher", FakeWatcher)
    monkeypatch.setattr("codex_tts.rollout.time.monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr("codex_tts.rollout.time.sleep", lambda interval: sleep_calls.append(interval))

    assert wait_for_final_answer(tmp_path / "rollout.jsonl", timeout=0.05, poll_interval=0.01) == "ready"
    assert sleep_calls == [0.01]
