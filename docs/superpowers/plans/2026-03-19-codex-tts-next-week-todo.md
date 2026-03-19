# Codex TTS Next Week Todo

## Current State

- Branch: `main`
- Verified commits already on `main`: `a67683f`, `e1d848e`
- Latest full test run:
  - `131 passed, 1 warning in 10.65s`
  - Python coverage: `100%`
- Latest live verification:
  - `codex-tts exec --skip-git-repo-check "Reply with exactly TEST-OK and nothing else."`
  - session bound successfully
  - final text recorded as `TEST-OK`
  - daemon stayed alive after client disconnect

## Next Week Priority Todo

- [ ] Re-verify real interactive `codex-tts` sessions in Terminal, not just `exec`, and confirm final answers are actually spoken aloud
- [ ] If interactive sessions still register but do not speak, trace the runtime path end-to-end: thread bind, rollout updates, speech policy, sanitized speech text, and `say` invocation
- [ ] Add a durable daemon startup path for macOS (`launchd` / `LaunchAgent`) so the app does not depend on shell-managed background processes
- [ ] Improve menubar diagnostics so the disconnected / pending-bind / active states are clearer without reading logs
- [ ] Decide whether to keep wrapper-only registration or add passive discovery for plain `codex` sessions
- [ ] Add one lightweight troubleshooting command, likely `codex-tts doctor` or `codex-tts logs`
- [ ] Rebuild and smoke-test the packaged menubar app after the next daemon changes

## Useful Commands

```bash
.venv/bin/python -m coverage run -m pytest -q && .venv/bin/python -m coverage report -m
~/.local/bin/codex-tts daemon run
~/.local/bin/codex-tts status --json
~/.local/bin/codex-tts exec --skip-git-repo-check "Reply with exactly TEST-OK and nothing else."
bash scripts/package-menubar-app.sh
```
