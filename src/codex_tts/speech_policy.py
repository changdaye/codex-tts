from codex_tts.models import ParsedRolloutEvent


class SpeechPolicy:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def should_speak(self, event: ParsedRolloutEvent) -> bool:
        if event.kind != "final_message":
            return False

        text = event.text.strip()
        if not text or text in self._seen:
            return False

        self._seen.add(text)
        return True
