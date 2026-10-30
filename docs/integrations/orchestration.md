# Three-system simulated orchestration — Step 15

This prepares a bounded interaction among IGRIS, Hermes, n8n, Ops Pilot and
Guardian. It does not claim those three external systems are connected.
No real Ops Pilot API is assumed or audited before Step 16.

## One supported scenario

1. An owner-created mission routes to a trusted SimulatedInspection handler.
2. MockHermesAdapter returns a strict inspect_fixture proposal, never commands.
3. N8nAdapter in explicit local_contract mode submits a read-only fixture request
   to an authenticated ephemeral HTTP fixture. Responses are correlated and
   validated; the origin remains simulated even though the HTTP round trip is real.
4. MockOpsPilotAdapter supplies typed synthetic observations. It has no live
   transport, credentials, recovery or arbitrary code-repair interface.
5. The handler proposes a simulation-labeled report at a fixed mission-specific
   path inside artifacts/. It requests a pending action-bound approval and the
   controller stops in awaiting_approval. No file exists at this point.
6. A synthetic owner decision in tests approves the exact digest. Resuming with
   its reference does not itself grant authority: the separate Guardian broker
   rechecks policy, scope, content and database approval at file creation.
7. A second Guardian-scoped read verifies artifact content. Only then does the
   controller report simulated success. No actual application is repaired or
   declared healthy. Resumption does not replay provider orchestration.

The trusted application owns policy, routes, adapters, workspace and store.
Untrusted text cannot select arbitrary tools, targets, paths or credentials.
The mutation is a real local test artifact in a disposable directory, not an
Ops Pilot recovery, production deployment or change to the live repository.

## Evidence matrix

| Component | Evidence exercised | Status |
| --- | --- | --- |
| IGRIS controller | Real local state transitions and sanitized reports | Tested locally |
| Hermes | Deterministic planner fixture; live selection unavailable | Simulated; real connectivity pending |
| n8n | Real authenticated loopback HTTP against fixture; inactive template JS tested with Node | Simulated service; actual n8n import/runtime pending |
| Ops Pilot | Typed synthetic snapshot; default real port unavailable | Simulated; source audit deferred to Step 16 |
| Guardian | Real child process, permissions, exact approval consumption and scoped file access | Tested locally; hostile same-user isolation unverified |
| Approval store | Real private SQLite with synthetic test-owner decisions | Local enforcement tested; production identity/clock/storage prerequisites remain |
| Artifact | Real disposable file with explicit simulation label and read-back verification | Local fixture only |

## Negative cases and remaining limits

Tests cover denied/forged approvals, changed action after review, missing
permissions, malformed workflow output, unavailable live Hermes/Ops Pilot and
post-approval filesystem failure. None may become successful or create an
unauthorized report. The broker, not the model/controller's assertion, decides
whether a side effect is permitted.

This scenario does not implement monitoring/diagnosis/recovery capabilities in
Steps 17–20. Ops Pilot stub types are an IGRIS-owned test port, not a statement
about upstream supported APIs. No other repository was modified.

No multi-user deployment, durable mission recovery, real model, actual n8n
runtime or real Ops Pilot service has been validated. All live feature flags
remain disabled. Mock adapters and trusted route code run under the same cloud
OS user; they are not containment of malicious executable third-party code.
Before any future nested real workflow mutation, Guardian must protect the
actual side-effect boundary; merely approving a workflow is insufficient.

Run tests only in a development environment allowing loopback sockets:

```sh
$ python3 -m unittest discover -s tests -v
$ PYTHONPATH=src python3 -m igris.guardian.scan
```

This Codex sandbox needs command-level network permission for local socket tests.
No public listener, credentials or paid service is required.
