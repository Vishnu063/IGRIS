# Owner-selected real Hermes specialists

The original fifteen copied/adapted Agency Agents definitions and manifest are
reused. Task 6 removes assumed PM memory, workspace paths and fixed framework requirements from its adapted copy; the vendor original is unchanged and the manifest records the new reviewed hash. The legacy `SpecialistScheduler` remains a clearly
labelled simulator. `LiveSpecialists` is the optional real execution profile,
using the existing Hermes runtime and Guardian authority rather than a new agent
framework. List all choices before selecting one:

```sh
$ PYTHONPATH=src python3 -m igris.specialists --list
$ PYTHONPATH=src python3 -m igris.specialists --enable-runtime --role code_reviewer --context 'Review def append(x, items=[]): items.append(x); return items.'
```

A separate controlling terminal displays the role, exact task/context, full
reviewed definition hash, model identity and scope. Approval expires and is
consumed once. Reject, timeout, cancellation, changed arguments and restart do
not activate a role. There is one specialist slot and one global inference slot.
No worker is started merely by listing or recommending a role.

Each role receives a deterministic 1,800-character excerpt from its reviewed
upstream technical methodology; the complete definition is hash-verified first.
The excerpt length is included in the approved execution scope. This bounds
prompt overhead for the two-billion-parameter model without changing copied
source or loading every role. Task context is explicitly supplied and bounded;
there is no implicit access to conversation history or other project data.

Role selection grants no OS, network, browser or native Hermes tool rights.
Responses are advisory proposals, not evidence of executed development, mobile
builds, security certification, external research or incident recovery. Native
Hermes tools and its actual dispatch boundary remain disabled/default-deny.
Any future request to perform a recommended action must separately pass Guardian.
The worker has no approval DB, credentials, daemon socket or writable source.

Live acceptance executes fifteen distinct scoped tasks and retains generated
responses and role-specific checks. Automated owner decisions in the acceptance
script are trusted fixtures, never AI approvals. Text matching alone is not a
quality certification: the first attempt incorrectly reversed HTML for/id
attributes despite matching broad keywords. That attempt was rejected, the
check was tightened to inspect generated markup, and excessive role prompt
content was bounded. No hardcoded specialist responses are used.

These small-model proposals require human review. Same-user host/DB tampering,
model mistakes, hallucinations and untrusted prompt content remain limitations.
The infrastructure enforces permissions independently of response correctness.
No Mac performance, simultaneous fifteen-agent execution or production access
is implied.

An additional observed quality limitation: the backend response returned the
correct POST/201/validation contract but appended unsupported advice to omit
authentication, audit logs and monitoring. Those exclusions are not endorsed or
accepted as production design. The scoped contract checks do not certify the
whole response. The mobile response suggested a cloud database without cost
assessment; no account or paid integration is activated. Human review must reject
unjustified additions. Guardian remains independent of model recommendations.

The terminal entry point stores completed selected-role results in its private
`results.sqlite3`, outside all worker mounts, and correlates them with the
Guardian mission and action digest. Failed/cancelled authority remains in the
Guardian audit without raw task contents. Owner review of generated results is
required before acting on them; journal storage never grants authority.
The first PM answer also imported a FluxUI dependency from the copied methodology
although it was not in the task. That response was rejected. Explicit project
scope is necessary; copied examples must not become requirements. The correction
evaluation supplies an explicit standard-library-only API scope.


Reproduce the final scoped cases with the retained cloud runtime:

```sh
$ PYTHONPATH=src python3 scripts/test_specialists_acceptance_live.py
$ PYTHONPATH=src python3 scripts/test_hermes_cancel_live.py
```

The final accepted matrix is assembled from sequential real test batches. The
broader initial benchmark (`test_specialists_live.py`) deliberately retains the
original harder questions and can still fail; it is not relabelled as passing.
Rejected answers and their inputs are retained separately in validation data.
The focused voice control contract concerns advisory control-state design; it
does not verify an actual microphone or multilingual speech quality.
