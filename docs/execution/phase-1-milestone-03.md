IGRIS EXECUTION REPORT

Phase: 1
Milestone: 3 — Real Guardian Security and Controlled Tool Execution

Status: PASS

Implemented:
- Audited the original 50 records, both activation milestones, architecture and actual controller/Hermes/runtime/memory/Guardian/approval/specialist/n8n paths before implementation. Recorded baseline hashes and a short audit in docs/security/guardian-tools-audit.md.
- Reused the existing Guardian Policy, executor, independent broker and ApprovalStore. Added no replacement agent, second Guardian service, paid dependency or upstream source change.
- Implemented explicit tool-mode flow: local owner request -> existing controller -> actual offline Hermes inference -> untrusted JSON -> existing broker policy/scope/approval checks -> one restricted handler -> protected audit -> verified IGRIS result and existing memory.
- Kept native Hermes tools empty and their actual dispatch denied. The planner emits a single JSON proposal; no host heuristic rewrites a wrong request into a successful one. Bounded relative filename hints improve grounding without granting authority.
- Added only get_current_time, list_workspace_files and read_workspace_file. READ permission AND an explicit private tools-only profile are required. Default chat remains tool-free. Tools-only broker startup cannot dispatch legacy mutation/terminal/fixture/Git/provider handlers.
- Added exact operation/argument schemas, per-directory/file allowlists, private isolated workspace checks, bounded no-follow descriptor reads, sensitive path/output filtering, safe listing and 2048-byte file limit.
- Reused single-use approvals, adding scope and intended request/mission binding. Chat cannot issue, decide or submit approvals; approval-required operations stay blocked. Real broker tests use clearly synthetic trusted owner decisions.
- Added minimal persistent tool events to existing ApprovalStore. Denials/malformed/unknown requests are audited without raw arguments or bodies. Required audit failure fails closed. Added interruption cleanup and Linux no-new-privileges/seccomp restrictions for network, asynchronous I/O and process/executable creation in read-only broker mode.
- Added an explicit no-overwrite cloud demonstration helper, real acceptance harness, source-bound evidence, performance measurements and current capability status. No model stays running.

Architecture before and after:
- Before: real controller chat -> isolated Hermes -> sanitized text -> persistent conversations. Native tool dispatch denied; the existing Guardian broker was reachable by trusted development/fixture code, not real reasoning output.
- After: the optional chat tool mode forwards real proposal bytes to that SAME broker. Startup identity/policy/scope/store/correlation are trusted host inputs, never model fields. The model container never mounts the workspace or state databases. Results are rendered directly after execution/audit rather than sending them through another inference call that might invent success.
- Specialists remain simulated-only and approval-gated through their existing broker fixture. n8n remains an inactive/local contract integration. Neither receives a live bypass or a new privileged endpoint. Trusted project/Git utilities remain unreachable from model proposals.

Files changed:
- README.md; docs/execution/README.md; this report.
- src/igris/adapters/hermes_chat.py; src/igris/chat.py.
- src/igris/guardian/policy.py; approvals.py; broker.py; executor.py.
- src/igris/guardian/readonly.py; kernel.py; tools.py.
- scripts/hermes_tool_worker.py; create_guardian_test_workspace.py; test_guardian_tools_live.py.
- tests/test_guardian_tools.py.
- docs/architecture/controller.md; docs/integrations/hermes-chat.md; integrations/hermes-inference/README.md.
- docs/security/guardian-tools-audit.md; guardian-controlled-tools.md; guardian-design.md; execution.md; approvals.md.
- docs/validation/guardian-tools-audit-sources.json; guardian-tools-attempts.json; guardian-tools-live.json; guardian-tools-performance.json; guardian-container-observation.json; guardian-demo-cli-live.json; hermes-activation-status.json; integration-matrix.md.
- Ignored runtime files contain local assets/locks, prepared synthetic demo/profile/state and intermediate evidence. No model, database, credential, private configuration or venv is committed. Original reports, upstream source and prior commits remain intact.

Tool registry and permissions:
- get_current_time: exact empty arguments; READ plus operation allowlist; actual UTC from the OS, no external network.
- list_workspace_files: exact string path; READ plus approved directory and explicit file allowlists; direct safe entries only, no recursive discovery of unapproved names.
- read_workspace_file: exact string path; READ plus explicitly allowed ordinary single-link UTF-8 file; 2048-byte cap, no traversal/absolute/hidden/sensitive/symlink/hardlink/FIFO/device access.
- Approval checks additionally bind complete arguments, actor, canonical workspace, environment, policy version, canonical scope digest and intended request/mission IDs. Missing/pending/denied/expired/forged/mismatched/replayed or old unbound approvals cannot authorize execution. A permission is not an approval, and approval cannot enable an unregistered handler.

Commands executed:
$ pwd
$ git status --short
$ git branch --show-current
$ git log -3 --oneline
$ git ls-remote origin refs/heads/develop
$ python3 (baseline source/document hashes, real selective Docker inspection and evidence verification)
$ python3 -m compileall -q src scripts tests
$ python3 scripts/create_guardian_test_workspace.py
$ PYTHONPATH=src python3 -m igris.chat --state-dir runtime/guardian-demo/state --list
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ git diff --check
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ git add (explicit milestone files)
$ git diff --cached --check
$ git commit (verified milestone implementation and evidence)
$ git push origin develop
- Model/chat prompts for acceptance and the real CLI example were supplied through subprocess stdin, never command arguments. No model/API credential was requested or printed.

Tests:
- Commands:
$ python3 -m unittest discover -s tests -p test_guardian_tools.py -v
$ python3 -m unittest discover -s tests -p 'test_guardian*.py' -q
$ python3 -m unittest discover -s tests -p test_approvals.py -q
$ python3 -m unittest discover -s tests -p test_chat.py -q
$ python3 -m unittest discover -s tests -q
$ python3 scripts/test_guardian_tools_live.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
- Passed: final complete suite 196 tests in 26.156 seconds, including 14 new actual broker/kernel/filesystem/SQLite security tests. Existing controller/chat/memory/approval/fixture/workflow tests remain passing. CI structure/delivery/compile/whitespace and configured credential-pattern checks pass.
- Passed real Hermes/controller: current-time proposal executes and falls within the measured real clock window; listing returns only injection.md and note.txt; approved Markdown read returns actual synthetic document contents; all native tools remain disabled.
- Passed real denials: outside-file and shell prompts produce unsupported JSON and Guardian denies the unregistered operation. Separate real broker tests exercise actual absolute/traversal/unlisted paths, symlink/hardlink escapes, forbidden directories and legacy operations; none returns outside file contents or creates a marker.
- Passed retrieved injection: real Hermes receives malicious instructions in completed conversation history and proposes another read of the same allowed document. Guardian checks it again; the document grants no permissions and no outside content/action occurs. This does not establish general model prompt-injection immunity.
- Passed approvals: real broker/SQLite enforce missing/forged/modified arguments/intent/replay rejection and one synthetic approved execution. Real model-generated time proposals claiming self-approval and restored conversation authority remain denied. Focused tests also cover valid-but-changed read arguments, actor/scope changes, expired/denied and old unbound records.
- Passed failures/cleanup: malformed arguments denied, an allowed missing file reports actual execution failure, a shortened real process deadline kills/reaps the broker and audits timeout, and a subsequent actual read succeeds. An injected KeyboardInterrupt reaps a real child and records interruption. Existing real model stop behavior is unchanged; no inference containers remain after acceptance.
- Passed persistence: three separate CLI processes remember and recall randomized CEDAR4F192C56, then deny a new approval-required time request in that same conversation. Stored text restores context, not authorization.
- Passed actual CLI demonstration: the documented prepared profile and terminal entry point read the actual note.txt through real inference and Guardian. Source-bound result is guardian-demo-cli-live.json. The helper/list smoke test starts no model.
- Passed audit: 25 acceptance events with correlation/digest/decision/timing metadata; assertions exclude raw command arguments, file names and document bodies. Known sensitive output is redacted in focused tests. Required audit failure prevents successful execution. Actual container inspection confirms no privilege/network/writable source/state/socket exposure.
- Failed: two preliminary real Markdown routing attempts. First produced unsupported; the first prompt revision then invented approved/file_injection.md. Guardian denied both. Added bounded filename hints and explicit exact-name guidance; focused actual read passed, then the complete live matrix passed. Final review added explicit io_uring syscall denial; reran all 196 tests and the entire real acceptance matrix successfully. Failure evidence is retained; no allowlist was expanded to rescue a hallucinated path.
- Mocked: original suites contain labeled fixtures/process doubles. New timeout tests shorten only the deadline; interruption tests inject only the exception. Real processes, kernel checks, files, approvals and live model responses are not substituted. Approval decisions are synthetic trusted-owner test decisions, not a verified human approval UI.
- Not tested: Mac M1, voice, live n8n/Ops Pilot/specialist models, hostile same-user/host compromise, public/multi-user UI, sustained load, exhaustive model reliability, hard host-crash recovery or full dependency vulnerability review. Hosted Actions were not dispatched.

Security review:
- Model runs offline/non-root with read-only source/model mounts, no workspace/chat/audit/approval database or Docker socket, no capabilities, no-new-privileges, 2 CPUs, 3-GiB memory and bounded PIDs/tmpfs/time. Pinned runtime/source verification and default native dispatch denial remain.
- Read-only mode uses the EXISTING isolated/no-site broker, scrubbed environment, 3-second wall timeout, 2-second CPU, 256-MiB address space, 64 descriptors, bounded output/file size and disabled core dumps. Linux syscall filtering denies networking, io_uring and new processes/executables; failure to install it denies execution. The kernel negative test uses actual syscalls, not patched sockets/processes.
- Request validation, policy, scope, exact approval consumption, required pre-execution audit and fixed handler are inside the broker boundary. User/model/history/workflow strings cannot create issuer authority, choose policy or reach legacy capabilities. No generic shell/code/network/browser or modifying tool is exposed.
- Minimal logs contain no prompts, raw arguments, contents or arbitrary exception messages. Raw synthetic proposals appear only in the reviewed acceptance evidence. Approval IDs/authority are never obtained from model JSON. Memory cannot revive permissions or old approvals.
- This is self-review and bounded development verification, not an independently certified full sandbox. Same-user malicious code, host Docker/kernel compromise and local database/clock tampering remain trust limitations. Local SQLite audit is private, plaintext and mutable by its OS owner.
- No main merge/force push, production deployment, Mac installation, spending, new paid/model account, external client contact or new heavyweight installation.

Performance:
- Final live matrix: 8 measured model tool proposals, 28.311–53.194 seconds for actual Hermes generation; 42.012–68.265 seconds including model/container/integrity startup.
- Seven directly timed model-tool turns took 42.100–68.354 seconds end-to-end. The previous milestone's 43–59-second samples are historical context, not a controlled before/after benchmark.
- Four authorized model-driven tool turns: 0.115–0.221 ms for parse/policy/scope/approval before audit; 0.021–0.168 ms for handler execution. All eight broker wall observations were 69.581–102.283 ms, including startup, limits/profile validation and audit. Raw samples and definitions are retained in guardian-tools-performance.json.
- Measured process high-water marks: Hermes 187312–188812 KiB; model 2744744–2765368 KiB; broker 16768–26448 KiB. These are Linux per-process peak RSS, not summed physical usage, cgroup peak or Mac measurements.
- Implemented: one proposal inference and direct rendering of verified tool output, avoiding a second inference call. Potential future improvement: explicitly started isolated warm model worker with fresh validated per-conversation context and independently revalidated stop/isolation. Not implemented. Integrity, Guardian, scope, approvals and audit must not be skipped for speed; no paid service is needed.

Git commit:
- Commit containing this record; exact SHA supplied after push and remote verification. Parent is 308fdfd71ccd42d50a488379d2b34abed71fdd6a. Prior history/user work preserved.

Known limitations:
- Only the prepared Linux x86_64 cloud profile is verified. Mac M1 memory/performance/native runtime remain PENDING_EXTERNAL_VERIFICATION; nothing was installed there.
- Only three bounded read-only tools operate in explicitly configured synthetic workspaces. Normal chat remains tool-free; tool mode handles one intent per turn. No arbitrary shell, writes, Git, deployments, browser, external network or live specialist/workflow execution.
- No interactive authenticated approval issuer exists. Approval-required chat operations stay blocked. The trusted issuer API is not available to model prompts; synthetic approval tests do not prove a real-user review interface.
- Model path extraction can fail despite hints; invalid proposals are denied rather than silently repaired or retried. Passing samples do not establish general reliability or prompt-injection immunity.
- Scope/profile/OS actor and protected source are trusted operator inputs. Filesystem handlers and kernel restrictions do not isolate malicious same-user code or prevent host/database rollback/tampering. Plaintext audit/state needs separate retention/backup protection.
- Audit storage caps at 10,000 tool events and may fail sooner under storage/resource limits; this fails closed. No automatic retention/export, encrypted audit or remote immutable log is implemented.
- Synchronous single-owner controller and global one-model lock remain. Mission state is in memory; completed exchanges/provenance persist. SIGKILL/host failure can leave pending state/container requiring operator review. Kernel/host failure cannot guarantee cleanup.
- Existing runtime assets/image are local prerequisites; clean-room installation and broader platform/dependency certification are not claimed. Development source delivery does not mean the full assistant/voice stack is operational.

Remaining blockers:
- None for the tested Milestone 3 scope. Interactive human approvals, Mac hardware and later live service/specialist/voice integrations remain unavailable or externally unverified; they are not enabled by this milestone.

Next action:
- Stop after this milestone's verified commit/push. Await the next authorized milestone. Do not merge, deploy, install on Mac or spend money.

Approval required:
- No for this explicitly authorized implementation, tests, commit and push to develop. Production, main merge, spending and Mac installation still require separate authorization.
