IGRIS EXECUTION REPORT

Task: 2 / 14
Title: Handy voice input
Status: BLOCKED

Recorded: 2026-11-01T18:55:43.470492+05:30

Implemented:

- Pinned Handy v0.9.8 public headless file interface and exact multilingual Whisper Small checksum.
- Disabled-by-default file adapter, bounded private WAV snapshot, offline non-root worker and explicit CLI connection to existing Hermes chat and SQLite.
- Manual microphone capture interface with explicit consent, stop/cancel, duration limit and text fallback; no device activated.

Real versus simulated:

- REAL: Handy transcribed synthetic English WAV; unchanged text reached real Hermes, answered 12 and persisted.
- FIXTURE: microphone callback tests; not physical microphone proof.
- UNTESTED: real human microphone, Mac input/permissions and physical playback.

Tests and results:

- 209 regression tests PASS in 28.246 seconds; five new audio/capture tests.
- Secret scanner, CI structure/import check and compileall PASS.
- Real ASR/Hermes/persistence mechanics PASS; evidence docs/validation/handy-live.json.
- Initial failed attempts: source asset HTTP403 (identical checksum mirror used); minimal Python lacked json (full stdlib added); upstream Deb omitted ALSA (explicit container library added); numeric-word assertion corrected after actual transcript inspection.
- Actual isolated worker success, timeout, execution error, output limit and cancellation all PASS after fixing asynchronous Docker --rm cleanup race. No lingering owned containers.
- Handy live pipeline evidence predates only the cleanup hardening; the final transport was separately tested with real fixed offline workers. Human and Mac testing remain unavailable.
- Final post-cleanup-hardening regression: 209 tests PASS in 26.719s; existing Guardian tool test emitted unclosed-writer ResourceWarning, no test failure.

Security review:

- Network disabled, root filesystem read-only, nonroot UID, no caps, no-new-privileges, fixed RO mounts only, bounded CPU/RAM/PID/time/output; existing Guardian profile unchanged.
- No keyboard monitoring, accessibility, clipboard, microphone device mounts, approval databases, credentials or Docker socket inside worker.
- Cancellation/timeout cleanup is tested with actual owned workers; no generic command capability is registered.
- Same-user parent mutation and host administrator remain outside isolation boundary.

Performance:

- Synthetic clip 1.855 seconds; ASR wall 32.761s, model load 6754ms, recognition 14162ms.
- Real Hermes chat wall 61.927s on cloud Linux; not Mac measurements.

Known limitations:

- Task acceptance BLOCKED for unavailable physical microphone and authorized Mac; live file pipeline verified only.
- Handy JSON has no detected language; language=null is preserved.
- Optional native sounddevice dependency is not installed, pinned or device-verified yet; text/WAV fallback only in this environment.
- Linux GTK/WebKit container overhead remains; optional assets ignored, no Mac installation.
- VFS storage driver copies the full 836 MB Handy image per run. Builds exhausted disk; only task-owned failed image/cache records were cleaned. Current free disk is insufficient for another Handy run; optional runtime must be archived/reclaimed before subsequent components.

External requirements:

- Authorized target Mac and physical microphone, OS permission and human speech testing.

Files changed:

- README.md
- docs/integrations/handy.md
- docs/validation/handy-live.json
- docs/validation/isolated-worker-live.json
- integrations/handy/Dockerfile
- integrations/handy/profile.json
- integrations/handy/worker.py
- scripts/fetch_handy_assets.py
- scripts/test_handy_live.py
- scripts/test_isolated_worker_live.py
- src/igris/isolated.py
- src/igris/voice/__main__.py
- src/igris/voice/capture.py
- src/igris/voice/handy.py
- tests/test_handy.py

Commands executed:

$ python3 scripts/fetch_handy_assets.py
$ python3 -m unittest discover -s tests -q
$ PYTHONPATH=src python3 scripts/test_handy_live.py
$ PYTHONPATH=src python3 scripts/test_isolated_worker_live.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ python3 scripts/check_ci.py
$ git diff --check

Git delivery: Connected GitHub App, exact staged tree and normal expected-head fast-forward; remote SHA verified. Git CLI authentication was unavailable.

Git commit:

- Verified implementation: 2977b932be2337e2b59923981996c6803a8063ae
- This report is recorded in a following documentation commit; remote tip is checked after publication.

Next task:

- 3

Approval required:

- No for authorized development/push. Mac access, production, main merge, paid services and new host privileges remain unauthorized.
