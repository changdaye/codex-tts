from subprocess import run


class SayBackend:
    def speak(self, text: str, *, voice: str, rate: int) -> None:
        run(["say", "-v", voice, "-r", str(rate), text], check=True)
