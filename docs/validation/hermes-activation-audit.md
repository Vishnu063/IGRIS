# Activation audit — Phase 1, Milestone 1

Started 2026-10-31; continued 2026-11-01. Baseline `develop` commit:
`01da63e67142fb062b1e44c79c25d8f9245aae71`, matching GitHub at audit start.
No user changes were present. All 50 numbered execution reports, consolidated
delivery, reuse correction, integration/security records and the historical
Step 48 blocker were read. Document hashes are in activation-audit-sources.json.
Historical scope-limited PASS records do not prove live integrations.

## Actual components inspected

| Component / source | Actual baseline behavior | Reuse and remaining gap |
|---|---|---|
| controller.py; test_controller / test_orchestration | Real synchronous in-memory mission state machine; named trusted handlers | Reuse; no conversational UI, durable task queue or full cancellation |
| guardian/policy.py, executor.py, broker.py, approvals.py, secrets.py | Real restricted child process, argument schemas, FD-based file access, default-deny permissions, exact expiring single-use SQLite approval, redaction | Reuse; this process boundary alone does not isolate a complete Hermes process or protect against hostile same-user code |
| adapters/hermes.py; reused_agents.py; test_hermes / test_reused_agents | Planner mock; real selector/activation raises unavailable. Copied backend hashes and actual no-tool branch tested | Reuse copied AIAgent source; prior tests do not execute full inference |
| vendor/hermes-agent/run_agent.py, agent_init.py, hermes_bootstrap.py, pm/environments.py, venv_sync.py, safe_worker_policy.py, tools/registry.py | Actual upstream runtime interfaces exist; imports can prepare environments, register tools and load profile configuration | Explicit independent venv, disabled lazy installs, pre-bound upstream safe-worker policy and container isolation required before execution |
| adapters/n8n.py; test_n8n / workflow JSON | Real authenticated local HTTP contract client, bounded retries and strict schema; fake workflow server and inactive template | Reuse contract; no real installed/imported n8n workflow verified |
| adapters/ops_pilot.py, ops_monitoring.py, recovery.py | Source-shaped export mapping, typed mock/unavailable transport, simulated recovery; live mutation refuses | Reuse audit/mapping; actual authenticated read-only target access not configured |
| specialists/registry.py, scheduling.py; Agency manifests | 15 copied/adapted methodologies; exact definition hashes and approved fixture scheduling | Reuse; no live specialist inference or user selection UI |
| memory.py; tests/test_memory.py | Real private SQLite knowledge, owner checks, approved writes, fact/assumption distinction, correction/deletion/backup | Reuse; not persistent conversation memory, not a permission source, no Mem0 |
| dashboard.py; test_dashboard.py | Real authenticated read-only loopback HTML/JSON, role views, escaped supplied snapshots | Reuse; no chat input, approval decision endpoint or automatic real status collector |
| voice/push_to_talk.py, languages.py, personality.py | Local permission/start/stop/deadline logic, script hints and guarded randomized greeting selection | Reuse; microphone/ASR/TTS absent; Hindi/Marathi script ambiguity deliberately unresolved |
| business, costs, earnings, backup and development modules | Real local planning/SQLite/backup/disposable project utilities with synthetic scenarios | Reuse; no real clients, earnings, billing, production delivery or deployment |

Baseline execution: **166 tests passed in 22.323s** during this milestone.
Local Git/HTTP/SQLite/broker tests are real; upstream/provider/model/client/audio
fixtures remain simulations. No model credentials, local engine or model were
configured at the start. No Mem0, MarkItDown, Playwright or Pydantic AI integration
exists; these belong to later milestones rather than new duplicate controllers.

## Confirmed problems and bounded resolution

1. The initial raw pip dependency check rejected browser-harness 0.1.13's Pillow
   12.3.0 requirement against Hermes' Pillow 13.0.0 pin. Further source review
   found upstream's explicit tool.uv Pillow override. Repeating resolution with
   all upstream overrides and its three-day quarantine **succeeded**. The initial
   check omitted that project policy; it does not establish a full-stack blocker.
   The separate inference-only source-run profile deliberately omits unused
   browser/web/document/graphics engines and retains upstream pins for used
   packages. Its complete 53-distribution resolution is hash-locked and installed
   in runtime/hermes-venv. No Pillow downgrade or forced inconsistent install was
   used. Full optional-stack installation/execution is not claimed by this lean
   profile; the full supported lock was resolved as an audit control only.
2. Installed uv did not list Python 3.14.9. Downloaded the exact first-party
   standalone archive identified by Hermes' own pm/lock.json and verified its
   SHA-256 before extraction. It resides only under ignored runtime/.
3. User-namespace/bubblewrap attempts were unavailable in this managed sandbox.
   No unrestricted inference fallback was used. The managed Docker daemon is
   available through the supported command permission path; no daemon restart or
   root helper was needed. A file-specific Docker socket grant triggered a tool
   sandbox setup error; the supported network permission path worked.
4. The native CPU server initially failed because the minimal Ubuntu image lacked
   libgomp.so.1. A dedicated image adds **only libgomp1**, 382 kB installed, from
   signed Ubuntu repositories. Runtime remains offline/non-root/read-only; the
   CA is mounted as a build secret, not copied into image layers. Package version
   and immutable image ID are recorded in integrations/hermes-inference/profile.json.

Full optional-stack runtime remains untested, not proven broken by item 1. Later
browser work must preserve the first-party dependency policy and test actual APIs.
Installed packages/models are development runtime artifacts, never committed.

The next live probe exposed an additional compatibility constraint: Hermes
requires at least 64,000 context tokens. The first server's 8,192-token window
was correctly rejected; that model's native 32K window is also insufficient.
The next candidate, native-262K Qwen3.5 0.8B, could run but failed multiple simple
arithmetic checks. Its two passing examples were not treated as broad readiness.
The final accepted candidate is Qwen3.5 2B, original revision
15852e8c16360a2fea060d615a32b45270f8a8fc, quantized by Unsloth at revision
f6d5376be1edb4d416d56da11e5397a961aca8ae. Its published native context is 262,144;
the actual server is configured at 65,536. Both original and quantization metadata
declare Apache-2.0. The unavailable official 0.8B GGUF repository was not accessed
or bypassed. No context guard or model capability was falsified to make tests pass.

## Current execution design

The explicit one-shot launcher verifies Python/engine/model archives and every
copied Hermes source hash. A fresh non-root container has no external network,
read-only mounts, no Docker socket or credentials, dropped capabilities,
no-new-privileges, 2 CPUs, 3 GiB memory, 128 PIDs and bounded writable tmpfs.
Nothing starts on import or boot. The launcher refuses absent Docker/assets/image
instead of falling back to an unrestricted host process.

Inside, a real llama.cpp CPU server loads pinned GGUF weights on private
container loopback. The accepted model is Apache-2.0 Qwen3.5 2B, quantized by
Unsloth (1,280,835,840 bytes), native context 262,144, served context 65,536.
No context check was disabled or false limit advertised. Its private
ephemeral credential is not put in command arguments, source, prompts or evidence.
The original copied AIAgent performs actual inference through run_conversation;
no SDK, model response or framework stubs are used. An explicitly empty toolset,
safe-worker configuration and default-empty IGRIS Guardian at the actual dispatch
method deny all tool execution. Real allowed tools are not introduced here.

The complete IGRIS adapter remains unavailable; chat, conversation persistence,
n8n, Ops Pilot, specialists and voice have not advanced to live operation in this
milestone. A tiny CPU model can demonstrate inference, not professional coding,
reliable multilingual speech, advanced reasoning or autonomous task competence.
The model/engine are public downloads, not paid APIs. Mac M1 remains untested.

The final live probe passed: original regression 18+13 → 31, random 12+12 → 24,
and uppercase window → WINDOW, with one actual Hermes API call per answer and an
independent native-engine control answer 31. Authentication, source read-only,
absent external route, non-root, default-empty Guardian dispatch and cleanup
checks passed. Per-answer observed times were 22.772s, 13.8096s and 13.4718s on
two cloud CPUs; this is not low-latency voice or Mac performance validation.
No inference container remained running. Earlier failed candidates are retained
in the attempt history; their verified unused model cache files were removed.

Also fixed a source-delivery omission: Dockerfiles are now included by the bundle
builder. Added a regression ensuring failed preflight invalidates older PASS
evidence, with atomic private outcome files and source/model identity binding.

See the milestone execution record and checked live evidence. Residual limits include Docker/kernel trust, same-user Docker operator
authority, unencrypted development state, regex redaction limits and incomplete
upstream dependency/security audit. No production security certification claimed.
