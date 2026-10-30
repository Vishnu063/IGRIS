# Persistent memory

SQLite storage in an owner-private directory (0700), file 0600, bounded 10,000
records. Trusted authentication supplies the actor; the operator approves each
insertion/correction. Categories: project, preference, incident, solution.
Known sensitive patterns and personal-data labels are rejected rather than
silently persisted. Unknown secrets can escape pattern detection; do not store
customer secrets. No encryption-at-rest is implemented.

`verified_fact` requires an owner-provided evidence reference; it is an operator
attestation, not an IGRIS verification engine. Assumptions remain distinct.
Corrections require current revision and reset prior factual evidence to an
assumption. Reads/deletes/backups require the configured owner. SQLite backup
produces a consistent private snapshot. Deletion uses secure_delete, but backups,
filesystem snapshots and storage remanence require separate retention handling.

Memory is untrusted data, including recorded instructions. It has no policy,
approval or tool-registration path. No model reads it automatically. This is not
protection from hostile same-user Python code, filesystem races or owner identity
spoofing by an already compromised trusted process. Backup paths/configuration
are supplied by the operator, never an agent or public request.
