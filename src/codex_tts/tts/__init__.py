from codex_tts.tts.say import SayBackend


def build_backend(name: str):
    if name == "say":
        return SayBackend()
    raise ValueError(f"Unsupported backend: {name}")
