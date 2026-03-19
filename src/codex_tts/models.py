from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedRolloutEvent:
    kind: str
    text: str = ""


@dataclass(frozen=True)
class ThreadRecord:
    thread_id: str
    rollout_path: Path
    created_at: int
    updated_at: int
