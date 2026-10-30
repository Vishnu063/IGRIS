# Ops Pilot read-only audit — Step 16

Reviewed 30 October 2026 (Asia/Kolkata), revision
`349aa13e4d3be33665bd8335636fc315e71b5ee2` of
[Vishnu063/ops-pilot](https://github.com/Vishnu063/ops-pilot/tree/349aa13e4d3be33665bd8335636fc315e71b5ee2).
Scope: selected source/docs/test review, not a complete penetration test or live
installation. Upstream repository, configuration and infrastructure are unchanged.

## Pinned evidence

| Path | Git blob | Observation |
| --- | --- | --- |
| README.md | 5e553f2b45ee73d32574148ba47b08014e635fd5 | Early v0.2 one-owner/one-Docker-app preview; claims lab evidence, not production certification |
| SECURITY.md | 7c2bef124f45aad0f21d1ad4dc1864d68dce418e | Loopback-only, private capability login, separate approve/apply, Docker privilege risk |
| LICENSE | b62320ed5bb0412edbdd63e95eb18b86b8b1c89d | MIT, preserve notice if redistributing substantial code |
| pyproject.toml | 2a02c301c510047d44d7ffd2441007a634b3181a | Python >=3.11; pinned triage dependency ZIP |
| ops_pilot/web.py | bdfee93dd42958a714a6571473a1a3870f458cad | Actual routes, cookie session, Host/Origin checks, separate bridge roles |
| ops_pilot/service.py | See pinned source | Pilot.state/export_report/action; immutable container and daemon identity validation |
| ops_pilot/config.py | 77769054819fcaff4d0c17c1cfdf5b1debd29a46 | Exact target/context and health policy, private configuration writes |
| ops_pilot/runtime.py | 0c13de9445ee32b7b5c87b451f6c9bde25c7ce5e | Persisted maintenance/monitor controls and alert history |
| tests/test_pilot.py | bdd0a6af089d4bd0da227928ae9152ed290ff471 | Simulated Docker, real local HTTP/SQLite, approval/replay/identity/health cases |
| tests/test_daily.py | 6fd6026ddbf4cd2967d4080d899fd23aae0057d3 | Maintenance persistence, failed HTTP recovery and alert delivery cases |
| docs/VALIDATION.md | 0c634c5791bd644ffd0401f8764c75bd7b65d83d | Historical CI links and explicitly user-reported EC2 demo; not independently rerun here |
| ops_pilot/diagnostics.py | a421375b1e6d444ca50ee8d65d9d804842ae366e | Optional explicitly scoped read-only collectors, no general repair API |
| ops_pilot/ecosystem.py | See pinned source | Separate read/source event credentials and incident lifecycle |
| docs/FREELANCE.md | c377231e8771a5c37464388fd1a718a9525d1623 | Bounded freelance outputs; no connected model/payment/customer deployment |

Inspected pinned dependency `Vishnu063/devops-triage-assistant` revision
`d00b4fa5b861bd8a24935725300fe1d0a0ac538a`: triage/tool_engine.py
(blob 05f03a425eb0112e29f9a620953a1f4609e7c073), experience.py
(bed1410eda28ef10076d9c4cb2ebafa99b862e4d), evidence.py
(96f2cd84a021d68c6f18013894164e758882eed2), integrations.py
(3d26159038d7a9d6a37d502bd30427c4f363e5ef). No dependency installed.

## Supported interfaces and limits

- GET /api/state and /api/report require the startup owner session cookie
  named ops_pilot plus a valid loopback Host. The login capability changes on
  restart; it must not be collected into prompts, logs or source. /api/report
  exports schema_version 1, generated_at, target fields, monitor, diagnosis,
  report, plan, result, history, maintenance and alerts.
- POST /api/action requires owner session, valid Host/Origin and bounded JSON
  with action/optional plan_id. Supported actions include investigate, plan,
  approve, apply, cancel, monitoring/maintenance and optional advisory explanation.
  There is no generic HTTP /restart or arbitrary command endpoint.
- /bridge/* credentials authorize the freelance workspace, not Docker recovery.
  Do not send those keys to monitoring endpoints or infer owner authority.
- /integration/state, /integration/diagnostics and /metrics are optional ecosystem
  read surfaces, available only with an enabled EventHub and its read credential.
  They are not an unconditional monitoring export or recovery bridge.
- Python Pilot API exists but imports the pinned triage engine and Docker-backed
  adapter. Do not import/run it just to inspect source or assume it is a sandbox.

## Monitoring and evidence

The configured endpoint monitor and separate timestamped investigation may differ
in freshness. Collection errors are incomplete evidence, never healthy results.
Docker inspection records selected metadata, state, OOM and restart counts.
Bounded logs are reduced to signature counts from the last 100 stdout/stderr
lines; raw logs are discarded. IGRIS should consume those counts, not invent a
raw-log API. Optional diagnostics require separately configured native tools.

## Recovery semantics verified in source

Pilot plans only the supported restart. The command targets an immutable 64-hex
container ID and configured Docker context; daemon identity is rechecked. The
triage engine binds state/configuration, expires plans after five minutes,
requires a distinct explicit approval, consumes it before dispatch and refuses
reuse/changed evidence. Maintenance blocks planning, approval and execution.
Verification requires matching container identity/state AND application endpoint
health. A running container alone is not recovery. Restart may repeat a fault,
interrupt traffic, or have unknown outcome on timeout. No arbitrary code repair,
image/configuration edits, automatic retry or Docker restart rollback is supported.

## Risks and integration decision

1. Docker access may be host-root-equivalent. Neither owner session nor process
   separation supplies hostile same-user containment. Keep loopback and protected
   identities; never expose the dashboard publicly.
2. Owner capability is broad, not a dedicated least-privilege monitoring token.
   Default live transport stays disabled. An operator-provided sanitized export
   is the safer initial input; source-shaped fixtures verify mapping locally.
3. No independent Guardian hook exists at the actual Docker restart call in the
   audited source. A wrapper checking approval only before POST /api/action would
   not prove enforcement against alternate callers. DO NOT enable live recovery
   under this plan. Step 20 may implement the explicit simulation and a disabled
   live recovery port; upstream boundary work needs separate authorization.
4. Local state is not encrypted or tamper-proof against its owner/root; logs,
   health URLs, identifiers and downloaded reports can contain private metadata.
   Filter exported data again and reject stale/mismatched scope.
5. MIT applies to Ops Pilot; this is not a full transitive dependency/license,
   native CLI supply-chain or long-running production review. Installation can
   fetch dependencies; no installer/CI/Docker/systemd work was run here.

Step 16 PASS means this evidence-based static audit is complete. Real service
connectivity, actual Docker recovery, M1 compatibility and deployment isolation
remain PENDING_EXTERNAL_VERIFICATION. Subsequent steps can safely test strict
export mapping, deterministic diagnosis/recommendations and simulated recovery
without modifying Ops Pilot or claiming its real service is connected.
