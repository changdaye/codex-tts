import json

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
