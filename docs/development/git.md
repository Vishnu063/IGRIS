# Git workflows — Step 23

Trusted operator utilities support new isolated repository initialization, local
branches, explicit path staging with review/credential checks, commits, PR draft
metadata, real conflict detection and history-preserving revert of an exact
expected HEAD. No remote submission, force push, branch deletion, reset or
arbitrary shell API exists. A conflict is left for owner review, not auto-resolved.

GIT permission uses the existing git.status capability category; these utilities
are not broker-exposed tools and must never be handed to untrusted agents. Only
new trusted development repos are tested; do not run them on untrusted .git
configuration or content. Git hooks/fsmonitor/signing are disabled and inherited
Git configuration is scrubbed for these local operations. Scanning can leave a
rejected staged index intact for inspection; it does not silently discard work.
PR drafts are data only. Revert can conflict and requires owner resolution.
