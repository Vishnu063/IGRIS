# Final code review — Step 49

Scope: IGRIS-specific source, active dependencies, tests, CI, provenance and
documentation; selected upstream trust boundaries. Review performed by the
implementing agent (self-review), not an independent security/licensing audit.

| Finding | Resolution / verification |
|---|---|
| Development artifact omitted copied Hermes/Agency definitions, workflows, docs and tests | Fixed allowlisted text-source collection with all those directories and license notices, size/count bounds, per-file credential-pattern checks, deterministic hashes and private output. Tests verify copied-source/definition/workflow inclusion and exclusion of environment/runtime files |
| Artifact accepted unsafe source links / potential credential matches without dedicated regression evidence | Added rejected symlink and synthetic known-credential cases; no archive produced on preflight failure |
| README/architecture still claimed only foundation existed | Replaced with actual local-library state and explicit unavailable live runtime; removed brittle test tied to obsolete prose |
| Ledger lacked caps across invoices/payments/expenses | All four tables capped at 10,000 with transaction-bound checks; bounded integer amounts keep sums within SQLite integer capacity |
| Partial dashboard connection could occupy single server indefinitely | Added two-second accepted-connection timeout; still not a production availability guarantee |
| Payment replay/overpayment had inadequate direct regression coverage | Added actual SQLite tests for unconfirmed/duplicate/excess receipts and preserved total |
| Dashboard malformed auth/Host/provider failure needed explicit coverage | Added real HTTP 401/403/503 checks; unknown state never becomes healthy |
| No consolidated redistribution/license notice | Added THIRD_PARTY_NOTICES.md retaining upstream MIT locations and edition caveats; no project-wide license chosen for IGRIS-specific code |

Review of execution surfaces found fixed argument-vector subprocess calls in the
broker and trusted Git utilities. No general shell/eval handler is exposed.
The only test eval/exec executes the actual copied Hermes no-tool function branch
in an isolated test namespace; it does not start the full runtime. Broker FD-based
traversal refuses symlinks/hardlinks/special files. Approval validation remains
inside actual available mutation boundaries, not merely at planning time.

Active `src` dependencies remain Python standard library; pinned manual-only
GitHub Actions have read-only repository permission and do not dispatch
automatically. Node validates isolated workflow logic. Compile checks target
active source/tests/scripts, not all uninstalled upstream code. All 2674 copied
Hermes hashes and all 15 copied/adapted role mappings are verified by tests.
Root license/readme assessments do not validate entire external dependency trees.

No upstream repositories changed. No production deploy, forced push, branch
deletion, hosted CI run, paid service, Mac install or live client communication.

Remaining material limits: incomplete/disabled full Hermes runtime and dependency
audit; unavailable live service boundaries; no hostile same-user isolation;
operator-controlled approval issuance/clock/storage; regex secret detection;
unencrypted private state/backups; no persistent core mission engine or automatic
all-service UI wiring; no physical voice/M1 test. See security/validation.md and
the integration matrix. The intended fully operational assistant is not delivered
merely because numbered local scope records pass.
