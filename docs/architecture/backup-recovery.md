# Backup and recovery

Fixed private archive contains validated disabled-feature/zero-budget
configuration, non-executable project/mission/business state references, a
consistent approved-memory SQLite snapshot and per-entry SHA-256 manifest.
Secrets, environment files, approval databases, credentials and executable
actions are excluded by schema. There is no full directory sweep. Backup size
and memory records are bounded, and memory contents are revalidated.

The operator retains the returned archive digest separately. Restore requires
that trusted digest plus content hashes; an archive's own editable manifest is
not authenticity evidence. No extraction by archive filenames occurs. Only the
fixed names can be written, into a new private directory; existing live state
cannot be overwritten. Production restore is always blocked. Restoration never
resumes a mission, revives an approval, enables a feature or executes a rollback.
Credentials must be re-provisioned privately and approvals freshly issued.

Tests remove knowledge, restore into a disposable directory and reopen real
SQLite. Wrong identity, traversal archives, sensitive/approval state and
production targets are denied. Rollback preparation names exact prior version
and artifact plus impact/data-compatibility/health review; real provider rollback
is unavailable. Development code rollback remains the disposable Git workflow.

Archives are not encrypted or signed. Owner-only storage and a separately trusted
digest are essential; same-user attackers and filesystem races remain outside
this prototype's guarantee. Snapshot consistency spans the memory database only,
not a global transaction across business/earnings/configuration. Exporting the
earnings database, scheduling, off-site retention and backup rotation are manual
future work. Deleted knowledge can persist in older backups until they expire.
