IGRIS EXECUTION REPORT

Task: 4 / 14
Title: Real n8n integration
Status: PASS

Recorded: 2026-11-01T22:47:45.948958+05:30

Implemented:

- Real optional n8n 2.45.7 community CLI runtime with one reviewed bounded calculation workflow; disabled by default.
- Registered n8n.calculate in existing Guardian Policy/ApprovalStore; reusable owner action snapshots and opaque one-time execution permits.
- Controlling-terminal Approve/Reject, exact-context authorization, scope revalidation, expiry, cancellation, restart denial and audited outcomes.
- Private offline worker, verified runtime/template/worker hashes, exact partitioned dependency lock and explicit cloud preparation helper.

Real versus simulated:

- REAL: approved IGRIS CLI -> Guardian -> actual n8n import/execute -> successful native SQLite execution record and result 12.
- REAL: rejected action did not execute; real active n8n CLI cancellation and OS isolation probe.
- FIXTURES: automated owner PTY decisions; six shared-authority tests use a labelled local time handler, not n8n mocks.
- Legacy authenticated HTTP-contract adapter remains simulated. No external n8n account, public webhook or general workflow service is claimed.

Tests and results:

- 224 regression tests PASS in 52.419 seconds; repository secret scanner, CI structure/import checks and compileall PASS.
- Actual IGRIS CLI approval/rejection acceptance PASS; source-bound evidence docs/validation/n8n-runtime-live.json.
- Actual observed n8n CLI cancellation PASS; owned container removed, result discarded, consumed authority not reusable.
- Actual OS probe PASS: UID1000, CapEff0, NoNewPrivs1, RO root/modules, no Docker socket, external ENETUNREACH; cgroups 2GiB / two CPUs / 128 PIDs.
- Dependency lock reconstructs original 1250279 bytes exactly; tampered partition rejected. Three typed runtime tests and original broker denial of n8n operation PASS.
- Failed attempts fixed: mount named modules broke Node resolution; corrected node_modules. Added upstream-required no-node-snapshot flag. Error-only logger hid real JSON result; fixed private info capture. Cancellation observer lacked required PID column; corrected query.
- Typed telemetry initially matched phone redaction; fixed recursive JSON string/field checking while preserving sensitive-string denial; real time fixture now passes.

Security review:

- No second Guardian: existing immutable Policy, ApprovalStore, ActionReview and terminal channel reused. AI never receives issuer, permit, store or Docker socket.
- Only bounded integer operands, immutable reviewed workflow and finite nodes; no arbitrary command, workflow, URL, credentials or paid operation.
- Actual worker boundary consumes process-local exact-action permit; DB status forgery alone cannot authorize, and restart has no runnable snapshots.
- Separate offline n8n profile permits only private task-owned runtime prefix; original three-tool broker remains unchanged and rejects n8n.calculate.
- No secrets or binaries committed; optional native asset hashes/provenance recorded honestly. No paid feature, production change, main merge or Mac install.

Performance:

- Actual n8n CLI runtime 12.568s; approved total wall 74.113s; rejected total wall 26.332s.
- Cancellation after actual CLI observation 0.697s including verified removal.
- Runtime integrity hashing approximately 26–35s per pass; about 2.6GiB optional runtime on temporary storage. These are Linux cloud measurements, not Mac or measured peak RSS.

Known limitations:

- Only one on-demand local calculation; chat retains original three tools. No general n8n webhooks, external workflow authentication or customer automation connected.
- Cancellation is process-level startup cancellation of this owned offline runtime, not a verified remote API or rollback of completed external actions.
- Same-user parent manipulation, local DB rollback and shared-kernel/container risks remain. Not claimed fully sandboxed.
- Integrity revalidation currently shares sixty-second terminal deadline; late owner decisions can require a fresh review.
- Clean rebuild helper was lock-tested but not rerun with a second full tree due temporary disk budget. Exact image/Node/tree pins are specific to reviewed cloud setup; other builds/ARM require review and real validation.
- Official SQLite legacy release has no supplied digest/signature; local hashes pin TLS-downloaded asset, not an independent signed build attestation. Transitive vulnerability/license review continues in Task14.

External requirements:


Files changed:

- README.md
- docs/integrations/n8n-runtime.md
- docs/integrations/n8n.md
- docs/validation/n8n-cancel-live.json
- docs/validation/n8n-isolation-live.json
- docs/validation/n8n-runtime-live.json
- integrations/n8n/Dockerfile
- integrations/n8n/lock/manifest.json
- integrations/n8n/lock/part-001.json
- integrations/n8n/lock/part-002.json
- integrations/n8n/lock/part-003.json
- integrations/n8n/lock/part-004.json
- integrations/n8n/lock/part-005.json
- integrations/n8n/lock/part-006.json
- integrations/n8n/lock/part-007.json
- integrations/n8n/profile.json
- integrations/n8n/worker.py
- scripts/prepare_n8n.py
- scripts/test_n8n_cancel_live.py
- scripts/test_n8n_isolation_live.py
- scripts/test_n8n_runtime_live.py
- src/igris/guardian/activities.py
- src/igris/guardian/approvals.py
- src/igris/guardian/policy.py
- src/igris/integrations/__init__.py
- src/igris/integrations/n8n_cli.py
- src/igris/integrations/n8n_runtime.py
- src/igris/isolated.py
- tests/test_guardian_tools.py
- tests/test_n8n_lock.py
- tests/test_n8n_runtime.py
- tests/test_owner_actions.py
- workflows/n8n-bounded-calculation.json

Commands executed:

$ python3 scripts/prepare_n8n.py
$ python3 -m unittest discover -s tests -q
$ PYTHONPATH=src python3 scripts/test_n8n_runtime_live.py
$ PYTHONPATH=src python3 scripts/test_n8n_cancel_live.py
$ PYTHONPATH=src python3 scripts/test_n8n_isolation_live.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ python3 scripts/check_ci.py
$ git diff --check

Git commit:

- Verified implementation: 083be4212950e41793d1a83452e856d9b952d95d
- This report is recorded in a following documentation commit; remote tip is checked after publication.

Git delivery:

Connected GitHub App publishes the exact staged tree using expected-head fast-forward; remote branch SHA is verified separately. Git CLI authentication unavailable.

Next task:

- 5

Approval required:

- No for authorized development/push. Mac access, production, main merge, paid services and new host privileges remain unauthorized.
