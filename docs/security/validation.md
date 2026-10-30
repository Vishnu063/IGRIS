# Security validation — Step 46

Date: 2026-10-30, managed Linux cloud, Python 3.12.14. This is source self-review
and automated local validation, not independent certification or a production
penetration test. No external targets were attacked or modified.

| Attack/control | Executed evidence | Scope/result |
|---|---|---|
| Unauthorized commands / argument injection | test_guardian_executor, test_security_validation | Real bounded subprocess broker rejects arbitrary shell, extra argv and forged authority; no marker file created |
| Traversal / symlink / hardlink / FIFO / size bounds | test_guardian_executor | Real local files and special files; refusals verified |
| Missing permissions / escalation | test_guardian_policy, test_security_validation | Default deny; body fields cannot grant trusted actor permissions |
| Missing / denied / expired / mismatched / replayed approval | test_approvals, test_specialist_scheduling | Actual SQLite plus broker; exactly one consumption; concurrent checks covered |
| Production / destructive / finance / communication activation | test_deployment, test_security_validation | Unimplemented real operations remain denied even with all policy permissions |
| Secret exposure | test_secrets plus full guardian.scan | Redaction/formatting cases and all tracked/unignored working files plus index blobs scanned; no configured credential patterns found |
| Prompt injection / third-party instructions | test_security_validation, test_reused_agents | Adversarial text remains data; cannot configure permissions or start copied Hermes. Adapted definitions are hash-bound. No live model tested |
| Cost manipulation | test_costs | Positive, unknown, paid-trial and invalid estimates rejected under INR 0 budget |
| Persistent state / dashboard | test_memory, test_dashboard, test_backup | Owner checks, private files, read-only role views, HTML escaping and unsafe restore refusal |

Baseline full suite: **155 tests passed** before adding three cross-feature
security cases. The final post-addition full suite passed **158 tests in 21.445s**.
Workflow/import checks and whitespace review passed. Configured credential scan
patterns were not weakened to pass vendored-source scanning. Per-step staged
changed-file scans supplement this full worktree/index scan.

## Unresolved risks and externally unverified controls

- Same-user OS containment is absent. A trusted process compromise can tamper
  with SQLite, policy objects/source or credentials; broker subprocess separation
  alone is not a container/security-user boundary. No hostile full Hermes run.
- Regex redaction/scanning misses unknown secrets and cannot certify all prompt
  assemblies. Vendored backend is not fully audited or dependency-resolved.
- Approval DB rollback/owner clock manipulation remain out of scope. Trusted
  owner issuance is a Python API, not a hardened authenticated approval service.
- Trusted development utilities are not agent tools. Configuration/path inputs
  to those utilities must not be exposed directly to an untrusted request.
- Dashboard is a small loopback prototype: no TLS/remote deployment, rate limit
  or comprehensive availability hardening. It displays supplied snapshots, not
  independently measured external health.
- Backup digests need a separately trusted record; archives are not encrypted or
  signed. Knowledge may remain in prior backups. Filesystem races are not
  eliminated by path checks.
- Real n8n/Hermes/Ops Pilot recovery, speech engines, billing and customer
  communications remain unavailable/unverified. Mock contracts cannot prove
  these services enforce Guardian at actual provider boundaries.

These limits prevent a claim that IGRIS is production secure or fully connected.
