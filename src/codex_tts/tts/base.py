from typing import Protocol


class TTSBackend(Protocol):
    def speak(self, text: str, *, voice: str, rate: int) -> None:
        ...

    def list_voices(self) -> list[str]:
        ...
