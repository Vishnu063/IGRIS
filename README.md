# IGRIS — Personal AI Assistant

IGRIS is a cloud-first development prototype for software, automation, business
planning and DevOps work with a restricted independent execution broker.

**Current release acceptance: BLOCKED — 9 tasks PASS, 5 BLOCKED, 0 FAIL.** Real cloud chat, Guardian tools, approvals and selected integrations work within their documented scopes. n8n is quarantined; native Mac and human voice acceptance remain unavailable. See [current final review](docs/delivery/completion-final-report.md) and [live versus unverified matrix](docs/validation/completion-integration-matrix.md).

## Actual implementation state

Tested local libraries provide mission control, Guardian permissions and exact
approvals, project/Git utilities, an authenticated local dashboard, business
records, private SQLite memory/earnings and backup restoration. The 15 specialist
definitions are copied and adapted from Agency Agents. A curated Hermes backend
source subset is copied and patched as the intended reasoning foundation.

**Manual local Hermes inference is now verified** in an isolated, reasoning-only
cloud profile: [Phase 1 milestone](docs/execution/phase-1-milestone-01.md),
[actual generated responses](docs/validation/hermes-inference-live.json),
[explicit cloud setup/probe](integrations/hermes-inference/README.md).
**Manual IGRIS chat now connects the existing controller to real Hermes and
private persistent conversation memory**: [Milestone 2](docs/execution/phase-1-milestone-02.md),
[chat instructions and security limits](docs/integrations/hermes-chat.md),
[real restart/recall/stop evidence](docs/validation/hermes-chat-live.json).
Start explicitly with the prepared cloud runtime:

```sh
$ PYTHONPATH=src python3 -m igris.chat --remember
$ PYTHONPATH=src python3 -m igris.chat --remember --resume
```

Native tools remain disabled. The legacy planner adapter is still unavailable;
there is no always-running service. **Task 14 quarantines the previously verified n8n runtime after critical/high dependency findings; n8n execution is currently blocked.** Task 4 retains its historical live evidence; Task 5 verifies read-only Ops Pilot monitoring of a disposable Docker application. Speech synthesis is real in cloud tests, while microphone, human speech quality and Mac playback remain blocked. Task 6 adds opt-in real role-conditioned advisory specialist responses; the legacy scheduler remains simulated. Mission Control uses real backend data when explicitly enabled; no existing production service health is implied. Production deployment,
paid activation and external client submission remain disabled.

**Guardian-controlled tools are now verified** through real Hermes JSON
proposals: [Milestone 3 report](docs/execution/phase-1-milestone-03.md),
[execution and approval boundaries](docs/security/guardian-controlled-tools.md),
[actual acceptance evidence](docs/validation/guardian-tools-live.json).
Only current time, explicit workspace listing and allowlisted text-file reads
are available. Default chat executes no tools; choose a private test profile:

```sh
$ python3 scripts/create_guardian_test_workspace.py
$ PYTHONPATH=src python3 -m igris.chat --remember --tools-config runtime/guardian-demo/tools.json
```

The helper refuses to overwrite an existing demo. If this workspace already has
the prepared profile, use its existing file. No shell, writes, Git, browser or
external network tool is exposed. Approval-required chat actions require the opt-in controlling-terminal channel described below. This is development verification, with
same-user/database-tampering and hardware limits documented in the report.

The current completion and blocked work are tracked in [completion progress](docs/execution/completion-progress.md).
Task 1 adds opt-in [controlling-terminal approvals](docs/security/interactive-approvals.md):
the exact action is reviewed separately from chat, expires, and executes once
through Guardian. Enable with `--interactive-approvals` and a private profile
that explicitly marks the tool approval-required. Without this channel, such
operations remain denied. No additional tool capability is granted by the flag.

The authorized repository is `Vishnu063/IGRIS`; it is retained rather than
creating or renaming a repository to the suggested `igris-ai-assistant`.
Development takes place on `develop`. This cloud-first project must not install
software on the owner's Mac, activate paid services, or deploy to production.
The initial spending allowance is ₹0.

Current delivery: [completion release review](docs/delivery/completion-final-report.md), [current startup](docs/delivery/setup.md). Historical Step 50 delivery: [original consolidated report](docs/delivery/final-report.md),
[cloud setup](docs/delivery/setup.md), [exact capability status](docs/delivery/status.json)
and [later Mac plan](docs/delivery/mac-plan.md). All 50 numbered records describe
scoped local work; live activation and hardware checks remain pending.

## Structure

- `src/igris/`: standard-library controller/chat/storage, guarded runtime transport and disabled service adapters.
- `tests/`: local unit/security/integration tests with explicit simulations.
- `vendor/`, `integrations/agency-agents/`: copied source and adapted definitions.
- `workflows/`: inactive n8n definition and contract validation assets.
- `docs/architecture/`: design, local implementations and unresolved boundaries.
- `docs/governance/`: development and branch protection recommendations.
- `docs/execution/`: numbered execution evidence and status.

## Local verification

Run from the repository root:

```sh
$ python3 -m unittest discover -s tests -v
$ python3 scripts/check_ci.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ git diff --check
```

These checks exercise local implementation and explicit fixtures. They do not
establish live-service connectivity or Mac compatibility. Loopback tests need
socket permission. No package installation is needed for `src`/tests; Node is
used to verify workflow logic. See [configuration guidance](docs/configuration/README.md),
[integration matrix](docs/validation/integration-matrix.md),
[security results](docs/security/validation.md),
[cloud measurements](docs/validation/performance.md) and
[source notices](THIRD_PARTY_NOTICES.md). Hosted CI is manual-only and was not run.

## Architecture

See [the proposed architecture](docs/architecture/overview.md). This design is
not evidence that its components or security controls are implemented.

Hardware targets, unverified resource estimates and the ₹0 policy are documented
in [hardware and budget constraints](docs/architecture/hardware-budget.md).

[Guardian security design](docs/security/guardian-design.md) records the threat
model and required deployment isolation. Design alone does not enforce security.

[Restricted execution](docs/security/execution.md) documents the narrow tested
broker interface and its deployment limitations.

[Secrets protection](docs/security/secrets.md) describes tested redaction and the
local source/index credential scanner, including detection limits.

[Approval controls](docs/security/approvals.md) bind a reviewed exact action to a
single-use expiring approval. Real scoped mutations create new text artifacts;
recovery mutations are confined to simulator state. Production, spending and
external communications remain unavailable.

The [core controller](docs/architecture/controller.md) remains a synchronous
in-memory library. Its explicit [chat route](docs/integrations/hermes-chat.md)
uses real local inference and durable completed exchanges; no autonomous service is active.

[Simulated orchestration](docs/integrations/orchestration.md) connects tested
controller and Guardian code to explicit Hermes/Ops Pilot mocks and a local n8n
contract fixture. Real service connections remain unverified and disabled.

Ops Pilot work through Step 20 includes a [read-only source audit](docs/integrations/ops-pilot-audit.md),
[monitoring export mapping](docs/integrations/ops-monitoring.md), evidence-linked
diagnosis and [proposal-only repair guidance](docs/integrations/repair-recommendations.md).
[Approved recovery](docs/integrations/approved-recovery.md) is tested only with an
explicit simulator; real Ops Pilot restarts remain blocked.

Development through Step 25 includes [project scaffolding](docs/development/projects.md),
a [reviewed sample application](docs/development/workflows.md), [local Git workflows](docs/development/git.md),
[manual-only CI preparation](docs/development/ci.md) and [production approval controls](docs/development/deployment.md).
These are trusted development utilities; no real production deployment is enabled.

The [15 specialist contracts](docs/specialists/README.md) have tested role boundaries
and [approval-gated simulated scheduling](docs/specialists/scheduling.md). They
are not connected live models; no separate Agent Builder is added.

The user-authorized [reuse correction](docs/revisions/reuse-correction.md) copies
and adapts Agency Agents definitions and Hermes backend source in this repo.
The manual source-run reasoning profile is now verified; general product/runtime
activation remains unavailable. These source copies replace the earlier
reference-only strategy. MIT notices and provenance manifests are retained.

### Optional Handy file input

See [Handy integration](docs/integrations/handy.md) for explicit offline file transcription and text fallback. Physical microphone and Mac acceptance are not verified. No voice service starts automatically.

Optional English/Hindi/Marathi WAV generation and explicit language selection are described in [multilingual voice status](docs/integrations/multilingual-voice.md). Real human recognition, physical playback and M1 validation remain blocked; automatic spoken-language detection is not claimed.

[Real n8n local calculation](docs/integrations/n8n-runtime.md) now requires Guardian owner approval and a pinned offline runtime. It exposes no public webhook and does not enable general workflows or change the original three chat tools.

Task 5: [real read-only Ops Pilot runtime](docs/integrations/ops-runtime.md),
[actual healthy/stopped Docker evidence](docs/validation/ops-runtime-live.json).
No existing deployment is connected and remediation stays disabled.

Task 6: [owner-approved real specialist reasoning](docs/specialists/live.md),
[fifteen scoped acceptance results](docs/validation/specialists-live.json),
[retained initial attempts](docs/validation/specialists-attempts.json).
Small-model advice requires human review; role selection grants no tool rights.

Task 7: [interactive local Mission Control](docs/integrations/mission-control.md) adds
authenticated chat/history, exact Guardian approval controls, selected specialists,
bounded n8n/Ops operations and emergency stop. See [real browser acceptance](docs/validation/mission-control-live.json).
Voice is explicitly unavailable in the dashboard; no microphone starts automatically.

Task 8: [optional scoped Mem0 memory](docs/integrations/mem0.md) adds approved
facts, local semantic retrieval, correction/deletion and bounded real-Hermes
context. SQLite remains authoritative. Enable explicitly with `--enable-mem0`;
no automatic fact extraction or paid model is activated. Mission Control and
text chat now share the `runtime/chat` default state directory.

Optional approved owned-site browser inspection: [Playwright boundary and manual startup](docs/integrations/playwright.md). General web browsing remains disabled.

Optional owner-approved document conversion and real Hermes summaries: [MarkItDown setup and restrictions](docs/integrations/markitdown.md).

Optional manually started warm chat: [startup, stop controls and measured tradeoffs](docs/integrations/warm-inference.md). One-shot remains the default.

Mac M1 preparation is **BLOCKED pending authorized hardware and ARM64 security validation**. See the [safe preparation package and exact gates](docs/delivery/mac-package.md); no Mac installation was performed.
