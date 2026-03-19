# codex-tts

Language: [简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

`codex-tts` is a local speech wrapper for the interactive `codex` CLI. You start Codex through it, it watches local Codex rollout data, and it reads each new assistant `final_answer` aloud.

## What Problem It Solves

If you mainly use Codex in a terminal, you usually hit one of these situations:

- Codex already finished, but you are focused on another window
- You only care about the final result and do not want spoken progress updates
- You want speech support without modifying Codex itself

`codex-tts` keeps that scope intentionally narrow. It does not patch Codex. It adds a local speech layer around it.

## Current Capabilities

- Reads final replies only, not `commentary`
- Targets macOS and uses the system `say` command by default
- Keeps speaking new `final_answer` messages within the same Codex session
- Supports runtime overrides for voice, absolute rate, multipliers, and named presets
- Sanitizes spoken text before playback, removing bare URLs and keeping only link labels for Markdown links
- Never blocks or crashes the Codex session if speech playback fails
- Supports `--verbose` stderr diagnostics for thread matching and skipped playback
- Supports a background daemon runtime with multi-session focus control
- Includes a native macOS menubar shell for session visibility and focus switching

## Requirements

- macOS
- Python `3.11+`
- `codex` installed and available in `PATH`
- Working macOS `say`
- Access to local `~/.codex` state and session files

## Installation

### Option 1: Install as a global command

This is the recommended path. After installation, you can run `codex-tts` from any directory.

```bash
cd /path/to/codex-tts
bash scripts/bootstrap.sh
bash scripts/install.sh
```

The installer writes the launcher to:

```text
~/.local/bin/codex-tts
```

If your shell does not already include `~/.local/bin` in `PATH`, add it:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

You can also choose a custom install directory:

```bash
CODEX_TTS_INSTALL_DIR="$HOME/bin" bash scripts/install.sh
```

The installer checks that you are in the repository root and that `.venv/bin/python` exists. If the environment is not ready yet, it tells you to run `bash scripts/bootstrap.sh` first. It also warns if `codex` is not currently in `PATH`.

### Option 2: Run directly from source

If you do not want a global command yet, run it from the repository:

```bash
cd /path/to/codex-tts
bash scripts/bootstrap.sh
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

This avoids any `PATH` changes, but you need to run from the repo context.

### Uninstall the global launcher

If you no longer want the global command:

```bash
cd /path/to/codex-tts
bash scripts/uninstall.sh
```

This only removes `~/.local/bin/codex-tts`. It does not remove the repository, `.venv`, or your config file.

## Quick Start

If you installed the global launcher, the shortest command is:

```bash
codex-tts launch --preset ultra -- --no-alt-screen
```

If you are running from source, use:

```bash
PYTHONPATH=src python -m codex_tts.cli launch --preset ultra -- --no-alt-screen
```

Once Codex opens, send a short test prompt such as:

```text
Please reply with exactly: test successful
```

Expected behavior:

- No spoken progress updates during execution
- One spoken message when the final answer appears
- Later final answers in the same session are also spoken
- URLs inside replies are not spoken aloud

## Common Usage

Basic start:

```bash
codex-tts -- --no-alt-screen
```

Change voice and use a named preset:

```bash
codex-tts --voice Tingting --preset faster -- --no-alt-screen
```

Use a multiplier:

```bash
codex-tts --speed 3 -- --no-alt-screen
```

Set an absolute speech rate:

```bash
codex-tts --rate 540 -- --no-alt-screen
```

List available system voices:

```bash
codex-tts --list-voices
```

Print debug diagnostics:

```bash
codex-tts --verbose -- --no-alt-screen
```

Use a specific config file:

```bash
codex-tts --config ~/.codex-tts/config.toml -- --no-alt-screen
```

Notes:

- Arguments before `--` belong to `codex-tts`
- Arguments after `--` are passed through to the real `codex` command

## Command Reference

| Option | Type | Description |
| --- | --- | --- |
| `--config` | `Path` | Config file path, default `~/.codex-tts/config.toml` |
| `--voice` | `str` | Override the configured voice for this run |
| `--rate` | `int` | Set an absolute speech rate for this run |
| `--speed` | `float` | Multiply the current speech rate, for example `3` |
| `--preset` | `str` | Apply a named speech-rate preset |
| `--list-voices` | flag | Print available voices and exit |
| `--verbose` | flag | Print thread-selection and skip diagnostics to stderr |

Rules:

- `--rate`, `--speed`, and `--preset` are mutually exclusive
- If none of them is provided, the config file value is used
- `--voice` can be combined with `--rate`, `--speed`, or `--preset`

## Rate Presets

| Preset | Final Rate |
| --- | --- |
| `normal` | `180` |
| `fast` | `270` |
| `faster` | `360` |
| `ultra` | `540` |

If you already know the exact rate you want, use `--rate` directly.

## Configuration

Default config path:

```text
~/.codex-tts/config.toml
```

Example:

```toml
backend = "say"
voice = "Tingting"
rate = 180
speak_phase = "final_only"
verbose = false
```

Fields:

| Field | Default | Description |
| --- | --- | --- |
| `backend` | `"say"` | Speech backend. Only macOS `say` is supported today |
| `voice` | `"Tingting"` | Default voice |
| `rate` | `180` | Default speech rate |
| `speak_phase` | `"final_only"` | Only final-answer playback is supported today |
| `verbose` | `false` | Whether to print debug logs to stderr |

Validation rules:

- `backend` must currently be `say`
- `rate` must be greater than `0`
- `voice` must not be empty after trimming whitespace
- `speak_phase` must currently be `final_only`
- `verbose` must be a boolean

Precedence:

1. CLI arguments
2. Config file values
3. Built-in defaults

## How It Works

The runtime flow is:

1. Start the real `codex`
2. Record the working directory and launch time
3. Find the new thread in `~/.codex/state_5.sqlite`
4. Follow that thread's rollout JSONL file
5. Speak each new assistant `final_answer`

It does not parse terminal ANSI output. It reads Codex's structured local session data directly.

## Background Runtime

`codex-tts` now supports a daemon mode:

- `codex-tts launch -- ...` starts a new Codex session
- the daemon owns launch registration, thread binding, rollout polling, and speech arbitration
- only one focused session may speak at a time
- the first active session auto-focuses
- new sessions do not steal focus
- when the focused session exits, focus is cleared instead of being reassigned automatically

Common control commands:

```bash
codex-tts launch -- --no-alt-screen
codex-tts status --json
codex-tts focus <session-id>
codex-tts mute <session-id>
codex-tts unmute <session-id>
codex-tts enable
codex-tts disable
codex-tts daemon run
```

Legacy compatibility remains: `codex-tts -- --no-alt-screen` still behaves like `codex-tts launch -- --no-alt-screen`.

## Menubar Shell

The repository now includes a native macOS menubar shell under:

```text
macos/CodexTTSMenuBar
```

It is currently shipped as a Swift Package:

```bash
swift build --package-path macos/CodexTTSMenuBar
```

If you want a local double-clickable `.app` bundle, run:

```bash
bash scripts/package-menubar-app.sh
```

The packaged outputs are written to:

```text
dist/CodexTTS.app
dist/CodexTTS.app.zip
```

The shell can:

- show daemon reachability
- show the current focus session
- list managed sessions
- focus / mute / unmute sessions
- toggle global speech

Usage notes:

- This is a menu bar app, not a regular windowed app
- After launching it, look for the icon on the right side of the macOS menu bar
- Before first use, run `bash scripts/install.sh` so the `codex-tts` launcher is available in a standard location
- If the daemon is not running yet, the app now tries to start it automatically in the background
- The first connection can take a few seconds; if auto-start fails, use `Start Daemon` from the menu

## Spoken Text Sanitization

Before text reaches TTS, `codex-tts` applies a small cleanup layer:

- Bare URLs are removed
- Markdown links are converted from `[label](url)` to just `label`
- Extra whitespace and empty lines are collapsed
- If nothing readable remains after cleanup, nothing is spoken

This only changes the spoken text. It does not change what you see in the terminal.

## Current Limits

- macOS `say` only
- Final replies only, no spoken errors or intermediate status
- Concurrent Codex sessions in the same directory are not guaranteed to match perfectly
- Polling-based implementation, not filesystem events
- The menubar shell is currently a buildable native wrapper, not a fully packaged signed macOS app

## Troubleshooting

### No sound

Test the macOS speech subsystem directly:

```bash
say "test successful"
```

If that does not produce sound, check:

- System volume
- Active audio output device
- Whether macOS speech works outside this project

### Command not found

If you are running from source, use:

```bash
PYTHONPATH=src python -m codex_tts.cli --help
```

If you installed the global launcher, confirm:

- You ran `bash scripts/install.sh`
- `~/.local/bin` is in `PATH`
- You reloaded your shell config, for example `source ~/.zshrc`

### Double-clicked the app but no window appeared

That is expected. The current client is a `menubar app`, so it does not open a main window.

Check these first:

- Look at the right side of the macOS menu bar, not the Dock
- Make sure you already ran `bash scripts/install.sh`
- If the icon briefly shows a disconnected state, wait a few seconds for auto-start
- If it stays disconnected, click `Start Daemon` from the menu

### Codex replied, but nothing was spoken

Check these first:

- You started Codex through `codex-tts`, not plain `codex`
- The reply reached the final stage and is not still in `commentary`
- You are not running multiple unrelated Codex sessions in the same directory

If that still does not explain it, rerun with `--verbose`:

```bash
codex-tts --verbose -- --no-alt-screen
```

That prints thread candidate decisions, rollout attachment, and skip reasons such as sanitized text becoming empty.

### List available voices

```bash
codex-tts --list-voices
```

## Development and Testing

Run the full test suite:

```bash
bash scripts/bootstrap.sh
source .venv/bin/activate
python -m pytest -q
```

Build the menubar shell:

```bash
swift build --package-path macos/CodexTTSMenuBar
```

Package a local `.app` bundle:

```bash
bash scripts/package-menubar-app.sh
```

Show CLI help:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --help
```

Test the installer scripts only:

```bash
source .venv/bin/activate
python -m pytest tests/test_install_script.py -q
```

CI notes:

- GitHub Actions runs `python -m pytest -q` on every push and pull request
- Run the full suite locally before you hand off changes

## Future Work

- Add OpenAI / ElevenLabs / Edge TTS backends
- Add spoken error notifications
- Improve multi-session matching
- Ship a packaged signed macOS app with launch-at-login integration
- Add a notification-style history panel and replay actions
