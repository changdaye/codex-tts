from codex_tts.models import ParsedRolloutEvent
from codex_tts.speech_policy import SpeechPolicy


def test_policy_speaks_final_message_once():
    policy = SpeechPolicy()
    event = ParsedRolloutEvent(kind="final_message", text="done")
    assert policy.should_speak(event) is True
    assert policy.should_speak(event) is False


def test_policy_rejects_non_final_messages():
    policy = SpeechPolicy()

    assert policy.should_speak(ParsedRolloutEvent(kind="ignored", text="done")) is False
