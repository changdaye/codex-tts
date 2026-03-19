from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class DebugLogger:
    enabled: bool = False

    def log(self, message: str) -> None:
        if self.enabled:
            print(f"codex-tts: {message}", file=sys.stderr)
