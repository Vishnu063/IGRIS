# Action-bound approval controls

Step 10 implements a trusted-only approval store and enforcement at the broker's
actual file-creation boundary. It is local development infrastructure, not a
production authorization service or an approval dashboard.

## Requests and owner decisions

`ApprovalStore.request` creates pending, unguessable 32-character IDs for all
required risk categories: production deployment, destructive operation, sensitive
file change, external communication, paid service, financial transaction and
outside-scope change. New text artifact creation is additionally approval-gated.

A canonical SHA-256 digest binds trusted actor, canonical workspace, environment,
policy version, operation and complete arguments (including amount/currency,
target/version/scope when present). JSON key order is irrelevant; changing any
value invalidates matching. The trusted requester supplies a TTL of at most one
hour, default five minutes. A pending request is not an approval.

The owner must review the original exact action in the trusted application and
compare its digest; the database summary deliberately stores no argument bodies.
`decide(id, approve=..., reviewed_digest=...)` accepts only an unexpired pending
record with that digest. Denied decisions cannot be upgraded; issue a new request.
No approval issuance/decision method is exposed through broker request JSON,
models, memory, adapters or a network listener. The future UI must authenticate
the owner independently before calling this trusted API.

## Exact execution boundary

The trusted launcher supplies immutable policy, workspace, environment and an
existing private approval database outside the project workspace. Permission,
request/argument validation, supported-handler checks and approval matching all
apply. Approval cannot grant permission or create an unsupported tool.

For the one supported mutation (`file.create`), the broker consumes an approved,
unexpired, exact-matching record with an SQLite immediate transaction, then
checks the trusted clock after acquiring the transaction lock, then creates a new UTF-8 `.txt` or `.md` file inside an existing `artifacts/` directory.
No overwrite, append, deletion, source/configuration edit, symlink traversal,
outside-workspace write or detected-sensitive content is accepted. New files
use mode 0600 and O_EXCL/O_NOFOLLOW, with descriptor-based parent traversal.
Only development/test environments are supported by the launcher/broker.

Every other risk-category operation remains non-executable even with an approved
request. Real production deployments, messages, billing and financial actions
have no handlers. Future providers require their own boundary validation and
appropriate schemas before enabling them; generic argument dictionaries in
approval vocabulary are not verified provider contracts.

## Storage, auditing and failure semantics

The operator initializes the SQLite file with mode 0600 in an existing,
operator-owned private directory (no group/other access); nonregular files,
symlinks and hardlinks are rejected. Never put this database in the Git workspace,
backups accessible to agents or prompts. The trusted operator/issuer can write
it; this is not an authority separation against a malicious same-user process.

Audit rows contain ID, actor, operation, timestamp, digest and event, never raw
argument bodies. They record requests, decisions, consumption/rejection and
execution outcomes. The store is not encrypted, remotely immutable or a full
system audit; IDs and metadata should still be treated as private. Early schema
or permission failures before store access return sanitized denials without a
persistent audit row. A later authenticated service needs complete denial-event
collection without logging sensitive input.

Consumption is single-use even on execution failure. A failed/partial write may
leave a partial new file; do not automatically delete it or reuse the approval.
If execution or audit acknowledgement has an unknown outcome, reconcile actual
state and request a new reviewed action rather than retrying blindly. Approval
consumption and filesystem writes are not one distributed atomic transaction.

The trusted wall clock must be accurate. Database/clock rollback by an operator
or compromised host can undermine expiry/replay history: OS isolation,
rollback-resistant storage/time and backup recovery policy remain prerequisites
for sensitive deployment. No database restoration or sensitive live agent is
configured here. Exceptions and corrupt/missing/locked stores deny execution.

## Verified evidence

Tests use synthetic approvals and disposable files, with a real SQLite store and
real broker child processes. They cover missing/pending/denied/forged/expired
approvals, content/actor/workspace/environment mismatches, reviewer-digest checks,
permission requirements, replay, simultaneous consumption, simultaneous real
brokers, failed-execution consumption, restricted file creation, protected store
permissions and unsupported risky operations. None proves a real external
service, production permission workflow or hostile same-user containment.

Review fixes: expiry is checked after lock acquisition, risk categories are
immutable, and prefixed secret-label regression cases pass. The test clock and
database-access delay wrapper are synthetic; concurrent store/broker operations
use real SQLite and child processes.

Step 20 additionally gates the explicitly named ops.recovery.fixture simulator.
It requires both a synthetic provider decision and exact Guardian approval.
No live provider mutation handler is added.
