> Reuse strategy updated by explicit user instruction; see docs/revisions/reuse-correction.md. Earlier decisions below are historical.

# Agency Agents compatibility and security assessment — Step 26

Reviewed 30 October 2026 (Asia/Kolkata), upstream revision
b37b5bb33b78f2c1d6567d98e25ca818e3259219 of
[Agency Agents](https://github.com/msitarzewski/agency-agents/tree/b37b5bb33b78f2c1d6567d98e25ca818e3259219).
agency-evidence.json records the selected paths and exact Git blob identities.
Read-only review covered 15 relevant definitions plus README, LICENSE, SECURITY
and Codex integration documentation. No scripts, upstream code or prompt bodies
were installed, executed or imported as instructions. This is a selected-source
self-review, not a security certification of every upstream file or installer.

## Actual integration and licensing

The upstream security policy describes Markdown prompts plus executable installer/
conversion scripts. The Codex integration copies full Markdown bodies unchanged
into developer_instructions in files under the user's .codex/agents directory.
That would grant untrusted third-party prose instruction priority and modify
configuration outside this repository; it is not authorized or necessary here.
No integration script was run, on the Mac or in the cloud workspace.

Upstream LICENSE is MIT (2025 AgentLand Contributors): preserve its notice when
redistributing substantial source. IGRIS will keep evidence links and author its
own minimal role contracts; no upstream bodies/code are redistributed. This is
not a review of licenses for every recommended tool, framework or model.

## Relevant mappings and changes required

| IGRIS role | Reviewed upstream definition | Boundary for an IGRIS-owned contract |
| --- | --- | --- |
| Frontend | Frontend Developer | Supplied-source/UI advice; no assumed React install or measured performance |
| Backend | Backend Architect | API/data design proposals; no automatic microservices or deployment |
| Mobile | Mobile App Builder | Platform plan only; no SDK/Mac install or in-app purchases |
| AI | AI Engineer | Model/evaluation plan; no downloads, inference billing or performance claims |
| DevOps | DevOps Automator | Pipeline/runbook proposals; no provisioning, automatic rollback or production actions |
| Security/privacy | Application Security Engineer | Evidence-based threat/privacy review; no assertion of complete audit |
| Testing | Test Automation Engineer | Targeted test plan; no browser install, hosted CI dispatch or automatic quarantine |
| Code review | Code Reviewer | Findings tied to supplied evidence; no merge or self-approval |
| UI/UX | UX Architect | Accessibility/layout proposals; no mandatory theme/framework or project-spec paths |
| Database | Database Reliability Engineer | Schema/recovery plan; no migrations, failover, deletion or untested restore claims |
| Research | Research Synthesist | Source evaluation; no invented citations or automatic web access |
| Project management | Senior Project Manager | Bounded task planning; no invented persistent memory or client promises |
| Incident response | Incident Response Commander | Evidence and escalation plan; emergencies do not bypass approvals |
| Voice AI | Voice AI Integration Engineer | Engine/consent test plan; no continuous microphone, ASR purchase or model install |
| Minimal-change | Minimal Change Engineer | Scoped patch plan; no arbitrary file-count thresholds or unreviewed edits |

## Findings and decision

- Persona experience/memory and sample metrics are prose, not verified capability.
  Never present those numbers or supposed past work as IGRIS evidence.
- DevOps examples contain production rollout and cloud provisioning patterns;
  incident guidance grants emergency authority. Neither authorizes IGRIS actions.
- Security guidance prescribing only external secret managers conflicts with the
  approved lightweight staged approach; do not activate a paid vault to follow it.
- PM/UX definitions assume workspace paths/stacks and additional requirements.
  Voice/mobile definitions include heavy dependencies and platform operations.
- Examples inside Markdown may be executable if copied into tools. Keep them as
  untrusted reference data; no parser may convert prose into tool authority.
- Prompts do not enforce permissions, cost, approvals, credential boundaries,
  process isolation, scheduling limits or truthful output by themselves.

Decision: use reviewed concepts as reference, with original minimal inert
metadata, strict task/output contracts and no permissions granted by role choice.
Steps 27–29 register the 15 capabilities in groups. Contract fixtures are explicitly
simulated; no real LLM specialists are connected. Step 30 must gate activation
and bound scheduling at the independent Guardian boundary. No separate Agent
Builder, external specialist service, installer or always-running agent fleet.
Real specialist competence, model integration and M1 runtime use remain unverified.
