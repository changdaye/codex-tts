import json
from pathlib import Path

from codex_tts.rollout import FinalAnswerWatcher, parse_rollout_line


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
