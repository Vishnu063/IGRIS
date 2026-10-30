# Approved recovery workflows — Step 20

Implementation status: simulated workflow tested; LIVE RECOVERY BLOCKED.
The audited provider supports a reviewed Docker restart, but its real mutation
boundary has no independent Guardian hook. LiveOpsRecovery.request/run therefore
raise AdapterUnavailable regardless of any approval supplied. No owner cookie,
Docker socket, cloud credential or provider POST transport is enabled here.
Changing Ops Pilot requires separate authorization; its repository is unchanged.

## Supported simulation

SimulatedRecovery exercises the corresponding approval → dispatch → health
verification → outcome/audit lifecycle in a disposable workspace. The separate
Guardian broker implements only ops.recovery.fixture, never a real Docker action.
It cannot execute the plan's command array: that array is checked as data against
the audited restart shape and is never passed to a shell/subprocess/provider.

A trusted test operator initializes private fixtures/ops-state.json and an
existing fixtures/ops.lock. The file must explicitly declare simulation=true.
It contains fixed target identity, eligible stopped/restarting state, maintenance
status, a five-minute provider plan, separate synthetic provider approval,
single-use status and one predefined outcome scenario. No automatic fixture,
provider approval, Guardian approval or real-target discovery occurs.

The request binds plan ID, exact fixture-file SHA-256, context, immutable
container ID, daemon identity and local health-URL identity. Guardian also binds
trusted actor, canonical workspace, environment, policy version and full request
in its approval digest. Cloud, read and file-modification capabilities are all
required; defaults grant none. These are simulator permissions, not provider
credentials or permission to spend money.

Inside the broker, no-follow descriptor traversal and private regular-file
checks protect fixture/lock access. A nonblocking per-target lock serializes
cooperating broker instances. The broker validates state hash, maintenance,
identity, eligible state, exact plan/command and unexpired unused provider
approval; then atomically consumes the exact Guardian approval. It rechecks
provider expiry after possible database wait and before simulated dispatch.
The bounded state replacement is atomic, uses private temporary files and is
read back for verification. Source/config files or other targets cannot be
selected through this operation. Raw report/log bodies are not stored in audit.

## Outcomes and failure reporting

- verified means the **simulated fixture** has the expected matching running
  container AND healthy endpoint flag. It is not a real application check.
- needs_attention means the simulated container can be running while its
  simulated endpoint fails. Never report recovery from running state alone.
- failed and unknown are separate scenarios. No automatic retry or rollback is
  offered. Consumed provider/Guardian authorizations cannot dispatch again.
- rejected_or_failed means Guardian denied execution or the local operation
  failed; its sanitized reason helps the owner inspect the problem.

Audit records use the existing private SQLite approval store: request, decision,
consumption/rejection and execution success/failure. Successful dispatch and
failed health are not relabeled as recovery. The fixture file and approval DB
are not one distributed transaction; a crash can leave an unknown outcome.
Inspect actual local fixture state and audit, obtain fresh reviewed evidence and
never restore/reuse consumed approvals. Missing/changed stores deny execution.

## Verification and limits

Tests cover separate approvals, denied/pending/missing/forged/expired approvals,
provider-plan expiry, changed identity/state/command, maintenance, explicit
simulation label, permission restrictions, symlinks, concurrent execution,
success, failed endpoint, dispatch failure, unknown outcome, audit and replay.
The broker, SQLite, file locking and local fixture writes are real. Provider
states, restart and endpoint outcomes are simulated; no actual Docker or health
request is performed by this module.

OS isolation, trustworthy time, tamper/rollback-resistant approval storage,
production authorization, actual upstream boundary enforcement and real Docker
recovery remain unverified prerequisites. Same-user tests cannot prove containment
of hostile local code. Simulation cannot satisfy those live prerequisites.

As with the existing broker, early schema/scope/permission failures can return a
sanitized denial before persistent audit insertion. Complete denial-event
collection is not implemented or claimed as production-ready audit coverage.
