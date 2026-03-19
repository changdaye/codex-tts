import re
from subprocess import run


class SayBackend:
    def speak(self, text: str, *, voice: str, rate: int) -> None:
        run(["say", "-v", voice, "-r", str(rate), text], check=True)

    def list_voices(self) -> list[str]:
        result = run(
            ["say", "-v", "?"],
            check=True,
            capture_output=True,
            text=True,
        )
        voices: list[str] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            match = re.split(r"\s{2,}", line.strip(), maxsplit=1)
            voices.append(match[0])
        return voices
