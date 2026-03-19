from codex_tts.rollout import parse_rollout_line


def test_parse_rollout_line_extracts_final_answer():
    line = (
        '{"type":"response_item","payload":{"type":"message","role":"assistant",'
        '"phase":"final_answer","content":[{"type":"output_text","text":"done"}]}}'
    )
    event = parse_rollout_line(line)
    assert event.kind == "final_message"
    assert event.text == "done"
