# Specialist approval and scheduling — Step 30

The registry contains 15 inert roles. Recommend one or two compatible roles/tasks
first; recommendation does not activate anything. The scheduler stores a bounded
sanitized canonical batch and returns its role list. request creates a pending
exact-action approval with reviewable roles, task kinds, mission and context.
Only a separately authenticated trusted owner may decide through ApprovalStore;
there is no model-facing issuance or automatic approval method.

run sends the proposed batch/reference to the independent Guardian process. Its
specialists.fixture operation requires an explicit specialist permission, strict
schema and a private external approval store. It rechecks sanitized content,
role/task compatibility, batch size and actor/workspace/environment/action-bound
single-use approval INSIDE the broker before producing any fixture result.
Role choice grants zero file, terminal, Git, cloud, financial or communication
permissions. The simulation handler has no provider or general tool callback.

Only approved deterministic checklist fixtures run. Real model activation is
unavailable; mode=real is rejected, not silently replaced with a mock. The broker
loads requested group metadata lazily and executes at most two requested fixture
roles serially, not 15 models concurrently. Existing CPU/memory/output and wall
timeout limits still apply. Metadata inspection is not specialist activation.
Contract-fixture helpers are trusted test utilities, not agent execution APIs.

Each scheduler permits one in-flight batch, rejects excess calls without a queue,
and retains at most 64 recommendations; explicit forget frees metadata but does
not revive an approval. This is a per-instance bound, not a global host scheduler.
Deploy one trusted scheduler per controller; OS isolation/process quotas and real
model cancellation are still prerequisites for future live specialist execution.
Multiple independent broker requests cannot reuse an approval because SQLite
consumption is atomic. Consumed approvals remain consumed if a worker fails.

Audit records cover pending requests, decisions, consumption/rejection and local
fixture outcomes without prompt bodies. Early schema/permission denials can
return before persistent audit insertion, as with the existing broker. Same-user
source/database tampering, clock rollback, immutable remote auditing and Mac
performance are not validated by these tests. No separate Agent Builder, daemon,
model download, paid inference, Mac install or service deployment is added.

Verification uses real Guardian child processes and SQLite, synthetic owner
choices and simulated role outputs. All 15 pass individually through the approval
boundary; tests also cover two-role batches, malformed/oversized scope, injection,
missing/pending/denied/expired/forged/mismatched/reused approvals, permissions,
actor/context changes, busy slots and concurrent replay attempts. This does not
prove actual frontend/security/voice/etc specialist competence.
