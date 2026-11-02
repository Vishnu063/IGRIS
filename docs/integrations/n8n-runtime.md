> Current status: BLOCKED / QUARANTINED after Task 14 dependency audit (173 affected lock entries, including 6 critical and 78 high). Existing opt-in flags cannot bypass the adapter gate. The live tests below are historical Task 4 evidence. A patched, pinned tree and renewed audit/acceptance are required. See [audit evidence](../validation/n8n-dependency-audit.json).

# Real n8n: bounded private CLI profile

The original N8nAdapter remains a labelled simulated HTTP-contract client.
RealN8n is a separate optional execution profile using the actual community
n8n 2.45.7 command-line runtime on managed Linux x86_64. It does not connect to an
existing account, production deployment or remote webhook. No HTTP endpoint is
published. Internal CLI helper listeners stay inside a network-disabled container.

Audited the published package's execute/import commands, packaged LICENSE.md,
configuration include-list and native dependency requirements. The old --file
execution flag is explicitly unsupported by this version. IGRIS imports its
reviewed inactive workflow into fresh private SQLite, then executes by exact ID.
No enterprise feature, paid license, external credential or paid API is activated.
Community use here is personal/internal under n8n's Sustainable Use License;
enterprise-labelled code and third-party dependencies retain separate terms.

## Authorization and execution

Manual owner request -> registered Guardian profile -> typed integer operands ->
immutable ActionReview -> controlling-terminal Approve/Reject -> existing
ApprovalStore exact-context consumption -> opaque one-use ExecutionPermit ->
fixed offline worker -> actual n8n workflow -> verified execution record/result ->
Guardian audit. Policy, ApprovalStore and ActionReview are reused; no second
permission database, AI approval system or reasoning framework was introduced.

Only n8n.calculate exists: two integers from -1000 through 1000. Its reviewed
manual-trigger -> Set workflow evaluates their sum with n8n's expression engine.
The exact rendered workflow hash is in the action review. Raw workflow JSON,
node definitions, URLs, destinations, credentials, CLI arguments and expressions
are not accepted from the caller. NODES_INCLUDE further limits loading to those
two types. All sensitive or unknown workflow requests remain unsupported/denied.
The original three-tool broker still rejects n8n.calculate; its profile was not
widened. Chat currently retains that original tool set. This additional workflow
is invoked explicitly through the IGRIS CLI, not automatically selected by chat.

Approval binds actor, operation, full normalized arguments, workspace, request ID,
mission ID, policy version and execution-scope digest. Scope covers the pinned
runtime tree, image, worker and template. Original arguments are serialized once;
resume validates them and rechecks integrity. The worker validates its Guardian
permit immediately before launch. Missing, forged, reused, changed or cancelled
leases fail closed. Restart has no process-local proposal/permit snapshots.

Safe read capability does not remove the explicit approval requirement in this
profile. Expiry is capped at five minutes; terminal decision timeout is sixty
seconds. Current integrity revalidation also shares that sixty-second window,
so late decisions can safely fail at execution and require a new review. Full
runtime hashing takes roughly 26–35 seconds here. No automatic retry or reuse
of a consumed approval occurs. Calculation is deterministic and has no external
mutation. This is not general provider idempotency or transaction reconciliation.

## Runtime and isolation

The runtime is disabled by default. Model workers receive no approval database,
credentials or Docker socket. The fixed worker mounts only its code/template,
trusted Python, Node and a pinned dependency tree read-only. A separate explicit
n8n mount profile permits exactly the private task-owned /tmp/igris-task4-n8n
prefix. Other workers retain their repository-only mount rule. The original
read-only broker's kernel restrictions are unchanged.

Actual OS probes confirmed UID 1000, zero effective capabilities,
no-new-privileges, read-only root/dependency mounts, absent Docker socket and
external network ENETUNREACH. Cgroup limits observed: 2 GiB, two CPUs, 128 PIDs.
Worker wall deadline is 180 seconds; each CLI phase has its own deadline.
Private scratch space is bounded; file limit is 64 MiB. Fresh n8n encryption
material is generated inside the worker and never returned or logged by IGRIS.
No host environment/credentials are forwarded to Node. Raw library logs remain
inside disposable private files; only schema-validated numeric results return.

Actual n8n SQLite must contain one successful execution for the expected workflow.
Its output, request/mission correlation and rendered hash must match. A zero exit
code or mock HTTP response cannot satisfy acceptance. Fresh instances can each
use execution ID 1; correlate the ID with request, mission and workflow digest.

Cancellation was verified against an actual active n8n CLI startup process.
IGRIS terminates the tracked owned container and discards its result. This is
not a tested remote n8n cancellation API, rollback of completed actions or a
claim about external workflow side effects. Such workflows are not enabled.

Docker shares the cloud kernel. Same-user parent-process manipulation, database
rollback, host administrator access and container escape vulnerabilities are not
solved by this profile. It is not described as a fully demonstrated sandbox.
Mac/ARM profiles explicitly require separate verification; no x86 substitution.

## Preparation and manual use

Optional dependencies are outside the standard-library core. The exact npm lock
is partitioned on complete package records into scan-sized JSON files. The helper
verifies all partitions and reconstructs the original lock byte-for-byte.

$ python3 scripts/prepare_n8n.py

This checks only; it installs or activates nothing. --install is an explicit
Linux x86_64 development operation, requires the exact reviewed existing Node
binary and at least 4 GiB disposable temporary disk for a new installation.
It refuses to overwrite differing existing data. Installation uses npm ci with
scripts disabled, public registry, empty user/global config and a bounded private
cache. Only the explicitly pinned SQLite release binding is added. No global
package, Mac application or autostart mechanism is installed. A clean rebuild
has not been repeated here because the current temporary filesystem cannot hold
a second full dependency tree. Candidate fingerprint differences deny activation
until reviewed and tested; the helper never silently rewrites the trusted profile.

The installed runtime contains about 2.6 GiB including copied Node. Native SQLite
asset ID/URL and locally computed SHA-256 hashes are recorded in the profile.
Its old GitHub release supplies no digest/signature; TLS origin plus local pinning
is not a signed reproducible-build attestation. Node is copied unchanged from the
existing managed runtime. The pinned container image is built with the supplied
Dockerfile; a different rebuilt image needs review, repinning and real tests.

$ PYTHONPATH=src python3 -m igris.integrations.n8n_cli --enable-runtime --left 7 --right 5

The controlling terminal displays full action/arguments, scope target, risk,
digest and expiry. Chat stdin, transcription and model output are never decision
channels. Approve the displayed challenge or Reject. Without a controlling
terminal execution is denied. No background service remains after the command.

## Evidence and failures retained

Real approved 7 + 5 returned 12; n8n recorded success; Guardian consumed approval
once. Reject left the approval unused and executed no workflow. Automated owner
PTY inputs are test fixtures, not an assertion of human ergonomic validation.
Six core tests cover missing/forged/changed/expired/reused authority and restart;
the test time-handler fixture is not presented as n8n execution. Contract mocks
remain separately labelled. All 224 regression tests passed in 52.419 seconds.

Failed attempts: dependency mount was named modules instead of node_modules,
preventing standard resolution; corrected. isolated-vm's documented Node 20+
--no-node-snapshot compatibility flag was added; no model context/integrity check
was disabled. Error-only n8n logging suppressed the CLI's own JSON info output;
private info capture now permits strict result parsing. The cancellation observer
initially omitted Docker top's required PID column; its corrected query observed
the real CLI before cancellation. These failures were not counted as success.

$ PYTHONPATH=src python3 scripts/test_n8n_runtime_live.py
$ PYTHONPATH=src python3 scripts/test_n8n_cancel_live.py
$ PYTHONPATH=src python3 scripts/test_n8n_isolation_live.py
$ python3 -m unittest discover -s tests -q
$ PYTHONPATH=src python3 -m igris.guardian.scan

Actual workflow runtime was 12.568 seconds; total approved CLI wall time 74.113
seconds including integrity checks; rejection 26.332 seconds. Cancellation after
observed CLI startup took 0.697 seconds. These are Linux cloud measurements,
not M1 timings or peak-memory measurements. Dependency vulnerabilities/licenses
are reviewed again in Task 14; npm deprecation warnings remain recorded locally.
