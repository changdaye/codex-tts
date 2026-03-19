# Codex TTS Next Optimizations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `codex-tts` more robust for daily use by improving session matching, rollout watching efficiency, runtime diagnostics, and install/release reliability without changing the final-only user experience.

**Architecture:** Keep the user-facing CLI simple, but strengthen the internals around four pressure points: thread resolution, rollout tailing, observability, and packaging. Correctness comes first: the system should prefer “skip speech safely” over speaking the wrong session, and it should explain why it skipped when debug mode is enabled.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `dataclasses`, `json`, `pathlib`, `sqlite3`, `subprocess`, `time`, `tomllib`), `pytest`, GitHub Actions

---

## Why These Optimizations Matter

The current implementation works, but it still has a few structural weaknesses:

- Session matching is conservative, but still fragile when multiple Codex sessions share a directory or when a session is resumed instead of freshly created.
- Rollout polling rereads the whole file on each poll, which is simple but scales poorly and makes debugging harder.
- The runtime is mostly silent when it decides not to speak, so failures look like “nothing happened.”
- Packaging and install now work locally, but release hygiene is still thin: no CI gate, no bootstrap helper, and minimal validation around install prerequisites.

This plan intentionally does **not** expand the product surface first. It hardens the foundation so later features like additional TTS backends or optional error speech do not sit on top of brittle internals.

## Optimization Priorities

### Priority 1: Session Matching Robustness

Improve how the wrapper picks the correct Codex thread so that false matches become less likely and “no match” decisions become explainable.

### Priority 2: Rollout Watcher Efficiency

Stop reparsing the entire rollout file on every poll. Use a cursor-style reader so long-running sessions remain cheap and deterministic.

### Priority 3: Diagnostics And Debugging

Add a narrow debug mode so users can see why no speech happened, which thread was selected, and what text was sanitized before playback.

### Priority 4: Install And Release Reliability

Tighten bootstrap, installer checks, and CI so the repo is easier to set up and safer to change.

## File Structure

- Create: `docs/superpowers/plans/2026-03-19-codex-tts-next-optimizations.md`
  This implementation plan
- Create: `src/codex_tts/diagnostics.py`
  Small stderr logger and debug helpers for runtime decisions
- Create: `tests/test_diagnostics.py`
  Unit tests for debug logging helpers
- Create: `.github/workflows/ci.yml`
  Minimal test workflow for pushes and pull requests
- Create: `scripts/bootstrap.sh`
  Local bootstrap helper for `.venv`, test dependencies, and install guidance
- Modify: `src/codex_tts/cli.py`
  Add debug flag plumbing and validated runtime options
- Modify: `src/codex_tts/config.py`
  Validate and normalize config values; optionally expose debug defaults
- Modify: `src/codex_tts/models.py`
  Add richer dataclasses for thread candidates and watcher state
- Modify: `src/codex_tts/session_store.py`
  Add candidate scoring and better thread selection heuristics
- Modify: `src/codex_tts/rollout.py`
  Replace full-file rereads with byte-offset or open-handle cursor tracking
- Modify: `src/codex_tts/service.py`
  Introduce explicit runtime states, debug logging, and clearer skip paths
- Modify: `scripts/install.sh`
  Validate prerequisites and improve PATH guidance
- Modify: `scripts/uninstall.sh`
  Keep uninstall output aligned with installer behavior
- Modify: `README.md`
  Document debug mode, bootstrap flow, and refined troubleshooting
- Modify: `README.en.md`
  English doc parity for operational changes
- Modify: `README.ja.md`
  Japanese doc parity for operational changes
- Modify: `README.ko.md`
  Korean doc parity for operational changes
- Modify: `tests/test_service.py`
  Cover debug logging, empty-match decisions, and sanitized skip paths
- Modify: `tests/test_session_store.py`
  Cover improved thread scoring and resume scenarios
- Modify: `tests/test_rollout.py`
  Cover incremental cursor behavior and file truncation/reset cases
- Modify: `tests/test_install_script.py`
  Cover bootstrap/install checks and friendlier installer behavior
- Modify: `tests/test_config.py`
  Cover validation and normalized config behavior

## Implementation Notes

- Preserve the current user promise: only final replies are spoken.
- Treat thread selection as a scored decision, not just first match wins.
- Prefer explicit debug logs over implicit magic. Normal mode should stay quiet.
- Keep debug mode local and simple: stderr logging plus deterministic tests.
- Do not introduce external Python dependencies if the standard library is enough.
- Use TDD for each optimization slice. Every change should begin with a failing test.

### Task 1: Harden Session Candidate Selection

**Files:**
- Modify: `src/codex_tts/models.py`
- Modify: `src/codex_tts/session_store.py`
- Modify: `src/codex_tts/service.py`
- Modify: `tests/test_session_store.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write the failing candidate-selection tests**

```python
def test_resolve_active_thread_prefers_newest_candidate_with_rollout_path(tmp_path):
    ...


def test_resolve_active_thread_skips_threads_without_existing_rollout(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_session_store.py -q`
Expected: FAIL because the current resolver returns the first acceptable row and does not score candidates or validate rollout files.

- [ ] **Step 3: Add explicit thread candidate modeling**

```python
@dataclass(frozen=True)
class ThreadCandidate:
    thread_id: str
    rollout_path: Path
    created_at: int
    updated_at: int
    score: tuple[int, int]
```

- [ ] **Step 4: Implement scored selection heuristics**

Use a score that prefers:

1. rollout file exists
2. rollout file has non-zero size or recent modification time
3. newer `updated_at`
4. newer `created_at`

Keep the fallback safe: if no candidate passes minimum criteria, return `None`.

- [ ] **Step 5: Add service-level tests for “no reliable match”**

```python
def test_run_session_skips_speech_when_thread_candidates_are_ambiguous(...):
    ...
```

- [ ] **Step 6: Run the focused tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_session_store.py tests/test_service.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/codex_tts/models.py src/codex_tts/session_store.py src/codex_tts/service.py tests/test_session_store.py tests/test_service.py
git commit -m "fix: harden codex session selection"
```

### Task 2: Replace Whole-File Polling With Incremental Rollout Cursors

**Files:**
- Modify: `src/codex_tts/rollout.py`
- Modify: `tests/test_rollout.py`
- Modify: `tests/fixtures/fake_codex.py`

- [ ] **Step 1: Write the failing cursor tests**

```python
def test_final_answer_watcher_only_returns_new_lines(tmp_path):
    ...


def test_final_answer_watcher_recovers_from_rollout_truncation(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_rollout.py -q`
Expected: FAIL because the current watcher rereads the whole file each poll and only tracks line count.

- [ ] **Step 3: Introduce a byte-offset rollout cursor**

```python
class RolloutCursor:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0

    def read_new_lines(self) -> list[str]:
        ...
```

- [ ] **Step 4: Update `FinalAnswerWatcher` to use the cursor**

Keep behavior the same from the caller’s perspective:

- return only new final events
- handle missing files
- reset cleanly if the file shrinks or is replaced

- [ ] **Step 5: Extend fake rollout fixtures if needed**

Allow test helpers to simulate multiple appends and file resets without duplicating logic in test bodies.

- [ ] **Step 6: Run the focused rollout tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_rollout.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/codex_tts/rollout.py tests/test_rollout.py tests/fixtures/fake_codex.py
git commit -m "refactor: use incremental rollout cursors"
```

### Task 3: Add Debug Mode And Runtime Diagnostics

**Files:**
- Create: `src/codex_tts/diagnostics.py`
- Create: `tests/test_diagnostics.py`
- Modify: `src/codex_tts/cli.py`
- Modify: `src/codex_tts/config.py`
- Modify: `src/codex_tts/service.py`
- Modify: `tests/test_service.py`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `README.ja.md`
- Modify: `README.ko.md`

- [ ] **Step 1: Write the failing diagnostics tests**

```python
def test_debug_logger_writes_prefixed_messages(capsys):
    ...


def test_run_session_logs_why_speech_was_skipped(monkeypatch, tmp_path, capsys):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_diagnostics.py tests/test_service.py -q`
Expected: FAIL because there is no debug logger and the runtime does not explain skipped speech.

- [ ] **Step 3: Add a minimal diagnostics module**

```python
@dataclass(frozen=True)
class DebugLogger:
    enabled: bool = False

    def log(self, message: str) -> None:
        if self.enabled:
            print(f"codex-tts: {message}", file=sys.stderr)
```

- [ ] **Step 4: Expose a CLI debug flag**

Add a narrow flag such as:

```text
--verbose
```

Use it to log:

- thread candidate decisions
- rollout watcher attachment
- sanitized text becoming empty
- speech backend failures

- [ ] **Step 5: Document debug usage**

Update all four README files with a short “when nothing is spoken, rerun with `--verbose`” section.

- [ ] **Step 6: Run focused diagnostics tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_diagnostics.py tests/test_service.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/codex_tts/diagnostics.py src/codex_tts/cli.py src/codex_tts/config.py src/codex_tts/service.py tests/test_diagnostics.py tests/test_service.py README.md README.en.md README.ja.md README.ko.md
git commit -m "feat: add codex tts debug diagnostics"
```

### Task 4: Tighten Config Validation And Operational Defaults

**Files:**
- Modify: `src/codex_tts/config.py`
- Modify: `src/codex_tts/cli.py`
- Modify: `tests/test_config.py`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `README.ja.md`
- Modify: `README.ko.md`

- [ ] **Step 1: Write failing validation tests**

```python
def test_load_config_rejects_unknown_backend(tmp_path):
    ...


def test_load_config_rejects_non_positive_rate(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_config.py -q`
Expected: FAIL because the current loader trusts raw config values and does not validate them.

- [ ] **Step 3: Add normalized config parsing**

Implement validation for:

- backend name
- positive speech rate
- non-empty voice
- supported `speak_phase`

Surface config errors as clear `ValueError` messages that the CLI can print before exiting.

- [ ] **Step 4: Add CLI handling for invalid config**

Make the failure user-friendly:

```text
codex-tts: invalid config: rate must be greater than 0
```

- [ ] **Step 5: Update docs with validated config rules**

Document accepted values and likely failure cases.

- [ ] **Step 6: Run config tests**

Run: `source .venv/bin/activate && python -m pytest tests/test_config.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/codex_tts/config.py src/codex_tts/cli.py tests/test_config.py README.md README.en.md README.ja.md README.ko.md
git commit -m "fix: validate codex tts configuration"
```

### Task 5: Improve Bootstrap, Installer Checks, And CI

**Files:**
- Create: `scripts/bootstrap.sh`
- Create: `.github/workflows/ci.yml`
- Modify: `scripts/install.sh`
- Modify: `scripts/uninstall.sh`
- Modify: `tests/test_install_script.py`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `README.ja.md`
- Modify: `README.ko.md`

- [ ] **Step 1: Write failing installer and bootstrap tests**

```python
def test_install_script_reports_missing_virtualenv_python(tmp_path):
    ...


def test_bootstrap_script_creates_virtualenv_when_missing(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_install_script.py -q`
Expected: FAIL because there is no bootstrap script and installer checks are minimal.

- [ ] **Step 3: Add `scripts/bootstrap.sh`**

The bootstrap script should:

- create `.venv` if missing
- print the exact activation command
- optionally install dev dependencies when available

Keep it safe: if dependency installation fails, explain the next manual step instead of hiding the error.

- [ ] **Step 4: Strengthen `scripts/install.sh`**

Add checks for:

- repository root detection
- required `.venv/bin/python`
- optional warning when `codex` is not in `PATH`
- clearer PATH instructions

- [ ] **Step 5: Add a minimal CI workflow**

Create `.github/workflows/ci.yml` that runs:

```bash
python -m pytest -q
```

on pushes and pull requests.

- [ ] **Step 6: Update install docs**

Document:

- bootstrap path
- installer behavior
- uninstall behavior
- CI expectations for contributors

- [ ] **Step 7: Run the relevant verification**

Run:

```bash
source .venv/bin/activate && python -m pytest tests/test_install_script.py -q
source .venv/bin/activate && python -m pytest -q
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add scripts/bootstrap.sh scripts/install.sh scripts/uninstall.sh .github/workflows/ci.yml tests/test_install_script.py README.md README.en.md README.ja.md README.ko.md
git commit -m "chore: improve bootstrap and ci setup"
```

### Task 6: Final Verification And Release Hygiene

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `README.ja.md`
- Modify: `README.ko.md`

- [ ] **Step 1: Re-read the plan and check scope**

Confirm the implementation still matches the intended boundaries:

- no commentary speech
- no cloud backend dependency
- no daemon mode

- [ ] **Step 2: Run the full verification suite**

Run:

```bash
source .venv/bin/activate
python -m pytest -q
```

Expected: PASS with all tests green.

- [ ] **Step 3: Run smoke commands manually**

Run:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --help
PYTHONPATH=src python -m codex_tts.cli --list-voices | head -n 5
```

Expected:

- CLI help prints successfully
- voice listing prints a few available voices

- [ ] **Step 4: Commit final docs or cleanup if needed**

```bash
git add README.md README.en.md README.ja.md README.ko.md
git commit -m "docs: finalize optimization rollout notes"
```

- [ ] **Step 5: Prepare merge handoff**

```bash
git status --short --branch
git log --oneline --max-count=10
```

Expected: clean working tree and a small, readable commit stack.

## Recommended Execution Order

1. Task 1: session matching
2. Task 2: rollout cursor
3. Task 3: diagnostics
4. Task 4: config validation
5. Task 5: bootstrap and CI
6. Task 6: final verification

## Out Of Scope For This Plan

- New cloud TTS providers
- Speaking errors or commentary by default
- Windows/Linux voice backends
- Daemon mode
- GUI or desktop app packaging
