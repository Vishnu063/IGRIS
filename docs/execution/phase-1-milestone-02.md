IGRIS EXECUTION REPORT

Phase: 1
Milestone: 2
Title: Connect real Hermes inference to the existing controller and persistent chat memory

Status: PASS

Implemented:
- Reused the existing MissionController, Guardian policy, private SQLite Memory backend and verified Hermes source-run runtime. No replacement reasoning agent, new service deployment or upstream source modification.
- Added explicit ChatService/controller routing, typed bounded request/reply contracts, an opt-in terminal interface and owner-bound persistent conversations.
- Shared the original restricted container/bootstrap between the inference probe and chat. Added a global nonblocking execution lock and labeled-container check to prevent overlapping model workers.
- Stored completed exchanges with conversation/request/mission binding and real model provenance. Failed/blocked/cancelled turns are excluded from model history; mismatched/replayed completions fail closed.
- Added six-pair/16-KiB recent history, sensitive-input rejection, output redaction/control filtering, explicit forgetting and inherited private SQLite snapshot support.
- Recorded real CLI/restart/recall/isolation/stop evidence and a fresh regression of the original inference probe. Historical Milestone 1 evidence and all original 50 reports remain intact.

Files changed:
- README.md
- docs/execution/README.md
- docs/execution/phase-1-milestone-02.md
- docs/integrations/hermes-chat.md
- docs/validation/hermes-activation-status.json
- docs/validation/hermes-chat-live.json
- docs/validation/hermes-inference-regression-milestone-02.json
- integrations/hermes-inference/README.md
- scripts/hermes_inference_worker.py
- scripts/run_hermes_inference_probe.py
- scripts/hermes_chat_worker.py
- scripts/test_chat_live.py
- src/igris/adapters/hermes_chat.py
- src/igris/chat.py
- src/igris/conversations.py
- tests/test_chat.py
- Ignored runtime evidence/locks and disposable test databases were used locally; no database, model, credential, venv or container image is committed.

Commands executed:
$ git status --short
$ git branch --show-current
$ git log -2 --oneline
$ git remote -v
$ git ls-remote origin refs/heads/develop
$ env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock image inspect sha256:71ed6a3c8bc579133b3983e8e61599e7b1ecfba0a4985045451c6e8ec36fd855 --format '{{.Id}}'
$ python3 -m compileall -q src scripts tests
$ PYTHONPATH=src python3 -m igris.chat --help
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ git diff --check
$ git add (explicit milestone files)
$ git diff --cached --check
$ git commit (tested milestone implementation and evidence)
$ git push origin develop
- A manual help invocation without PYTHONPATH failed source-checkout import; the documented PYTHONPATH=src invocation succeeded. No package installation or code workaround was needed.
- An interrupted final-check tool call was resumed. Previously collected live evidence was verified against unchanged source hashes rather than inferred from a partial run.

Tests executed:
$ python3 -m unittest discover -s tests -p test_chat.py -v
$ python3 -m unittest discover -s tests -p test_hermes_probe_evidence.py -v
$ python3 -m unittest discover -s tests -q
$ python3 scripts/test_chat_live.py
$ python3 scripts/run_hermes_inference_probe.py
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ PYTHONPATH=src python3 -m igris.guardian.scan

Test results:
- Passed: complete local suite: 182 tests in 20.987 seconds; 15 new chat/security/protocol/interface tests pass. These use real disposable SQLite/filesystem/CLI and explicitly identified backend/protocol fixtures.
- Passed real end-to-end: separate CLI process/container returned NOTED.; the next process recalled the randomized MAPLEB524C2ED from persisted history without the codeword in its new prompt; a new conversation returned UNKNOWN. Each successful turn used one actual Hermes API call, the verified Qwen3.5-2B model hash and controller requested/planned/ready/running/verifying/succeeded transitions.
- Passed real end-to-end: owner mismatch denied on reopen, SQLite snapshot/reopen retained history, explicit forgetting removed the session, actual SIGINT exited 130, cancelled exchange remained incomplete and excluded, and no inference containers remained. Disposable acceptance state was removed.
- Passed regression: refactored original probe returned 31 for 18+13, 27 for random 15+12 and WINDOW for uppercase window; direct native control returned 31. Each worker checks real default-empty Guardian dispatch denial, authenticated inference, non-root execution, read-only source and absent external network.
- Passed: source-bound live evidence, compile/CI structure/delivery/whitespace checks and configured credential-pattern scanning. Existing vendor hashes and all 50 report formats remain valid.
- Failed unresolved: none in this milestone's tested scope. The corrected manual invocation above is not a passing inference test.
- Skipped: hosted Actions, production, Mac and later milestones.
- Mocked: unit backend failure/simulation fixtures and protocol transport interception; original prototype's labeled contract simulations remain simulations. No backend fixture was used by either live acceptance script.
- Not tested: speech/voice, live n8n/Ops Pilot/specialist execution, remote/multi-user authentication, browser UI, Mac hardware, long conversations/model competence, sustained concurrent load, hard host-crash recovery or comprehensive upstream vulnerability assessment.

Security review:
- The real Hermes dispatch boundary retains default-empty Guardian; native tools remain empty. Host storage permissions are trusted operator configuration and never transferred to model/history. There is no command parser, financial/client/deployment capability or approval granted by conversation text.
- Each turn uses a fresh offline non-root container, read-only selected mounts, no Docker socket or chat database mount, dropped capabilities, no-new-privileges, 2 CPUs, 3-GiB memory, bounded PIDs/tmpfs and timeout/cleanup. No host fallback, automatic pull/install or always-running process.
- Strict owner/session/request/mission correlation, reserved SQLite transactions, persisted logical ownership and history schemas prevent cross-session completion, overlapping turns and system/tool-role injection. Pending hard-crash state fails closed; it is never automatically replayed or expired.
- Prompt text travels through stdin, not process arguments. Recognized sensitive input is rejected before inference/storage; generated recognized secrets/control characters are filtered before storage/display. Failure reporting avoids worker output/private diagnostics. Storage/locks are private and model-local authentication is ephemeral.
- Self-review found no unresolved blocker in tested scope. Host operator/Docker/kernel trust, plaintext storage/backups, unknown-secret detection gaps, hallucination and malicious same-user code remain limitations, not solved security guarantees.
- No main merge, production deployment, Mac installation, paid service activation, external model account or client communication.

Git commit:
- Commit containing this record; exact SHA supplied after commit/push and remote develop verification. Parent is 1ecd0b3b0da6d9e40c3c2d17429972a5095002f5. Existing commits/user work preserved.

Known limitations:
- Manual terminal chat works in the prepared Linux x86_64 cloud runtime only. Native Mac M1 binaries/dependencies and hardware performance remain PENDING_EXTERNAL_VERIFICATION; this runtime refuses unsupported platforms.
- Real fresh-worker chat turns measured 53.1669, 59.3336 and 43.4640 seconds on two cloud CPUs. Startup/hash verification is included. This is unsuitable evidence for low-latency voice or Mac performance.
- Logical owner authorization inherits the trusted OS session. No web authentication or multi-tenant isolation is added. Model output/history cannot authorize tools, but arbitrary prompt-injection resistance or answer correctness is not guaranteed.
- Conversations/backups are private plaintext. Recent model context is bounded; older exchanges are not semantic/long-term retrieval. Mem0 is not integrated. No automatic retention purge or encrypted backup management is implemented.
- Normal stop is tested; SIGKILL/host failure can leave a pending request/container that requires operator review. No automatic recovery lease is provided. Completed controller mission state is in-memory; exchange IDs/provenance persist.
- Existing generic ZIP backup and dashboard are not wired to live chat state; the tested chat backup is the inherited SQLite snapshot API. Legacy Hermes planner remains unavailable; service adapters, specialist inference and speech remain unverified.
- No external credential/access blocker prevented Milestone 2. Existing runtime assets/image remain local prerequisites; clean-room installation, full optional Hermes stack and broader integrations are not certified.

Next step:
- Stop after verified Milestone 2. Continue only with the next authorized milestone; do not merge or deploy.

Approval required:
- No for this user-authorized implementation, tests, commit and push to develop. Production, main merge, spending and Mac installation remain unauthorized.
