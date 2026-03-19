import os
import subprocess
import sys
import time
from pathlib import Path

from codex_tts.config import AppConfig
from codex_tts.rollout import FinalAnswerWatcher
from codex_tts.session_store import list_thread_ids, resolve_active_thread
from codex_tts.speech_policy import SpeechPolicy
from codex_tts.tts import build_backend


def speak_text(text: str, config: AppConfig) -> None:
    backend = build_backend(config.backend)
    backend.speak(text, voice=config.voice, rate=config.rate)


def handle_rollout_events(
    watcher: FinalAnswerWatcher,
    policy: SpeechPolicy,
    config: AppConfig,
) -> None:
    for event in watcher.poll():
        if not policy.should_speak(event):
            continue
        try:
            speak_text(event.text, config)
        except Exception as exc:
            print(f"codex-tts: speech failed: {exc}", file=sys.stderr)


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
    thread = None
    watcher = None

    while True:
        if thread is None:
            thread = resolve_active_thread(
                state_db,
                cwd=str(cwd),
                started_at=started_at,
                known_thread_ids=known_thread_ids,
            )
            if thread is not None:
                watcher = FinalAnswerWatcher(thread.rollout_path)

        if watcher is not None:
            handle_rollout_events(watcher, policy, config)

        exit_code = process.poll()
        if exit_code is not None:
            break

        time.sleep(0.05)

    if thread is None:
        thread = resolve_active_thread(
            state_db,
            cwd=str(cwd),
            started_at=started_at,
            known_thread_ids=known_thread_ids,
        )
        if thread is not None:
            watcher = FinalAnswerWatcher(thread.rollout_path)

    if watcher is not None:
        handle_rollout_events(watcher, policy, config)

    return exit_code
