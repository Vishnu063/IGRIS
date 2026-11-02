IGRIS EXECUTION REPORT

Task: 12 / 14
Title: Performance optimization
Status: PASS

Recorded: 2026-11-02T06:16:48.316072+05:30

Implemented:

- Opt-in manually started warm model process, fresh actual Hermes agent/context for every turn; default one-shot mode retained.
- Authenticated sequence-bound bounded private pipe transport, twenty-request/idle/lifetime limits, tracked owned cleanup, concurrency denial and no automatic restart.
- CLI --warm-runtime with nested cleanup; explicit Mem0 conflict because the shared resource slot stays reserved.
- Fixed OwnerActions decision timeout incorrectly applying after owner approval; approved execution still enforces existing five-minute expiry, exact scope and one-time consumption.

Real versus simulated:

- Actual same pinned Qwen3.5-2B Q4_K_M and real Hermes in both cold and warm samples; no simulated inference.
- Actual persistent recall and cross-conversation isolation, real structured time proposal, existing Guardian approval and actual time execution.
- Owner approval inputs are automated trusted fixtures; valid-payload forged MAC and signed replay were genuinely rejected by the final worker.

Tests and results:

- 271 regression tests PASS in 62.517 seconds; four focused warm boundary tests PASS.
- Paired cold/warm responses 12 and 14 correct. Separate final transport response 11 correct; forged transport and signed replay denied and cleanup verified.
- Conversation persistence, separate-session context isolation, one-use Guardian approval/execution, unsupported shell denial, active warm worker cancellation and no automatic restart PASS.
- Guardian secret scan, compile, CLI help with PYTHONPATH=src and whitespace checks PASS. Initial help invocation omitted PYTHONPATH and failed import; corrected invocation succeeds.
- Performance collection precedes final transport serialization/nested cleanup hardening; original source hashes retained and final transport separately verified live.

Security review:

- Native tools remain disabled and default-empty Guardian rejects actual agent dispatch on every fresh agent.
- Original model/archive/upstream source integrity checks and 65536-token context retained; no context or sandbox controls disabled.
- Network-none, non-root, read-only, 3 GiB/two-CPU worker; approval DB, credentials and workspace not mounted.
- No keys in arguments, prompts, logs or source; private ephemeral pipe key and monotonically increasing signed frames. Same-user/admin tampering remains outside isolation claim.

Performance:

- Cold requests 69.477/60.868 s; warm 36.904/40.111 s; startup 11.178 s. Total two-request reduction including startup: 32.34%; mean per-request reduction excluding startup: 40.91%.
- First cold sample overlapped regression load. Small Linux sample, no Mac benchmark or latency SLA.
- Model-ready 4.334 s, framework imports 2.246 s, unchanged integrity preflight 2.539 s; generation/fresh-agent work dominates.
- Model peak 2871968 KiB (~2.74 GiB); no memory reduction claimed. Guardian authorization 6.200 ms, tool execution 0.408 ms. Warm cancellation/removal 2.901 s.

Known limitations:

- Warm mode reserves the heavy worker slot; Mem0/n8n/Ops cannot run concurrently through that slot. Dashboard stays one-shot.
- Small-model specialist reasoning remains fallible. Already quantized Q4 model retained; no untested smaller model downloaded or substituted.
- Original Mac and human voice acceptance remains unavailable. Kernel/same-user risks and abrupt-crash operator recovery remain.

External requirements:


Files changed:

- README.md
- docs/integrations/warm-inference.md
- docs/validation/warm-hermes-live.json
- docs/validation/warm-protocol-live.json
- scripts/hermes_chat_worker.py
- scripts/hermes_inference_worker.py
- scripts/hermes_specialist_worker.py
- scripts/hermes_tool_worker.py
- scripts/hermes_warm_worker.py
- scripts/test_warm_hermes_live.py
- scripts/test_warm_protocol_live.py
- src/igris/adapters/hermes_warm.py
- src/igris/chat.py
- src/igris/guardian/activities.py
- tests/test_owner_actions.py
- tests/test_warm_boundary.py

Commands executed:

$ python3 scripts/test_warm_hermes_live.py
$ python3 scripts/test_warm_protocol_live.py
$ python3 -m unittest discover -s tests -p test_warm_boundary.py -q
$ python3 -m unittest discover -s tests -q
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ PYTHONPATH=src python3 -m igris.chat --help
$ git diff --check

Git commit:

- Verified implementation: 3a27888de701a404287c18e1b81244c0b21bc2e6
- This report is recorded in a following documentation commit; remote tip is checked after publication.

Git delivery:

Connected GitHub App publishes the exact staged tree using expected-head fast-forward; remote branch SHA is verified separately. Git CLI authentication unavailable.

Next task:

- 13

Approval required:

- No for authorized development/push. Mac access, production, main merge, paid services and new host privileges remain unauthorized.
