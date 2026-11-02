# IGRIS Single-Task Architecture — execution report

Date: 2026-11-02. Branch: **develop**. Baseline: `2592bf2b69902c43f5d1934435eaf7787915b53c`, initially clean. Verified implementation commit: **`796f3f681db19ea64da5b707cc93a218b4ef3c50`**. This report/evidence follows in a separate documentation commit; its remote tip is reported at delivery. Existing commits, pinned upstream trees and user work are preserved.

**PASS: available cloud implementation and acceptance checks. BLOCKED: actual Mac M1 installation/resource/voice validation. This is not a production-readiness certification.** No Mac installation, deployment, main merge, force push, new paid service or n8n execution occurred.

## 1. Existing architecture findings — PASS

Reviewed README, architecture, the original fifty report statuses/scopes, three inference/Guardian activation milestones, fourteen completion reports, tests and actual controller, chat, Guardian, specialists, dashboard and Ops Pilot implementation. The written plan was recorded before edits in [single-task-plan.md](../architecture/single-task-plan.md).

Reused real Hermes inference with native tools disabled, SQLite conversations, exact-action Guardian approvals, owned-launch acknowledgement/cleanup, the model's cross-process resource lock, the single dashboard execution thread, reviewed specialist definitions, and the disposable-target read-only Ops proxy/export validator. The old explicit one-shot Ops CLI remains intact and passed its real compatibility replay. Upstream Ops Pilot/Triage source is unmodified.

Missing at baseline: a mission-wide reservation spanning entry points and approval waits; durable retry identity/outcome metadata; and explicit retained/on-demand Ops lifecycle. The baseline suite ran 280 tests with one intermittent dashboard approval failure. A numeric twelve-character digest confirmation could be mistaken for a telephone number by free-text privacy filtering. Typed exact-digest owner validation fixes this without relaxing prompt/document filtering or Guardian's approval checks.

## 2. Changes implemented — PASS

- Default one-foreground-task coordinator: standard-library private SQLite journal plus process file lock, shared by chat and registered Guardian activities across this checkout. States include starting/running/waiting_for_approval/stopping and terminal completed/failed/cancelled, with idle availability. No additional model or orchestration framework.
- Reservations persist through preparation, inference, owner review, execution, verification and cleanup. Additional dashboard work queues without another worker; another direct entry point is denied while reserved. Durable request IDs/fingerprints prevent replay or changed-body retries after restart. Restart never resumes old authority; uncertain cleanup blocks subsequent work.
- Structured journal results include task ID/type, timestamps, actions, verified outcomes, limitations, outcome classification and cleanup disposition. Explicit failed/unverified executor results cannot become successful tasks. Decision/control requests do not create another foreground execution.
- Per-task cancellation permits later intentional tasks after verified cleanup. Emergency stop cancels pending authority and tracked work and prevents automatic restart. Approval and stop HTTP paths remain responsive. Idle execution uses a wakeup event, and hidden dashboard tabs stop status-network refresh.
- Small trusted lazy integration catalog: static factories, finite capabilities, permission/resource metadata, health and lifecycle methods. Only selected adapters load. A zero-process clock executes through Guardian. Naukri, LinkedIn, GitHub, Gmail and browser entries remain unavailable placeholders; no account access was added.
- Ops lifecycle uses the existing actual pinned library and restrictions: Manual default, explicit Monitoring retention, and On-demand start/probe/validate/stop. Owner approves exact action/target/mode/current component and runtime scope. No silent Manual start, automatic remediation or background polling. Sessions are bounded to sixteen probes/one hour.
- Existing specialists retain the shared Hermes backend and exact owner-authorized activation; they receive no extra tool authority. Ordinary chat starts no Ops/browser/job-search service. n8n is excluded from new startup and UI; preserved quarantine is unchanged.

## 3. Files changed — PASS

The implementation commit contains 29 files (1,175 insertions, 114 deletions):

- Scheduler/chat/security: `src/igris/foreground.py`, `chat.py`, `guardian/activities.py`, `guardian/approvals.py`, `guardian/policy.py`.
- Integration lifecycle: `src/igris/integrations/catalog.py`, `ops_lifecycle.py`, `ops_lifecycle_cli.py`, `session_process.py`, `ops_runtime.py`; `integrations/ops/worker.py`, `session_worker.py`, `profile.json`.
- Dashboard: `src/igris/mission_control.py`, `src/igris/web/control.html`, `control.js`.
- Tests: `tests/test_foreground.py`, `test_integration_catalog.py`, `test_single_task_control.py`, `test_ops_lifecycle_contract.py`, `test_mission_control.py`, `test_owner_actions.py`.
- Reproducible checks: `scripts/measure_single_task.py`, `test_ops_lifecycle_cli_live.py`, `test_single_task_dashboard_live.py`, `test_single_task_ops_dashboard.py`, `test_single_task_ops_failures.py`, `test_single_task_ops_live.py`, and the initial architecture plan.

Delivery also updates README and architecture links, adds [single-task.md](../architecture/single-task.md), [ops-lifecycle.md](../integrations/ops-lifecycle.md), this report, and the `docs/validation/single-task-*.json` evidence/tracker. No runtime credentials, virtual environments, model assets or unrelated files are committed.

## 4. Tests and actual results — PASS after fixes

Final full regression: **295 tests passed in 31.155 seconds**, zero failures. This suite contains synthetic unit fixtures as well as real filesystem/SQLite/process-lock checks; it is not described as 295 live integrations. Security source/index scanning found no configured credential patterns. CI structure/pinning and delivery/provenance checks passed, including 2,674 Hermes hashes and fifteen original/adapted specialist pairs. JavaScript syntax and staged diff whitespace checks passed.

| Check | Result | Evidence |
| --- | --- | --- |
| Cross-entry foreground exclusion, approval hold, retries, changed identity, crash/recovery, outcome schema | PASS | `tests/test_foreground.py`, actual file locking/SQLite/subprocess; no inference claimed |
| Queued requests, cancellation, responsive stop, lazy idle startup, numeric digest validation | PASS | `tests/test_single_task_control.py`; explicitly synthetic cooperative inference |
| Guardian exact permissions/approvals, path controls and existing behavior | PASS | Full regression and real approvals below |
| Actual Hermes response and competing entry rejection; only one model process/container | PASS | [single-task-memory.json](../validation/single-task-memory.json); real answer `12` |
| Actual Hermes tool proposal, browser owner approval, time execution, cancellation followed by another task, emergency stop | PASS | [single-task-dashboard-live.json](../validation/single-task-dashboard-live.json); real sandboxed Chromium at 390px |
| Actual Ops Manual/On-demand/Monitoring behavior | PASS | [single-task-ops-live.json](../validation/single-task-ops-live.json) |
| Actual Ops timeout, owned-worker failure and cancellation cleanup | PASS | [single-task-ops-failures.json](../validation/single-task-ops-failures.json) |
| Actual controlling-terminal and browser Ops approvals/lifecycle | PASS | [single-task-ops-cli-live.json](../validation/single-task-ops-cli-live.json), [single-task-ops-dashboard.json](../validation/single-task-ops-dashboard.json) |
| Preserved one-shot Ops running/stopped fixture compatibility | PASS | [single-task-legacy-ops-live.json](../validation/single-task-legacy-ops-live.json) |
| Fifteen new live specialist benchmarks in this change | NOT TESTED | Prior specialist evidence is preserved; this change does not claim a fresh fifteen-role live campaign |
| Mac ARM64, physical microphone/playback, production integration | BLOCKED / NOT TESTED | No authorized target hardware or production runtime used |

The final actual UI run measured 1.188 seconds from cancellation request to terminal job state, and 0.709 seconds for emergency stop/verified worker disappearance. These are Linux test observations, not hard realtime guarantees.

Live approvals use explicitly automated trusted terminal/browser owner fixtures, not AI authorization. Live scripts use actual Hermes/Docker/Guardian/filesystem boundaries; deterministic race tests separately label synthetic backends.

Recorded failures and fixes:

1. Baseline HTTP 400 approval failure: fixed typed numeric digest handling; forged/mismatched/type-invalid confirmations still fail and free-text privacy filtering still rejects sensitive-looking input.
2. An intermediate regression run overlapped a real terminal acceptance process: two tests correctly received ForegroundBusy. Reran the final suite without competing acceptance activity; all 295 passed. The global exclusion was preserved.
3. First Ops GUI attempt submitted into the prior action's stale DOM card. Exact-action checks rejected it. The automation now waits for the current full digest; real GUI acceptance passes. No security relaxation.
4. Staged diff review caught an extra EOF blank line in the new console file. Normalized whitespace and replayed the actual PTY check successfully. The original Ops CLI was verified unchanged.

Reproduction commands (run real acceptance serially, not alongside regression or another foreground task):

```sh
$ python3 -m unittest discover -s tests -q
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ node --check src/igris/web/control.js
$ python3 scripts/test_single_task_ops_live.py
$ python3 scripts/test_single_task_ops_failures.py
$ python3 scripts/test_ops_lifecycle_cli_live.py
$ python3 scripts/test_ops_runtime_live.py
$ unshare --user --map-current-user --keep-caps --net python3 scripts/test_single_task_dashboard_live.py
$ unshare --user --map-current-user --keep-caps --net python3 scripts/test_single_task_ops_dashboard.py
$ python3 scripts/measure_single_task.py
$ git diff --cached --check
```

The browser checks use a network-isolated user namespace with loopback and the preinstalled Chromium sandbox. No browser or n8n installation is performed. Live checks require the existing reviewed cloud runtime/assets; they are not generic Mac commands.

## 5. Real memory measurements — PASS on Linux only

Environment: managed Linux x86_64, Python 3.12.14, Docker VFS. Method: current `/proc/PID/status` VmRSS, exact owned-container PIDs, sampled model loading/inference. Controller includes the standard-library measurement harness. Docker daemon and disposable monitored application are excluded. RSS includes shared/file-backed pages and is not PSS or unique physical RAM. Sampled peaks are not guaranteed absolute peaks.

| Measurement | Observed MiB |
| --- | ---: |
| Idle controller/harness, no optional adapters loaded | 19.051 |
| Loaded model process, sampled peak | 2,681.051 |
| All owned Hermes processes, sampled aggregate peak | 2,862.137 |
| Controller after Hermes | 22.324 |
| Controller before Ops | 20.598 |
| Ops active worker, additional RSS | 25.742 |
| Controller while Ops active | 20.715 |
| Controller after Ops stop | 21.211 |
| Owned Ops process RSS after verified removal | 0 |
| Controller with lightweight clock / after final cleanup | 21.215 |

Only one model process/container was observed; a competing ChatService call was denied before model launch. The final controller delta was +2.164 MiB from initial idle; the post-Ops delta was +0.613 MiB from its immediate pre-Ops baseline. Owned process RSS disappears after verified container removal; Python retains some imports/allocator pages. This is evidence of cleanup, not a long-running leak certification or a guaranteed exact return to baseline. See raw bytes and source hashes in the memory evidence.

## 6. Ops Pilot lifecycle verification — PASS

Manual status is initially stopped, probes without explicit approved start are denied, rejected start launches nothing, and separately approved probes reuse the same acknowledged component. Monitoring requires its configured mode and explicit owner-approved start; it permits retained foreground probes without an automatic poller. On-demand starts only inside an approved probe and stops after success, real timeout, induced owned-worker failure or cancellation. Structured results distinguish retained_authorized from verified stopped cleanup. Real failure tests ended with zero owned sessions; the monitored application remained untouched until explicitly owned fixture teardown.

The new session worker uses non-root read-only Docker, network none, no capabilities, no-new-privileges, 256 MiB/one CPU/64 PIDs, bounded tmpfs and authenticated sequenced pipe frames. It sees only the existing exact-target read proxy and disposable application socket. Scope binds reviewed sources/runtime, daemon, fixture, target, mode, timeout and current component. Models get no raw Docker socket, approval database or read credential. Stopping targets, arbitrary commands and repairs are not exposed.

## 7. Guardian security verification — PASS within stated boundary

Guardian remains the sole authorizer. The foreground lock/catalog do not grant permissions. Sensitive actions stay gated by exact immutable review, owner identity, scope revalidation, expiry and one-use consumption. Native Hermes tools stay disabled. Tests cover default-deny, malformed/unregistered arguments, unauthorized targets/modes, approval forgery/replay, path traversal and prompt-injection execution boundaries. HTTP owner/viewer authorization, Origin/Host/CSRF controls and safe rendering remain intact.

Cleanup only addresses acknowledged IGRIS-owned components; uncertain cleanup retains ownership evidence and blocks work. Crash recovery requires explicit independently verified owner cleanup, never automatic replay. Pending conversation reservations may also need owner recovery after a hard crash. Same-user host/Python/database tampering, database rollback, kernel compromise and distributed/network-filesystem lock behavior are not certified isolation. Late cancellation cannot undo already-committed side effects.

## 8. Features still incomplete — BLOCKED / NOT TESTED

- Actual target Mac/ARM64 isolation, memory fit, model startup and physical multilingual voice remain BLOCKED by unavailable authorized hardware. Existing honest voice/hardware status is preserved.
- Real Naukri, LinkedIn, Gmail and other future account integrations are NOT IMPLEMENTED; disabled metadata placeholders confer no access.
- Production DevOps, remediation, purchases, messaging/job submissions, deployment and automatic background monitoring are NOT ENABLED. Read-only disposable targets remain the only Ops acceptance scope.
- n8n remains quarantined; this architecture introduces no n8n dependency or live runtime. Broader previous release blockers are not cleared by this task.
- Automatic crash recovery, distributed scheduling and hostile-host sandbox guarantees are NOT IMPLEMENTED. Owner-reviewed recovery is intentional.

## 9. Mac-specific validation and startup — BLOCKED hardware; cloud startup available

No Mac changes occurred. Later authorized M1 testing must verify ARM64 assets/kernel restrictions, the native voice/VM boundary, actual 8 GB RAM/storage behavior, microphone/playback, startup/shutdown and cleanup. These Linux measurements must not be used as Mac results. Existing Mac guidance remains provisional until that hardware acceptance.

Use the already prepared cloud runtime for manual text chat:

```sh
$ PYTHONPATH=src python3 -m igris.chat --remember
```

Use the existing private Mission Control account file; no default credentials are added:

```sh
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json
```

Only add `--enable-specialists` or `--ops-demo --ops-mode manual` deliberately. The Ops demo flag explicitly creates the disposable application fixture, not a production target. Optional integrations remain stopped until their approved actions. See [Ops lifecycle guidance](../integrations/ops-lifecycle.md) for the other modes and terminal interface. Ctrl+C shuts down owned resources; dashboard Cancel stops one task, and Emergency stop disables further work until explicit restart. No autostart service is added.

## 10. Git delivery — PASS for implementation

Implementation commit `796f3f681db19ea64da5b707cc93a218b4ef3c50` was published normally to origin/develop using the connected GitHub App's expected-head, non-force fast-forward update (CLI HTTPS credentials are unavailable). The exact API-created tree/commit was imported locally and the remote SHA verified. Documentation/evidence follows separately; the final response gives that verified tip and working-tree state. No main ref was changed. Repository development/publication was already authorized; no additional credentials or permission were requested.

Next action: owner review of the cloud implementation; later explicitly authorized target-Mac acceptance. No user help is needed for the completed cloud work.
