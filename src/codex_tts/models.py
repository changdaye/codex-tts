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


@dataclass(frozen=True)
class ThreadCandidate:
    thread_id: str
    rollout_path: Path
    created_at: int
    updated_at: int
    score: tuple[int, int]


@dataclass(frozen=True)
class ManagedSessionSnapshot:
    session_id: str
    cwd: str
    started_at: int
    status: str = "pending_bind"
    launcher_pid: int | None = None
    codex_pid: int | None = None
    thread_id: str | None = None
    rollout_path: str | None = None
    is_focus: bool = False
    is_muted: bool = False
    last_final_text: str | None = None
    last_event_at: int | None = None


@dataclass(frozen=True)
class DaemonStatusSnapshot:
    global_enabled: bool = True
    focus_session_id: str | None = None
    sessions: list[ManagedSessionSnapshot] | None = None

    def __post_init__(self) -> None:
        if self.sessions is None:
            object.__setattr__(self, "sessions", [])


@dataclass(frozen=True)
class DaemonSettings:
    global_enabled: bool = True
    updated_at: int | None = None
