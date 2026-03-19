import os
import subprocess
import time
from pathlib import Path

from codex_tts.config import AppConfig
from codex_tts.models import ParsedRolloutEvent
from codex_tts.rollout import wait_for_final_answer
from codex_tts.session_store import list_thread_ids, resolve_active_thread
from codex_tts.speech_policy import SpeechPolicy
from codex_tts.tts import build_backend


def speak_text(text: str, config: AppConfig) -> None:
    backend = build_backend(config.backend)
    backend.speak(text, voice=config.voice, rate=config.rate)


def wait_for_active_thread(
    state_db: Path,
    *,
    cwd: Path,
    started_at: int,
    known_thread_ids: set[str],
    timeout: float = 5.0,
    poll_interval: float = 0.05,
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        thread = resolve_active_thread(
            state_db,
            cwd=str(cwd),
            started_at=started_at,
            known_thread_ids=known_thread_ids,
        )
        if thread is not None:
            return thread
        time.sleep(poll_interval)
    return None


def run_session(
    codex_cmd: list[str],
    config: AppConfig,
    state_db: Path,
    home_dir: Path,
    cwd: Path,
) -> int:
    started_at = int(time.time())
    known_thread_ids = list_thread_ids(state_db)
    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    process = subprocess.Popen(codex_cmd, cwd=str(cwd), env=env)
    policy = SpeechPolicy()

    thread = wait_for_active_thread(
        state_db,
        cwd=cwd,
        started_at=started_at,
        known_thread_ids=known_thread_ids,
    )
    if thread is not None:
        final_text = wait_for_final_answer(thread.rollout_path)
        event = ParsedRolloutEvent(kind="final_message", text=final_text)
        if policy.should_speak(event):
            speak_text(final_text, config)

    return process.wait()
