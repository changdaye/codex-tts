# Codex TTS Design

## Summary

This project adds a local speech layer for Codex so that when an interactive Codex session finishes and emits its final reply, the reply is spoken automatically.

The first version targets the user's current primary workflow:

- Launching interactive Codex via `codex`
- Running on macOS
- Reading only the final reply
- Using a pluggable TTS interface with a default `say` backend

The delivery scope also includes repository bootstrap:

- Initialize a local Git repository
- Prepare project documentation
- Later create a private GitHub repository with GitHub CLI and push the project once authentication is valid

## Goals

- Preserve the existing interactive Codex experience
- Avoid parsing terminal UI text or ANSI output
- Detect the final reply from Codex's structured local rollout data
- Speak the final reply exactly once
- Keep the TTS backend replaceable

## Non-Goals For V1

- Speaking commentary or intermediate progress
- Running as a background daemon
- Cross-platform TTS support
- Perfect support for concurrent multi-session matching
- Cloud TTS integration out of the box

## Primary User Flow

1. The user runs `codex-tts` instead of `codex`.
2. `codex-tts` launches the real interactive Codex CLI and transparently forwards terminal I/O.
3. In parallel, `codex-tts` watches Codex's local thread metadata and rollout file for the newly created session.
4. When Codex writes a structured assistant event for `phase:"final_answer"`, `codex-tts` extracts the final text.
5. The text is sent to the configured TTS backend.
6. The reply is spoken once through the local audio output.

## Architecture

### 1. CLI Wrapper

`codex-tts` is a launcher that behaves like a thin wrapper around the normal `codex` command.

Responsibilities:

- Accept user arguments intended for Codex
- Launch the real `codex`
- Keep terminal behavior as close to native as possible
- Manage the lifecycle of the watcher and TTS components

### 2. Session Resolver

The wrapper identifies the correct Codex thread by observing local Codex state after launch.

Primary data sources:

- `~/.codex/state_5.sqlite`
- `threads.rollout_path`
- `~/.codex/sessions/.../rollout-*.jsonl`

Matching heuristics for V1:

- Match the current working directory
- Prefer threads created or updated after `codex-tts` started
- Confirm that the referenced rollout file is actively growing
- Bind only one primary thread per launcher process

If no unique thread can be identified, the wrapper must fail safe and skip speech.

### 3. Rollout Watcher

The watcher tails the rollout JSONL file and parses structured events.

Relevant structured event forms already observed locally:

- `event_msg.payload.type == "agent_message"`
- `response_item.payload.type == "message"`
- `response_item.payload.phase == "final_answer"`
- `event_msg.payload.type == "task_complete"`

V1 completion rule:

- Speak only assistant text from `response_item.payload.phase == "final_answer"`

Fallback handling:

- If no `final_answer` appears, do not speak
- `task_complete.last_agent_message` may be retained as a future fallback, but is not required for V1 behavior

### 4. Speech Policy

V1 policy is intentionally narrow:

- Speak only the final reply
- Ignore commentary
- Ignore tool events, token counters, and status events
- Speak the same normalized text at most once

### 5. TTS Adapter Layer

The system exposes a thin backend interface:

```text
speak(text, options) -> Result
```

V1 backend:

- `macos-say`

Planned future backends:

- OpenAI
- ElevenLabs
- Edge TTS

The event parser and speech policy must not depend on backend-specific details.

## Configuration

Planned config location:

- `~/.codex-tts/config.toml`

Initial config surface:

```toml
backend = "say"
voice = "Tingting"
rate = 180
speak_phase = "final_only"
```

V1 should run with sensible defaults even if the config file does not exist.

## Failure Handling

The system must not interfere with normal Codex usage.

Fail-safe rules:

- If the session cannot be matched, skip speech
- If the rollout file cannot be parsed, skip speech
- If the backend fails, log to stderr and keep Codex running
- If no final answer is found, exit silently

Priority order:

1. Do not break Codex
2. Do not read the wrong session
3. Speak only when the signal is reliable

## Testing Strategy

### Unit Tests

- Parse representative rollout JSON lines
- Verify that only `final_answer` events produce a speech candidate
- Verify text normalization and deduplication

### Integration Tests

- Simulate a rollout file that is appended over time
- Verify that the watcher detects the final reply once
- Verify that non-final events do not trigger speech

### Manual Verification

- Launch a real interactive `codex-tts` session on macOS
- Complete a short prompt
- Confirm that the final reply is spoken once and only once

## Delivery Plan Additions

In addition to the core feature, the project should include:

- A local Git repository
- A clear README
- Private GitHub repository creation with GitHub CLI
- Initial push to GitHub

Current constraint:

- `gh auth status` reports that the active GitHub token is invalid, so private repository creation and push cannot be completed until authentication is fixed

## V1 Scope Boundary

V1 is complete when all of the following are true:

- Running `codex-tts` launches interactive Codex
- The wrapper finds the correct rollout file for the launched session
- Only the final assistant reply is spoken
- Speech uses the macOS `say` backend by default
- The system degrades safely when matching or speech fails
- Core behavior is documented and testable

## Future Extensions

- Error or attention-needed speech modes
- A daemon mode
- Cross-platform backends
- Better multi-session disambiguation
- Richer per-project voice settings
