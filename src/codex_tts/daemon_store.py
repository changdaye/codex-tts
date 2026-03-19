import json
from pathlib import Path

from codex_tts.models import DaemonSettings


class DaemonStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> DaemonSettings:
        if not self.path.exists():
            return DaemonSettings()

        data = json.loads(self.path.read_text(encoding="utf-8"))
        return DaemonSettings(
            global_enabled=bool(data.get("global_enabled", True)),
            updated_at=data.get("updated_at"),
        )

    def save(self, settings: DaemonSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "global_enabled": settings.global_enabled,
                    "updated_at": settings.updated_at,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
