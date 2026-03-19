# Codex TTS Hybrid Daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `codex-tts` into a macOS background utility with a Python daemon, a CLI control plane, and a menubar shell so only the focused Codex session is allowed to speak.

**Architecture:** Extend the current Python watcher / speech core into a long-lived daemon that owns session discovery, focus arbitration, and speech decisions. Keep the CLI as both launcher and machine-readable control plane, and build a thin SwiftUI menubar app that polls CLI JSON and issues control commands instead of duplicating daemon logic.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `dataclasses`, `json`, `pathlib`, `selectors`, `socket`, `sqlite3`, `subprocess`, `threading`, `time`, `uuid`), `pytest`, Swift 5.10+, SwiftUI / AppKit for `MenuBarExtra`

---

## Scope Guard

This plan covers the first background-native subproject only:

- Python daemon runtime
- multi-session focus control
- CLI launcher / control commands
- menubar shell for focus switching and status

It does **not** include:

- transcript history
- notification center UI
- cloud TTS backends
- cross-platform desktop UI
- packaging a standalone notarized macOS app bundle

## File Structure

- Create: `docs/superpowers/specs/2026-03-19-codex-tts-hybrid-daemon-design.md`
  Product and architecture spec for this phase
- Create: `docs/superpowers/plans/2026-03-19-codex-tts-hybrid-daemon.md`
  This implementation plan
- Create: `src/codex_tts/ipc.py`
  Local Unix socket client / server helpers and JSON request / response framing
- Create: `src/codex_tts/daemon_store.py`
  Persisted daemon settings such as global enablement
- Create: `src/codex_tts/session_manager.py`
  Managed session lifecycle, focus arbitration, watcher ownership, and speech gating
- Create: `src/codex_tts/daemon.py`
  Daemon entrypoint and main event loop
- Modify: `src/codex_tts/models.py`
  Add daemon session snapshots, control request / response payloads, and settings models
- Modify: `src/codex_tts/config.py`
  Add daemon path helpers and optional daemon-related config defaults
- Modify: `src/codex_tts/cli.py`
  Add `launch`, `status`, `focus`, `mute`, `unmute`, `enable`, `disable`, and `daemon run`
- Modify: `src/codex_tts/service.py`
  Keep direct single-session fallback and shared speech helper paths
- Modify: `src/codex_tts/__init__.py`
  Export version or shared constants if needed by daemon / app integration
- Modify: `README.md`
  Document daemon mode, menubar workflow, and new CLI commands
- Modify: `README.en.md`
  English doc parity
- Modify: `README.ja.md`
  Japanese doc parity
- Modify: `README.ko.md`
  Korean doc parity
- Create: `tests/test_ipc.py`
  Unix socket and request framing tests
- Create: `tests/test_daemon_store.py`
  Persisted settings tests
- Create: `tests/test_session_manager.py`
  Focus arbitration and multi-session lifecycle tests
- Create: `tests/test_daemon.py`
  Daemon main loop and fallback integration tests
- Modify: `tests/test_service.py`
  Cover daemon-unavailable fallback and shared speech helpers
- Modify: `tests/test_cli.py`
  Cover new CLI subcommands and backward-compatible `launch` alias behavior
- Modify: `tests/fixtures/fake_codex.py`
  Support multiple fake Codex launches and controllable exit timing
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar.xcodeproj/project.pbxproj`
  Native macOS menubar app project
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/CodexTTSMenuBarApp.swift`
  `MenuBarExtra` entrypoint
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/MenuBarViewModel.swift`
  Poll `codex-tts status --json` and expose menu actions
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/CLIClient.swift`
  Shell out to `codex-tts` control commands and decode JSON output
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/Models.swift`
  Swift status snapshot decoding types
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/LoginItemManager.swift`
  Launch-at-login support for the menubar app
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBarTests/CLIClientTests.swift`
  Decode and command execution tests for the macOS shell

## Implementation Notes

- Preserve the current speech behavior: only final replies may be spoken.
- The daemon is the single speech authority. The menubar app must never call TTS.
- `codex-tts -- ...` should remain a valid user entrypoint by mapping to `launch`.
- Use a local Unix socket for daemon IPC, but keep the CLI as the only public machine-facing client.
- Menubar actions should shell out to the CLI instead of speaking daemon protocol directly.
- Auto-focus only the first active session when no focus exists. Never auto-steal focus from an existing active session.
- When the focused session exits, clear focus instead of transferring it automatically.
- Prefer silence over wrong speech in every ambiguous state.
- Use TDD for each slice. Begin every task with failing tests.

### Task 1: Introduce Daemon Models And Path Helpers

**Files:**
- Modify: `src/codex_tts/models.py`
- Modify: `src/codex_tts/config.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing config and model tests**

```python
from codex_tts.config import daemon_socket_path, daemon_state_path


def test_daemon_socket_path_defaults_under_codex_tts_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert daemon_socket_path() == tmp_path / ".codex-tts" / "daemon.sock"


def test_status_snapshot_defaults_to_global_enabled():
    snapshot = DaemonStatusSnapshot()
    assert snapshot.global_enabled is True
    assert snapshot.sessions == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_config.py tests/test_cli.py -q`
Expected: FAIL because daemon path helpers and daemon snapshot models do not exist yet.

- [ ] **Step 3: Add daemon-facing shared dataclasses and config helpers**

Implement:

- `ManagedSessionSnapshot`
- `DaemonStatusSnapshot`
- `DaemonSettings`
- `daemon_root_path()`
- `daemon_socket_path()`
- `daemon_state_path()`

Keep the existing config behavior unchanged for the direct wrapper path.

- [ ] **Step 4: Run the focused tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_config.py tests/test_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/codex_tts/models.py src/codex_tts/config.py tests/test_config.py tests/test_cli.py
git commit -m "feat: add daemon runtime models"
```

### Task 2: Add Unix Socket IPC And Persisted Daemon Settings

**Files:**
- Create: `src/codex_tts/ipc.py`
- Create: `src/codex_tts/daemon_store.py`
- Create: `tests/test_ipc.py`
- Create: `tests/test_daemon_store.py`

- [ ] **Step 1: Write the failing IPC and store tests**

```python
def test_ipc_round_trip_returns_json_response(tmp_path):
    ...


def test_daemon_store_persists_global_enabled(tmp_path):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_ipc.py tests/test_daemon_store.py -q`
Expected: FAIL because the IPC helpers and daemon store do not exist.

- [ ] **Step 3: Implement minimal JSON-over-socket helpers**

Implement:

- one request / one response per connection
- newline-terminated JSON messages
- safe stale-socket cleanup before server bind
- a small `call_daemon()` client helper used by the CLI

- [ ] **Step 4: Implement minimal persisted settings store**

Persist:

- `global_enabled`
- optional lightweight metadata such as `updated_at`

Do not persist session history or focus state in this task.

- [ ] **Step 5: Run the focused tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_ipc.py tests/test_daemon_store.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/codex_tts/ipc.py src/codex_tts/daemon_store.py tests/test_ipc.py tests/test_daemon_store.py
git commit -m "feat: add daemon ipc and settings store"
```

### Task 3: Implement Multi-Session Registry And Focus Arbitration

**Files:**
- Create: `src/codex_tts/session_manager.py`
- Modify: `src/codex_tts/service.py`
- Modify: `tests/test_service.py`
- Create: `tests/test_session_manager.py`

- [ ] **Step 1: Write the failing multi-session behavior tests**

```python
def test_first_active_session_auto_focuses():
    ...


def test_new_active_session_does_not_steal_focus():
    ...


def test_exiting_focus_clears_focus_without_reassigning():
    ...


def test_only_focused_session_is_allowed_to_speak():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_session_manager.py tests/test_service.py -q`
Expected: FAIL because no daemon session manager or focus rules exist yet.

- [ ] **Step 3: Implement managed-session state and focus rules**

Implement a manager that can:

- register launches before thread binding
- bind launches to `thread_id` and `rollout_path`
- mark sessions `pending_bind`, `active`, `unbound`, `exited`, or `error`
- auto-focus the first active session if no focus exists
- leave focus unchanged when new sessions appear
- clear focus when the focused session exits
- gate speech by `global_enabled`, `is_muted`, and `is_focus`

- [ ] **Step 4: Reuse shared speech helpers instead of duplicating TTS calls**

Move any common "sanitize + policy + speak" helpers into reusable functions that
the daemon path can call without rewriting the direct wrapper behavior.

- [ ] **Step 5: Run the focused tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_session_manager.py tests/test_service.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/codex_tts/session_manager.py src/codex_tts/service.py tests/test_session_manager.py tests/test_service.py
git commit -m "feat: add multi-session focus arbitration"
```

### Task 4: Add Daemon Runtime And Control Commands

**Files:**
- Create: `src/codex_tts/daemon.py`
- Modify: `src/codex_tts/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_daemon.py`

- [ ] **Step 1: Write the failing daemon and CLI command tests**

```python
def test_cli_launch_aliases_plain_passthrough_args():
    ...


def test_cli_status_json_reads_daemon_snapshot():
    ...


def test_launch_falls_back_to_direct_mode_when_daemon_unavailable():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_cli.py tests/test_daemon.py -q`
Expected: FAIL because the daemon runtime and control commands do not exist.

- [ ] **Step 3: Implement daemon entrypoint and request handlers**

Support:

- `ping`
- `status`
- `register_launch`
- `set_focus`
- `mute_session`
- `unmute_session`
- `set_global_enabled`

Run the manager loop on a short poll interval that reuses the existing rollout
cursor and session resolver.

- [ ] **Step 4: Extend the CLI parser and command dispatch**

Add:

- `launch`
- `daemon run`
- `status --json`
- `focus`
- `mute`
- `unmute`
- `enable`
- `disable`

Keep `codex-tts -- ...` equivalent to `codex-tts launch -- ...`.

- [ ] **Step 5: Implement direct fallback for `launch`**

If daemon connection fails:

- launch Codex normally
- use the existing single-session wrapper flow
- do not crash

- [ ] **Step 6: Run the focused tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_cli.py tests/test_daemon.py tests/test_service.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/codex_tts/daemon.py src/codex_tts/cli.py tests/test_cli.py tests/test_daemon.py tests/test_service.py
git commit -m "feat: add daemon runtime and control cli"
```

### Task 5: Verify Multi-Session Integration With Fake Codex Processes

**Files:**
- Modify: `tests/fixtures/fake_codex.py`
- Modify: `tests/test_daemon.py`
- Modify: `tests/test_rollout.py`

- [ ] **Step 1: Write the failing integration tests**

```python
def test_daemon_tracks_two_sessions_but_only_speaks_focused_one(tmp_path):
    ...


def test_focus_change_allows_new_session_to_speak(tmp_path):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_daemon.py tests/test_rollout.py -q`
Expected: FAIL because the current fixture only models a simpler single-session flow.

- [ ] **Step 3: Extend the fake Codex fixture**

Support:

- multiple concurrent launches
- controllable final-answer timing
- delayed exit
- multiple rollout files

- [ ] **Step 4: Finish daemon integration behavior**

Use the fixture to verify:

- first session auto-focuses
- second session stays silent
- changing focus changes which session may speak
- focused exit clears focus

- [ ] **Step 5: Run the focused tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_daemon.py tests/test_rollout.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/fake_codex.py tests/test_daemon.py tests/test_rollout.py
git commit -m "test: cover multi-session daemon flow"
```

### Task 6: Build The Menubar Shell

**Files:**
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar.xcodeproj/project.pbxproj`
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/CodexTTSMenuBarApp.swift`
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/MenuBarViewModel.swift`
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/CLIClient.swift`
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/Models.swift`
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBar/LoginItemManager.swift`
- Create: `macos/CodexTTSMenuBar/CodexTTSMenuBarTests/CLIClientTests.swift`

- [ ] **Step 1: Write the failing Swift tests for CLI JSON decoding**

Write tests that decode a representative `status --json` payload and verify the
client invokes `focus` and `mute` commands correctly.

- [ ] **Step 2: Run the Swift tests to verify they fail**

Run: `xcodebuild test -project macos/CodexTTSMenuBar/CodexTTSMenuBar.xcodeproj -scheme CodexTTSMenuBar -destination 'platform=macOS'`
Expected: FAIL because the macOS shell project and CLI client do not exist.

- [ ] **Step 3: Implement the thin CLI-backed menubar client**

Build:

- `CLIClient` that runs `codex-tts status --json`
- JSON decoding types that mirror the Python snapshot
- action methods for focus / mute / enable / disable

- [ ] **Step 4: Implement the `MenuBarExtra` UI**

Display:

- daemon reachable / unreachable state
- global enabled toggle
- current focus summary
- active session list ordered by recency
- per-session focus and mute actions
- launch-at-login toggle
- quit action

Do not add transcript history or replay controls in this task.

- [ ] **Step 5: Hook up daemon supervision for the menubar app**

On launch:

- ensure the daemon is running, or start it in development mode
- poll status on a short interval
- surface degraded state if the daemon cannot be reached

- [ ] **Step 6: Run the Swift tests again**

Run: `xcodebuild test -project macos/CodexTTSMenuBar/CodexTTSMenuBar.xcodeproj -scheme CodexTTSMenuBar -destination 'platform=macOS'`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add macos/CodexTTSMenuBar
git commit -m "feat: add macos menubar shell"
```

### Task 7: Document The Background Workflow

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `README.ja.md`
- Modify: `README.ko.md`

- [ ] **Step 1: Write the failing documentation checklist**

Capture a short checklist that verifies the docs explain:

- daemon mode
- launch command
- focus semantics
- daemon-down fallback
- menubar workflow

- [ ] **Step 2: Update the READMEs**

Document:

- `codex-tts launch`
- `codex-tts status --json`
- menubar-driven focus switching
- "only focused session speaks"
- daemon unavailable fallback
- development instructions for the macOS shell

- [ ] **Step 3: Run the full Python test suite**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: PASS

- [ ] **Step 4: Run the macOS shell tests**

Run: `xcodebuild test -project macos/CodexTTSMenuBar/CodexTTSMenuBar.xcodeproj -scheme CodexTTSMenuBar -destination 'platform=macOS'`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md README.en.md README.ja.md README.ko.md
git commit -m "docs: add daemon and menubar workflow"
```

## Manual Verification Checklist

After implementation:

1. Start the menubar app and confirm it reports the daemon as reachable.
2. Launch one Codex session with `codex-tts launch -- --no-alt-screen` and confirm it auto-focuses.
3. Launch a second Codex session and confirm it appears in the menu but does not speak.
4. Switch focus from the menubar and confirm the newly focused session speaks the next final reply.
5. Mute the focused session and confirm speech stops without changing focus.
6. Exit the focused session and confirm focus clears instead of moving automatically.
7. Stop the daemon and confirm `codex-tts launch` still works in direct fallback mode.
