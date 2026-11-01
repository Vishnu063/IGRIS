# Real read-only Ops Pilot integration

Task 5 pins unmodified `Vishnu063/ops-pilot` at
`57c46ce40a62a2cb129a1034f631b928831c265f` (MIT, Python 3.11+),
and its sole dependency, Triage at `d466ca4e1cdd93d02274145c0b12e73f76863b6d`
(MIT, no Python dependencies). Archive and complete source-tree hashes are in
`integrations/ops/profile.json`; source remains ignored development storage.
This audit supersedes earlier source observations only for this pinned runtime.

The upstream `Pilot` library, default `DockerAdapter`, health probe, `tick()` and
`export_report()` run unchanged. This is a real local library integration, not
an HTTP connection to an existing deployment. Watch threads, owner web cookies,
plan/approve/apply and restart capabilities are not exposed. The legacy fixture
adapter remains explicitly separate.

The owner authorizes `ops.monitor` through existing Guardian `OwnerActions`,
`ApprovalStore` and a one-use process-local execution lease. A private authenticated
Unix Docker proxy allows only bounded reads of one immutable disposable container
ID and selected daemon identity. Inspect responses omit environment and mounts.
Raw logs go only to the isolated worker; upstream produces signature counts.
A loopback bridge forwards actual application health over its private Unix socket.
The model receives no daemon socket, proxy credential or execution service.

The worker has no external network, root writes, capabilities or privilege gain;
it uses one GiB memory, two CPUs, 128 processes and a 90-second wall deadline.
Cancellation cleans only the tracked worker. The explicit demonstration creates
and removes a tiny task-owned Docker application; this setup helper is never a
model tool. Existing containers and deployments are outside its allowlist.

```sh
$ python3 scripts/prepare_ops_runtime.py --prepare
$ PYTHONPATH=src python3 -m igris.integrations.ops_cli --enable-runtime --demo
$ PYTHONPATH=src python3 scripts/test_ops_runtime_live.py
```

Prerequisites are the previously verified Linux x86_64 portable Python, Docker
runtime and thin image pinned in the profile. Setup downloads only reviewed
source and copies an already installed hash-matching Docker client; no service
starts implicitly. Approval uses a separate controlling terminal. The demo
requires explicit startup and stops on exit. The profile is disabled by default.

Actual acceptance in `docs/validation/ops-runtime-live.json` observes a running,
healthy application and the same container after an explicit test-only stop:
exited and unhealthy. Restart advice remains proposal-only. Wrong target,
restart route and invalid read credential return 403, 403 and 401. Both real
monitoring grants are consumed once, sources remain unchanged, and cleanup is
verified. Automated owner decisions in this test are fixtures; Docker, HTTP,
Ops Pilot, Guardian and filesystem execution are genuine.

This is not a full sandbox against the host owner or Docker administrator.
Same-user process inspection, local database tampering/rollback and compromised
upstream dependencies remain risks. The daemon proxy is trusted host code; its
credential and state remain private but same-user access is not OS isolation.
No production account, external Ops Pilot service, real customer workload,
ARM64/Mac execution or remediation has been validated or enabled.
