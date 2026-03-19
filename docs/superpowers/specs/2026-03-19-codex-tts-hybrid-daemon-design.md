# Codex TTS Hybrid Daemon Design

## Summary

This design defines the first background-native version of `codex-tts`.

Instead of treating `codex-tts` as a per-invocation wrapper that watches one
Codex session and speaks one stream of final replies, this phase turns it into
an always-on macOS productivity tool with three cooperating parts:

- a Python daemon that owns session discovery, rollout watching, focus
  arbitration, and speech
- a CLI that still launches interactive Codex, but now also registers launches
  with the daemon and controls it
- a macOS menubar shell that shows active sessions and lets the user choose
  which session is allowed to speak

This is intentionally the first sub-project of the broader "daily driver"
vision. It solves the core concurrency problem first: when multiple Codex
sessions exist, only the user-selected focus session should speak.

## Goals

- Preserve the existing terminal-first Codex workflow
- Make `codex-tts` useful as an always-on background tool rather than a
  one-shot wrapper
- Support multiple concurrent Codex sessions without guessing which one should
  speak
- Introduce a single explicit focus session that is allowed to produce speech
- Provide lightweight menubar visibility and control for active sessions
- Keep the current Python rollout / resolver logic as the core speech engine
- Fail safe to silence instead of speaking the wrong session

## Non-Goals For This Phase

- Full notification-center history or searchable transcript storage
- Rewriting the Python speech / watcher core in Swift
- Speaking commentary, tool chatter, or rich intermediate progress
- Cross-platform menubar support outside macOS
- Packaging cloud TTS backends in the same phase
- Fully automatic focus switching between active sessions

## Product Shape

### 1. Always-On Menubar Utility

The primary user-facing product becomes a menubar app.

Its responsibilities are intentionally narrow:

- ensure the daemon is running
- show whether speech is globally enabled
- show which session is currently focused
- show the active managed sessions
- let the user change focus or mute a session
- expose launch-at-login, logs, and quit actions

The menubar shell is not the speech engine. It is the control surface.

### 2. Python Daemon Core

The daemon becomes the single owner of runtime truth.

It maintains:

- the registry of active launches
- the mapping from launches to Codex threads / rollout files
- the watcher objects for active rollout files
- the focus session choice
- per-session mute state
- global speech enable / disable state
- the speech policy and TTS backend calls

Only the daemon decides whether a final reply is spoken.

### 3. CLI As Launcher And Control Plane

The CLI remains important, but its role changes.

- `codex-tts launch -- ...` launches real `codex` and registers the launch with
  the daemon
- `codex-tts status --json` returns daemon state for the menubar shell
- `codex-tts focus <session-id>` changes the focused session
- `codex-tts mute <session-id>` and `unmute <session-id>` control per-session
  speech
- `codex-tts enable` and `disable` control global speech
- `codex-tts daemon run` starts the daemon directly for development and manual
  recovery

For backward compatibility, plain `codex-tts -- ...` should behave like
`codex-tts launch -- ...`.

## Primary User Flows

### Flow 1: First Session Of The Day

1. The user logs in and the menubar app launches.
2. The menubar app ensures the daemon is running.
3. The user starts Codex from the terminal with `codex-tts launch -- ...`.
4. The CLI launches the real `codex` process and registers that launch with the
   daemon.
5. The daemon binds the launch to the correct Codex thread and rollout file.
6. If this is the only active session and no focus exists yet, the daemon
   auto-focuses it.
7. Final replies from that session are spoken.

### Flow 2: Multiple Concurrent Sessions

1. The user launches another Codex session in a different terminal or project.
2. The daemon registers and binds the second session, but it does not steal
   focus.
3. The menubar now shows multiple sessions.
4. The currently focused session remains the only one allowed to speak.
5. The user can switch focus from the menubar at any time.

### Flow 3: Focused Session Exits

1. The focused Codex process exits.
2. The daemon marks that session as exited.
3. Focus is cleared rather than automatically transferred.
4. Remaining sessions stay visible, but no session speaks until the user
   chooses a new focus.

This rule is conservative by design. The product should prefer silence over a
surprising voice from the wrong terminal.

### Flow 4: Daemon Missing

1. The user runs `codex-tts launch -- ...` while the daemon is not reachable.
2. The CLI attempts to connect and fails.
3. The CLI falls back to the current direct wrapper behavior for that one
   launch.
4. Codex still works and speech still works for that launch.
5. Control-plane features such as focus switching are unavailable until the
   daemon returns.

This fallback keeps the tool usable during development and during local
failures.

## Architecture

### Python Runtime Layout

The Python side should be split into explicit daemon-oriented units instead of
growing the current single-session `service.py` loop indefinitely.

Recommended responsibilities:

- `daemon.py`
  Process entrypoint, main loop, server startup, graceful shutdown
- `ipc.py`
  Local socket protocol and request / response helpers
- `session_manager.py`
  Session registry, focus rules, state transitions, watcher ownership
- `daemon_store.py`
  Small persisted settings such as global enablement and launch-at-login
  preferences exposed to the UI
- `service.py`
  Keep single-session launch fallback logic and shared speech helpers
- `session_store.py`
  Keep Codex thread resolution logic
- `rollout.py`
  Keep rollout cursor and final-answer extraction logic

The existing watcher / resolver / sanitizer code is already modular enough to
be reused. This phase should wrap it in a daemon orchestration layer rather
than replacing it.

### Native Menubar Shell

The menubar shell should be a native macOS app built with SwiftUI
`MenuBarExtra`.

Its model should stay intentionally thin:

- poll `codex-tts status --json`
- decode daemon status into simple Swift models
- invoke `codex-tts focus`, `mute`, `unmute`, `enable`, `disable`
- manage launch-at-login for the app itself

The menubar shell should not speak directly and should not read Codex rollout
files. It remains a controller, not an alternate runtime.

### Why The Menubar Should Call The CLI

The daemon still needs an IPC protocol. However, the menubar app does not need
its own duplicate socket client.

The simplest boundary is:

- daemon speaks JSON over a local Unix socket
- Python CLI is the official socket client
- menubar app shells out to the CLI for read / write actions

This keeps the Swift surface area small and makes the CLI the single
machine-readable control plane.

## Session Model

Each managed session should have a stable daemon-level identifier, separate from
the Codex thread id. A launch can exist before a Codex thread has been bound.

Recommended session fields:

- `session_id`
  Daemon-generated id for this managed launch
- `cwd`
  Launch working directory
- `started_at`
  Launch timestamp
- `launcher_pid`
  PID of the short-lived CLI wrapper process
- `codex_pid`
  PID of the real Codex process when known
- `thread_id`
  Bound Codex thread id when known
- `rollout_path`
  Bound rollout path when known
- `status`
  One of `pending_bind`, `active`, `unbound`, `exited`, `error`
- `is_focus`
  Whether this session is currently selected as the only speaking session
- `is_muted`
  Whether this session is explicitly muted
- `last_final_text`
  Most recent sanitized final reply observed for that session
- `last_event_at`
  Timestamp of last rollout or lifecycle activity

`focused` should not be a separate lifecycle state. It is an orthogonal flag
because a session can be both `active` and focused, or `pending_bind` and
pre-selected as the desired focus target.

## Focus Arbitration Rules

This is the core product behavior and must be explicit.

### Rule 1: Only One Session May Speak

At any moment, zero or one managed sessions may produce speech.

### Rule 2: Auto-Focus Only The First Session

If no focus exists and exactly one newly active session is present, the daemon
may auto-focus that first active session.

This keeps the single-session experience low-friction without reintroducing
guessing once multiple sessions exist.

### Rule 3: New Sessions Never Steal Focus

When a second or third session appears, it remains silent until the user
changes focus explicitly.

### Rule 4: Exiting Focus Clears Focus

When the focused session exits, focus is cleared. The daemon does not
automatically hand control to another active session.

### Rule 5: Unbound Sessions Stay Silent

If a launch is registered but cannot yet be bound to a reliable thread /
rollout, it may appear in the session list but it must not speak.

### Rule 6: Mute Wins Over Focus

If the focused session is muted, it remains the focused session, but speech is
suppressed until it is unmuted or focus changes.

This makes the UI model consistent: focus answers "which session is primary,"
mute answers "may this session currently emit sound."

## IPC Contract

The daemon should expose a local Unix domain socket at:

```text
~/.codex-tts/daemon.sock
```

The protocol can stay simple JSON request / response with one request per
connection.

Minimum commands for the first phase:

- `register_launch`
- `list_sessions`
- `status`
- `set_focus`
- `mute_session`
- `unmute_session`
- `set_global_enabled`
- `ping`

The CLI should expose a stable JSON format for `status --json` so the menubar
app can depend on it without learning daemon internals.

## Persistence

The daemon should persist only the settings that matter across app restarts.

Persisted:

- global speech enabled / disabled
- launch-at-login preference surfaced by the menubar app

Not persisted in MVP:

- historical session list
- focus session from a previous macOS login
- per-session mute state after a full daemon restart
- transcript history

This keeps the first background release conservative and easy to reason about.

## Failure Handling

### Safety Priorities

1. Do not break interactive Codex
2. Do not speak the wrong session
3. Do not lose the user's ability to recover control
4. Do not crash the menubar app because the daemon is unavailable

### Concrete Failure Rules

- If daemon IPC is unavailable, `codex-tts launch` falls back to direct
  single-session speech mode
- If thread binding is ambiguous, mark the session `unbound` and keep it silent
- If rollout parsing fails for one session, isolate that failure to the session
- If TTS playback fails, log the failure and continue managing sessions
- If the socket file is stale, daemon startup should replace it safely
- If the menubar app cannot reach the daemon, it should show a degraded state
  and offer a retry / restart path rather than disappearing

## Testing Strategy

### Python Tests

- Unit tests for focus arbitration rules
- Unit tests for daemon store persistence
- Unit tests for IPC request / response handling
- Integration tests for multiple fake Codex launches
- Integration tests for daemon-down fallback to direct single-session mode
- Integration tests that verify only the focused session produces speech

### Swift Tests

- Decode tests for `status --json`
- Command invocation tests for focus / mute / enable actions
- View model tests for degraded daemon-unreachable state

### Manual Verification

- Start the menubar app, confirm daemon starts
- Launch one Codex session and confirm it auto-focuses and speaks
- Launch a second Codex session and confirm it stays silent
- Switch focus from the menubar and confirm the newly focused session speaks
- Quit the focused session and confirm focus clears rather than moving
- Stop the daemon and confirm `codex-tts launch` falls back cleanly

## Phase Boundary

This phase is complete when all of the following are true:

- A background daemon can manage multiple concurrent Codex launches
- The CLI can register launches and query daemon status
- Only the focused session is eligible to speak final replies
- A menubar app shows active sessions and can change focus
- The first active session auto-focuses when no focus exists yet
- Focus clears when the focused session exits
- `codex-tts launch` still works if the daemon is unavailable
- The new runtime is documented and testable

## Future Extensions

- Notification-center style recent replies
- Per-project focus rules or pinned default focus targets
- Daemon start / stop from launchd instead of app-owned supervision
- Cloud or premium TTS backends
- Error-only and approval-needed speech modes
- Richer menu actions such as reopen project, replay last reply, or open logs
