# Integration testing — Step 47

Managed Linux cloud, 2026-10-30. “Real local” means the actual local Python/HTTP/
SQLite/filesystem/subprocess implementation, not a real upstream service.

| Interaction | Classification | Evidence / unverified boundary |
|---|---|---|
| Controller ↔ Guardian ↔ approval DB ↔ artifact | Real local | Actual isolated broker writes once after exact owner test approval, then reads/verifies; tests/orchestration and delivery_integration |
| Core ↔ Hermes adapter | Simulated / unavailable real | Mock plan schema and fail-closed real selection; no model/provider calls |
| Copied Hermes foundation | Partial source verification | 2674 source/config files and hashes, actual no-tool initialization branch; full runtime/dependencies/provider not run |
| Core ↔ n8n adapter | Real loopback HTTP carrying simulated workflow results | Authentication, schemas, correlation, bounded retries/idempotency; no installed n8n execution |
| n8n workflow definition | Static / isolated JS logic | Inactive importable JSON and Node fixture checks; no workflow imported into user's n8n |
| Core ↔ Ops Pilot | Simulated / imported schema projection | Source-derived export/job shapes; no actual Docker monitoring or repair connection |
| Guardian ↔ specialists ↔ adapted definitions | Real broker + simulated work | Hash-bound copied definitions, owner approval and lazy bounded registry; zero live specialist models |
| Business ↔ core mission references | Real local state, synthetic objective | Separate business lifecycle; references do not grant technical authority |
| Memory ↔ owner access ↔ SQLite ↔ backup | Real local | Persistence, correction, deletion, fact labels, consistent snapshot and restoration with synthetic knowledge |
| Mission Control ↔ role ↔ snapshot | Real loopback HTTP, supplied data | Auth/authz, escaped HTML/JSON, unknown defaults; no live health probes |
| Cost Guardian ↔ requested estimates | Real local gate, synthetic prices | INR 0; unknown/paid/positive denied; no billing account |
| Proposal ↔ approval store | Real SQLite approval rehearsal | Exact body/recipient binding; external submit always denied |
| Delivery/earnings ↔ owner records | Real local state/SQLite, simulated client data | Lifecycle/partial payments/profit; no customers, bank or payment gateway |
| Voice routing/PTT/personality | Local logic with test doubles | No speech model, audio API or physical microphone tested |
| Production deploy/rollback | Unavailable, denial tested | No provider, environment, credentials or approval to activate |

`test_delivery_integration.py` composes business/core, Hermes mock, actual local
n8n contract HTTP, Ops mock, Guardian subprocess, approvals, adapted specialist
fixture, memory, cost gate and dashboard snapshot. Successful mission evidence
remains `simulated`; local artifact enforcement is real. A missing real adapter
blocks without silently falling back to a mock. Existing focused integration
suites cover transport and role HTTP failures. No external integration is
represented as connected because a mock/contract test passed.

There is no automatic all-service runtime or production dashboard wiring. These
are composable operator APIs plus tests, not evidence of an autonomous working
assistant. Hosted GitHub Actions was not dispatched; costs remain unauthorized.
