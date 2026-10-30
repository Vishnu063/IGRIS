# Incident diagnosis — Step 18

The deterministic diagnosis module separates source-reported observations from
possible causes. Each finding references a normalized export SHA-256 and exact
source field; its report preserves simulated/provided-export origin. This is not
an AI root-cause oracle or proof that imported evidence is genuine.

Scenarios include stopped/restarting containers, failed endpoints, Docker-reported
OOM termination, nonzero exits, historical restarts and filtered memory/disk/DNS/
dependency/timeout/authorization/image log signatures. An OOM flag corroborates a
runtime-reported termination, not a memory leak or its allocating component.
An exit code or signature does not prove the cause. A running container with a
failed endpoint stays unhealthy. A cumulative restart count does not prove an
active loop. Stale/incomplete sources do not become confirmed observations.

No commands, provider calls, recovery actions or repair recommendations execute
here. Tests exercise the above scenarios and evidence links without raw logs,
credentials or real infrastructure. Recommendations belong to Step 19.
