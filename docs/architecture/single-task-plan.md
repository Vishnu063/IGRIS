# Single-task implementation plan

Baseline: develop at 2592bf2b69902c43f5d1934435eaf7787915b53c, initially clean. Inspection covered README, original report statuses/scopes, the three activation milestones, fourteen completion reports, controller/chat, Guardian, worker transport, specialists, dashboard and Ops Pilot source/provenance. Existing models, source and user data are retained.

Existing: real Hermes with native execution disabled, per-worker cross-process locking, one dashboard execution thread, exact Guardian approvals, disposable-target read-only Ops Pilot worker, owned launch acknowledgement/cleanup and optional warm inference. Missing: one mission-wide reservation across entry points/approval waits, durable retry identity, normalized verified task results, and explicit resident Ops component lifecycle. Mac/physical voice acceptance and quarantined n8n remain blocked.

Baseline regression: 280 tests run, one intermittent dashboard approval test failed (valid decision returned HTTP 400). Investigate typed digest-confirmation handling rather than weakening security. Record the failing baseline and focused rerun.

1. Add a small standard-library foreground coordinator with a process lock, private SQLite metadata journal, idempotent IDs, cancellation and fail-closed crash/cleanup handling. It is scheduling, never permission.
2. Wire existing chat and Guardian OwnerActions to hold that reservation through approval, verification and cleanup. Preserve one model and original execution restrictions. Keep HTTP control endpoints responsive and use wakeups rather than an idle polling loop.
3. Define a lazy trusted adapter catalog with metadata, lifecycle, permissions, health and cancellation contracts. Add no account credentials or job-platform automation. n8n is neither imported nor run in this architecture.
4. Add explicit Manual (default), On-demand and owner-authorized Monitoring Ops lifecycle, reusing its actual library, exact read proxy, scoped target, parsed exports and owned container cleanup. Stopping the connector must never stop the monitored application.
5. Test concurrency, replay/restart, cancellation, approval responsiveness, cleanup and lazy startup. Run real disposable Ops and Hermes acceptance and measure process/cgroup memory with methods and Linux limits disclosed. Finish with focused commits, regression/security checks and a report; no main merge or Mac changes.
