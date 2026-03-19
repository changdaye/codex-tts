from dataclasses import dataclass
from pathlib import Path
import tomllib

SUPPORTED_BACKENDS = {"say"}
SUPPORTED_SPEAK_PHASES = {"final_only"}


@dataclass(frozen=True)
class AppConfig:
    backend: str = "say"
    voice: str = "Tingting"
    rate: int = 180
    speak_phase: str = "final_only"
    verbose: bool = False


def default_config_path() -> Path:
    return Path.home() / ".codex-tts" / "config.toml"


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return AppConfig(
        backend=normalize_backend(data.get("backend", "say")),
        voice=normalize_voice(data.get("voice", "Tingting")),
        rate=normalize_rate(data.get("rate", 180)),
        speak_phase=normalize_speak_phase(data.get("speak_phase", "final_only")),
        verbose=normalize_verbose(data.get("verbose", False)),
    )


def normalize_backend(value: object) -> str:
    backend = normalize_non_empty_string(value, field_name="backend")
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(f"backend must be one of: {', '.join(sorted(SUPPORTED_BACKENDS))}")
    return backend


def normalize_voice(value: object) -> str:
    return normalize_non_empty_string(value, field_name="voice")


def normalize_rate(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("rate must be greater than 0")
    try:
        rate = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rate must be greater than 0") from exc
    if rate <= 0:
        raise ValueError("rate must be greater than 0")
    return rate


def normalize_speak_phase(value: object) -> str:
    speak_phase = normalize_non_empty_string(value, field_name="speak_phase")
    if speak_phase not in SUPPORTED_SPEAK_PHASES:
        raise ValueError(
            f"speak_phase must be one of: {', '.join(sorted(SUPPORTED_SPEAK_PHASES))}"
        )
    return speak_phase


def normalize_verbose(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError("verbose must be true or false")
    return value


def normalize_non_empty_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must not be empty")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized
