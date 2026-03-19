from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class AppConfig:
    backend: str = "say"
    voice: str = "Tingting"
    rate: int = 180
    speak_phase: str = "final_only"


def default_config_path() -> Path:
    return Path.home() / ".codex-tts" / "config.toml"


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return AppConfig(
        backend=data.get("backend", "say"),
        voice=data.get("voice", "Tingting"),
        rate=int(data.get("rate", 180)),
        speak_phase=data.get("speak_phase", "final_only"),
    )
