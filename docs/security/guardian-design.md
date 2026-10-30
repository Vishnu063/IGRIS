# Independent Guardian security architecture

Step 6: design and threat-model review only. No security service is operational
at this step. Steps 7–10 implement progressively testable controls.

## Security objectives and assets

Protect project and customer files, credentials, approvals, financial allowance,
production infrastructure, external communications and audit integrity. Default
to no permissions. An AI proposal, retrieved instruction, memory or provider
response can never create execution authority. Preserve ₹0 spending and forbid
production deployment in this execution plan.

## Independent enforcement and trusted computing base

Guardian is a deterministic, model-free execution broker in a separate process.
Its operation registry and validation code are trusted application code. The
caller sends a bounded typed action; it cannot send Python, shell fragments,
policy definitions, identity claims or approval-issuance commands. Authorization,
argument validation, approval consumption and restricted execution occur together
inside the broker, not just before routing to a model or external workflow.

A trusted operator supplies workspace, actor and immutable permissions at broker
startup. Agent-produced JSON cannot replace that identity or startup policy.
Keep the broker source, policy and approval database outside agent-writable
storage in any future deployment; changes to these require operator review.
Use a fixed request channel (initially a short-lived subprocess stdin/stdout
protocol), a scrubbed child environment, narrow operation handlers and OS limits.
Only the trusted launcher can create that channel. There is no network listener.

The trusted computing base includes Python/OS, broker and launch code, configured
executable, operator policy, clock and approval store. Availability and integrity
of these dependencies matter; failure denies execution. Policy and approval
issuance are not exposed to the requester. External adapters must enforce the
same controls on each actual side effect; otherwise disable mutations.

## Required deployment trust boundary

A separate Python process provides independent decision logic and channel
separation, but DOES NOT isolate a malicious process with the same OS user or
root privileges. Such a process could alter code, files, policy, database or
launch its own unrestricted interpreter. Do not deploy an untrusted agent with
arbitrary shell access alongside the broker and call that a secure sandbox.

Future deployment requires different OS identities/containers or equivalent
restrictions: agent has only the request channel, no broker code/policy/secret
write access, no approval-store access, no direct provider credentials or general
execution tools. A restricted broker owns narrow filesystem/provider access.
Network egress must also be restricted outside Python. This cloud development
workspace has not established that deployment isolation; test processes use the
same user. Never report process tests as proof of hostile same-user containment.
No real agent, provider credentials, production target or financial executor is
enabled here. Missing deployment isolation blocks future sensitive live use.

## Threats, controls and evidence plan

| Threat / untrusted input | Required control | Verification owner |
| --- | --- | --- |
| Prompt injection in tasks/documents/provider output | Data cannot become policy or an operation name outside the registry | Steps 7–8, 46 |
| Permission escalation or forged actor | Trusted startup identity, enum permissions, exact operation mapping, default deny | Step 7 |
| Command/argument injection | No shell; fixed executable/argv; exact schemas, timeouts, resource bounds | Step 8 |
| Path traversal, symlinks, races, hardlinks | Workspace-relative paths, descriptor-based no-follow access, restrictive file types and size bounds | Step 8 |
| Secret/customer data exfiltration | Sensitive paths denied, no inherited credentials, redaction at output/log/prompt boundaries, restricted egress | Steps 8–9, deployment |
| Approval forgery, mismatch, replay or expiry | Trusted issuance, exact canonical action digest, server clock, atomic single-use consumption | Step 10 |
| Destructive operation disguised as ordinary write | Narrow non-destructive handlers only; approval does not create an unsupported capability | Steps 8, 10 |
| Unauthorized deployment/spending/communication | Deny unsupported operations even with approval; add future provider gates before activation | Steps 10, 25, 38, 43 |
| Resource exhaustion | Bounded JSON/file/output sizes, wall/CPU/memory/file descriptor limits | Step 8 |
| Policy/code/database tampering | Protected deployment identities, ownership and access controls; fail closed on invalid policy | Deployment prerequisite |
| Stale recovery/backup revives approval | Approval expiry/replay checks independent of mission memory; no authority from restore | Steps 10, 45 |

## Approval and audit intent

Approval is not permission: both must hold. Bind approvals to authenticated
actor, operation, complete arguments, workspace, environment, policy version,
amount/currency where relevant and an explicit expiry. Recheck at execution.
Use unguessable IDs and atomic consumption; denial/missing/expired/mismatched
records cannot authorize. Do not automatically reuse approvals after failure.
Trusted approval issuance must follow a real owner review; tests label synthetic
approvals and do not contact clients, providers or production systems.

Audit minimally: correlation ID, trusted actor, operation, outcome, reason code,
time and action digest. Do not log raw arguments, tokens or customer bodies.
No log statement may claim healthy/secure without evidence. Persistent immutable
remote audit and tamper-resistant storage are not established in this phase.

## Step 6 review findings

- Reviewed boundaries, assets, threats, provider nesting and deny-on-failure rules.
- Resolved architectural ambiguity: subprocess separation is not same-user OS
  isolation; deployment containment remains an explicit blocking prerequisite
  for sensitive live integrations.
- Credentials must never be passed to reasoning/specialist processes.
- Unimplemented provider operations remain denied even if an approval exists.
- Security effectiveness requires the later adversarial tests; this review is
  self-review, not an independent audit or hardware/deployment certification.
