# Hardware and budget constraints

Step 4 defines a planning envelope, not a measured compatibility claim.
All resource estimates below are UNVERIFIED until tested on the owner's Mac.
No Mac access, installation, paid activation, or production deployment occurred.

## Target and hard constraints

| Item | Target or rule | Evidence status |
| --- | --- | --- |
| Processor | Apple M1, ARM64 | User-specified; hardware not inspected |
| Unified memory | 8 GB shared by macOS, GPU and applications | User-specified; available memory unmeasured |
| Available storage | Approximately 50 GB | User estimate; free space unmeasured |
| Starting authorized spend | ₹0 | User constraint, not a free-service entitlement |
| Current execution | Existing GitHub repository and Codex cloud workspace | Verified in Steps 1–3; no new paid resources authorized |

Do not interpret all 8 GB as available for IGRIS. macOS, browser tabs and other
applications require headroom. Do not treat the remaining 50 GB as expendable.
No heavy local language models, GPU inference stack, always-running agent fleet,
or full business-tool suite is part of the baseline.

## Lightweight options, in preferred order

1. **Cloud-first development now:** use the already authorized repository and
   cloud workspace for documents, standard-library code and disposable tests.
   Availability of this session does not establish a free subscription, unlimited
   compute, free GitHub Actions minutes or authorization to purchase more.
2. **Minimal native runtime later:** after explicit Mac installation authorization,
   consider an ARM64 Python controller, independent Guardian/executor boundary,
   SQLite state and an on-demand authenticated dashboard. Start manually; stop
   workers after a mission. Security isolation must not be removed to save RAM.
3. **One optional local service at a time later:** evaluate n8n, Ops Pilot or a
   voice engine only after its numbered audit and actual resource measurement.
   A container runtime adds VM memory and image storage on macOS. Avoid Docker
   in the baseline; verify native support and licensing before choosing it.
4. **Existing remote service later:** an approved, already available endpoint may
   reduce local RAM use, but needs a verified API, security review and known cost.
   No cloud account, public endpoint, hosting plan or free tier is assumed.

Hermes and the 15 specialists are adapter/role capabilities, not 16 permanently
loaded local models. Reasoning requires a verified compatible engine; without a
known zero-cost option it remains disabled or explicitly simulated for tests.
VoiceStudio compatibility and language-engine requirements are deferred to Step
31. No voice engine is selected or declared to fit this hardware here.

## Estimated memory and CPU envelope — UNVERIFIED

These are engineering allowances for a small future standard-library application,
not upstream service minimums or cloud measurements. MiB uses 2^20 bytes; GB in
the hardware description is approximate. Peak memory depends on data and tasks.

| Component or activity | Proposed resident-memory allowance | CPU and scheduling intent | Verification |
| --- | --- | --- | --- |
| Controller and text interface | 50–150 MiB | Mostly idle; bounded synchronous requests | UNVERIFIED on Mac |
| Independent Guardian/executor | 30–100 MiB | Short authorization/validation operations | UNVERIFIED on Mac |
| SQLite, audit and memory working set | 20–100 MiB incremental | Small indexed records, bounded queries | UNVERIFIED on Mac |
| Dashboard server | 30–100 MiB incremental | Start on demand; browser memory is additional | UNVERIFIED on Mac |
| One lightweight task worker | 50–200 MiB | One active worker initially; explicit timeout | UNVERIFIED on Mac |
| Total illustrative core plus one worker | 180–650 MiB | Target at most one CPU-heavy task at once | UNVERIFIED; sum of allowances only |
| Build tools, browser, Docker VM, n8n, Ops Pilot, Hermes or voice | Not estimated before audits | May exceed the baseline substantially | Not measured; excluded from total |

Initial planning target: keep measured core peak below 1 GiB, leaving at least
3 GiB of the nominal 8 GB for macOS and other work; the remainder is contingency,
not a guaranteed allocation. Actual OS pressure and existing apps take precedence.
The 1 GiB cap is a proposed acceptance target, not an implemented resource limit.
Do not add excluded workloads to the 650 MiB figure and claim they fit. CPU limits,
worker limits and timeouts require later implementation; none are enforced yet.

## Storage envelope — UNVERIFIED

| Category | Planning allowance | Policy intent |
| --- | --- | --- |
| Source, virtual environment and small dependencies | 1 GB | Prefer standard library; audit any dependency before adding |
| State, approved memory and redacted logs | 1 GB | Bound retention; never silently delete user data |
| Disposable builds and caches | 2 GB | Clean only known disposable paths after scope validation |
| Verified local backup copies | 2 GB | Encrypt/restrict sensitive copies; rotate with explicit retention policy |
| Contingency | 4 GB | Reserved for variation; not approval for downloads |
| Total initial project allocation | 10 GB | Planning cap, not a measured footprint |
| Desired remaining free space from the estimated 50 GB | At least 40 GB | Recalculate against actual free space before any future installation |

A local backup is not protection against device failure. Remote backup storage,
if later requested, requires security and cost review; do not activate a service.
If free space is below 15 GB, pause new downloads/builds and report the constraint.
This is a proposed safety threshold, not an implemented monitor or macOS minimum.

## Zero-budget policy

- No API billing, paid inference, cloud instances, domains, subscriptions, paid
  workflow hosting, paid licenses or financial transactions are authorized.
- A free tier can require a card, expire or incur overages. Do not register,
  activate or rely on one without verified terms and explicit authorization.
- Model calls, network transfer, storage, workflow runs, CI minutes and background
  resources may cost money even when the software is open source.
- Unknown price means blocked for real use. Tests use local fixtures or clearly
  labeled mocks and must never be described as real service connectivity.
- Existing user-provided credentials do not authorize spending. Later Cost
  Guardian must track cost evidence and enforce the approved allowance. This
  document is not the implemented spending control.
- A later request to spend requires the exact service/action, amount/currency,
  billing period and scope. No such approval is requested or granted in Step 4.

## Future Mac validation checklist — not executed

Perform only after explicit authorization for Mac work; do not run installation
commands now. Record software versions, OS version, ARM64 compatibility and
native binary availability. Inspect actual memory and free storage first.

1. Measure baseline system memory pressure, swap and free space with ordinary
   applications open; record the method and units.
2. Start only the core and independent security boundary. Measure cold startup,
   idle RSS, peak RSS over repeated small missions, CPU time and log growth.
   Sum concurrent processes carefully; shared memory can cause double counting.
3. Add one lightweight worker and dashboard separately; measure the browser too.
   Reject the profile if it causes sustained memory pressure, material swap
   growth, UI degradation or unacceptable thermal load; reduce concurrency.
4. Evaluate each audited optional service independently. Record incremental and
   total process/VM memory and installed/cache storage before combining services.
   No evidence from the cloud Linux environment proves ARM64 macOS compatibility.
5. Check the proposed 1 GiB core peak, 10 GB project allocation and storage
   threshold against measurements. Revise estimates openly if they do not fit;
   never bypass Guardian isolation, approvals or redaction to reduce overhead.
6. Confirm services stop on request and do not auto-start or continuously record
   audio. Keep unsupported voice/model features disabled. Preserve measurements
   for the final hardware-verification report.

Step 4 can PASS for documenting constraints and explicit estimates. Mac
compatibility and these acceptance targets remain pending external verification.
