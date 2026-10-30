# Production deployment approval — Step 25

DeploymentIntent requires exact target, immutable version, explicit component
scope, bounded expected changes and an artifact SHA-256. DeploymentGate.request
returns those review fields plus a pending approval. It never deploys. The
existing store binds actor, workspace, policy, environment=production and every
intent field; default policy lacks deploy permission.

rehearse_approval is a trusted development test helper: it consumes an exact
synthetic owner approval and returns deployed=false and execution_available=false.
It does not produce an execution capability and should not consume real owner
approvals merely to preview them. No user-facing approval UI is implemented.

Both the actual broker and DeploymentGate.deploy reject production execution,
even with an otherwise valid approval. No provider callback, deployment workflow,
secret, credential, paid service or production environment is configured. This
is stronger than approving a workflow and hoping a downstream tool checks it.
A future production implementation must stop for explicit owner approval of a
reviewable target/version/scope/changes and enforce it at the real provider
boundary, validate artifact provenance, isolate credentials and verify health.
No such activation or deployment is authorized by this plan.

Automated tests prove missing/pending/denied/expired/mismatched/reused approvals
cannot pass the rehearsal gate; a valid rehearsal still cannot deploy. Actual
Guardian subprocess tests confirm production requests remain blocked. No real
production target is touched. Hosting, rollout, rollback and production health
remain unverified.
