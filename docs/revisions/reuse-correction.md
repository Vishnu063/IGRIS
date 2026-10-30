# Reuse correction C01 — before Step 31

Status: PASS for source copying/adaptation and local contract verification.
User explicitly selected BOTH copied Agency Agents specialists and Hermes core.
This supersedes the earlier reference-only design decisions in Steps 11/26–30;
those records describe historical work, not the current reuse strategy.

## Copied source and changes

vendor/agency-agents retains the 15 selected upstream definitions verbatim and
its MIT notice. integrations/agency-agents contains modified copies, not newly
written replacement personas. Adaptations retain technical methodology, remove
identity/memory and success-metric sections, replace the incident emergency
exemption, and add IGRIS permissions/approval/budget/hardware constraints.
The registry loads adapted definitions by role; scheduler approval includes each
definition SHA-256. No definitions are installed in the owner's Codex/Mac config.

vendor/hermes-agent contains 2674 backend source/configuration files copied from
revision 2d2808ee84549f9836b0056750265058e5488a8a, with MIT notice. It is a curated
backend subset, not a complete installable distribution: desktop, most assets,
shell installers and dependency lock are absent. The manifest records original
and modified hashes. Original upstream repositories remain unchanged.

The copied agent/agent_init.py is patched so an explicit empty tool list returns
before tool/plugin discovery and startup migrations. A test executes the actual
copied function's no-tool branch. This is not proof of whole-process containment
or a complete startup audit. Additional local edits change only reviewed prose/
diagnostic examples that falsely matched the credential scanner. Detection rules
were NOT relaxed. Manifest patch entries record those edits and source hashes.

hermes_core_spec maps IGRIS role definitions to actual AIAgent constructor kwargs:
no tools, context-file loading, claimed memory, background review, trajectories or
checkpoints. The earlier checklist fixtures remain tests, not the real specialists.
The real activation method remains unavailable until an isolated compatible
Python 3.14 runtime, dependencies, zero-cost provider and side-effect boundaries
are verified. Python 3.12 cloud tests do not prove Hermes inference works.

## Verification

Source/definition hash checks, role mapping, original-copy size/methodology,
actual copied no-tool branch and existing approval/schema tests were exercised.
All live model connections remain unverified. No runtime installed, paid service
activated, Mac operation, production deployment or third-party instruction
execution occurred. This correction does not advance numbered Step 31.

Final local suite: 124 tests passed. Credential-pattern scanning covers copied
source and passed after reviewed prose-only source edits; no patterns were
suppressed. Adapted definitions were whitespace-normalized; vendor whitespace is
preserved with an explicit formatting-only .gitattributes rule. Source/header
checks, constructor mapping and approved-specialist contracts pass. Initial
copied upstream whitespace findings were resolved without altering originals.
