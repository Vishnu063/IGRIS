# Repair recommendations — Step 19

Recommendations are immutable proposals, never executable commands or approvals.
They name evidence, required permission categories, owner approval needs, risks,
prerequisites, source origin and the fact that live execution is unavailable.

Only a fresh unhealthy endpoint plus eligible stopped/dead/restarting state,
immutable identities and an upstream-offered restart can produce a restart
proposal. Maintenance, missing identity/action, stale/incomplete evidence,
conflicting health and running-but-unhealthy cases do not invent that repair.
The diagnosis digest must match the current monitoring evidence.

Example: the source reports a stopped container. IGRIS recommends reviewing its
filtered logs and preparing an explicitly approved restart. It warns about
intentional stops, traffic interruption, repeated faults, unknown outcomes and
lack of automatic rollback. Permission to read is not permission to repair.
No source/image/database edit, arbitrary shell command or automatic restart is
supported. Real provider and Guardian approvals remain separate prerequisites;
a mere proposal cannot satisfy either. Step 20 tests the simulated workflow.
