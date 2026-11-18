# IGRIS native Mac readiness — execution report

Current follow-up: owner-reported native Lima installation and ARM64 VZ guest boot passed after the [TLS repair](mac-tls-retry.md). The first boot exposed unrequested loopback UDP forwarding; [the policy correction/migration report](mac-vm-policy.md) records the fix, 331-test replay and next actual-Mac inspection gate. The dedicated VM exists; IGRIS guest runtime/inference/voice acceptance remains pending. Initial source-bound results below remain historical.

Delivery date: 2026-11-18 IST; verification evidence retains its recorded UTC timestamps. **Overall goal: BLOCKED pending actual Mac execution and human voice acceptance.** Repository implementation and available verification were completed; no claim that IGRIS is installed on the Mac, that native speech works, or that the release is production-ready.

Repository: `Vishnu063/IGRIS`. Feature branch: `feat/mac-arm64-native-voice`, based on current develop `24196dad0094b60aec57450d0bd267a30dca4cd0`. Draft PR #1 remained open and unmerged; its exact commit `58276b6c7bfa4cf714683ae912b40170ebc946e5` is reused unchanged in this branch, not recreated/cherry-picked. Existing history and unrelated files are preserved. No main/develop ref was changed, production deployed, paid service activated or external account connected.

## Baseline and scope

Read current README, architecture/single-task design, release/progress records, Mac/voice/security/runtime documentation, current evidence and the actual controller, SQLite, Guardian, transport, specialist and Ops code. No AGENTS.md was present. Existing components are reused; Hermes remains the only reasoning framework and Guardian the only authorizer. The implementation plan was recorded before edits in [mac-readiness-plan.md](../architecture/mac-readiness-plan.md).

This managed cloud environment is Linux x86_64/Python 3.12.14, kernel 6.18.57, Docker 29.9.2/rootless/VFS, Node 24.22.1/npm 11.9.0. Worker Python is the pinned 3.14.9. It has usable Unix sockets and Docker, unlike the previous turn. Fresh develop ran 295 tests with one missing Mem0 fixture error; after applying PR #1 unchanged, all 295 passed. The previously reported 292 passes/three socket errors did not recur. An ignored runtime directory was created for logs; no installed optional runtime was assumed as evidence.

Owner-supplied Mac observations: ARM64 MacBook Air/8 GB RAM, reported macOS 27.2.1/build 26B131, Python 3.12.10, Git 2.54.0, virtualization support and about 149 GiB free; no Homebrew/Lima/Docker found and no VM installation. These are observations supplied by the owner, not remote hardware tests. There is no remote Mac connection.

## Implemented repository work

1. **ARM64 Guardian:** reviewed architecture-specific tables, kill-on-ABI-mismatch BPF and rejection of high-bit syscall ABIs; network/process/exec/io_uring denials preserved. Constants match Linux v6.17 UAPI definitions byte-verified against official Git blobs. A native target-header C compiler comparison plus actual irreversible syscall probes are required. The x86 probe passed every restricted syscall; ARM execution is not claimed.
2. **Native runtime:** ARM64 Python/engine/GGUF selection with no x86 or Mac-host fallback, ELF machine checks, exact reviewed profile, native image metadata/recipe identity, boot/source/kernel-bound proof and dependency hashes. Existing x86 behavior has a reviewed rebuild path because image build timestamps cannot reproduce an old private image ID. Warm ARM mode and unrelated x86-only optional integrations remain disabled until separately accepted.
3. **Resource enforcement:** daemon CPU/memory/swap/PID capabilities must be real, cgroup v2 must be supported, and the worker reads actual `memory.max`, `memory.swap.max`, `cpu.max` and `pids.max` before inference. Model containers request a 3 GiB memory/combined-swap ceiling, two CPUs and 128 PIDs; swap is therefore zero within the model container. CLI flags alone are not accepted as enforcement proof.
4. **Mac VM package:** reviewed current official Lima 2.3.0 binary installation; SHA-verified private install with safe archive extraction, manifest validation and preservation-aware uninstall. Dedicated VZ/aarch64/two-CPU/4 GiB/sparse-24-GiB profile, no home mounts, host socket forwarding, Rosetta, agent/X11 forwarding or autostart. Actual expanded Lima instance settings are validated against the upstream schema. Guest bootstrap preserves existing clones, installs only inside the dedicated guest, disables daemon autostart and uses a fresh Docker group context.
5. **Manual lifecycle:** exact-source guest bootstrap/preparation/verification/startup and private account export. Startup requires current native acceptance and kernel/runtime checks. Foreground shutdown stops the dedicated VM; interrupted verification stops only that identity-checked VM. Host RSS/swap and guest memory/swap measurement paths are prepared. These Mac operations are not represented as executed.
6. **Native voice:** original Swift AVFoundation/Speech helper, explicit TCC usage descriptions, local ARM64 compilation/ad-hoc signing, installed OS voice synthesis and optional owned playback. Recording is manual and bounded to 1–30 seconds. On-device recognition is required; there is no cloud fallback or implicit voice/model download. Explicit English/Hindi/Marathi routing, mute/cancel, text fallback, five existing filtered greetings and temporary-audio cleanup are implemented. Actual Swift SDK compilation, locale availability, permissions, human recognition and speaker usability remain unverified.
7. **Cross-device single-task boundary:** authenticated/CSRF-protected native-I/O reservations block competing foreground work; nonce, expiry, cancellation and emergency stop are enforced by the existing coordinator. Native text reaches the existing chat controller, not another agent framework. Transcripts cannot submit approvals. Audio stages release resources before model inference. Unit fixtures for devices/inference are explicitly synthetic.
8. **Dashboard and memory:** logout revokes the server-side Basic identity, cancels authority/work and requires explicit restart. Client-side stale replies, private form/retry data and visible private state are cleared. Existing chat/memory and exact tool approvals are preserved. Real data-only restore recovered the codename while rejecting an old approved-unused action; no credentials, pending requests or approvals were restored.

## Exact source versions and test evidence

- Functional diagnostic implementation: `31a9ea482da3ce3a0d8f9c4f9fe93339bc6b80bb`. Four live artifacts' recorded source hashes were compared against this commit and match exactly. Tests were performed before publication against those exact source bytes.
- Resource hardening: `3d44328df88d31f098023f8f953ddd821bd3ae48`. All 313 tests passed in 25.572 seconds and an actual daemon preflight correctly refused inference.
- Final source/privacy commit: `b4e31ab79762ae1015b9f676dfa48e73772c4d1c`. Final regression: 313 tests passed in 25.831 seconds; JavaScript syntax check passed. A separate clean-worktree replay also passed all 313 tests in 26.510 seconds, with no prepared model/runtime dependencies.
- Documentation/evidence follows separately to avoid a self-referencing commit SHA. The final delivery states the verified remote tip.

| Available check | Actual result | Evidence / limitation |
| --- | --- | --- |
| Core regression, including real broker/filesystem/SQLite and explicit unit fixtures | PASS: 313, zero failures/skips | Synthetic device/inference fixtures are not live acceptance |
| Native x86 target headers and restricted syscall execution | PASS | [kernel proof](../validation/mac-readiness-kernel-x86.json) |
| ARM64 UAPI/constants/BPF source review | PASS source review | [references/hashes](../validation/arm64-syscall-review.json); native ARM execution BLOCKED |
| Python/engine ARM64 ELF, Lima ARM64 Mach-O, actual safe archive extraction | PASS artifact review | [asset inventory](../validation/native-assets-review.json); no foreign binary execution |
| Cross-platform hash-locked ARM64 wheels | PASS: 53 downloaded | Availability/metadata, not native runtime compatibility |
| Real cold Hermes and restart recall | PASS diagnostic: three fresh randomized pairs plus new-conversation isolation | [chat artifact](../validation/mac-readiness-chat-live.json); preceding resource-hardening commit |
| Real Hermes/Guardian attack matrix | PASS diagnostic: eight grouped scenarios, 24 sanitized audit rows | [Guardian artifact](../validation/mac-readiness-guardian-live.json) |
| Real backup/restore, recall and no approval resurrection | PASS | [backup artifact](../validation/mac-readiness-backup-live.json) |
| Real authenticated HTTP chat, role/CSRF/Origin denial, cancel and logout | PASS functional diagnostic | [HTTP artifact](../validation/mac-readiness-http-live.json); native browser UI NOT TESTED |
| Current hardened cloud inference activation | BLOCKED; expected denial PASS | [resource evidence](../validation/mac-resource-enforcement.json) |
| Installed core Python vulnerability query | PASS: 53 versions, no reported OSV advisories at query time | [audit](../validation/mac-core-python-audit.json); excludes OS/native/optional dependencies |
| CI/delivery/provenance and source/index credential scanning | PASS | Manual-only CI, 2,674 Hermes hashes, fifteen definition pairs; hosted CI not run |
| Actual ARM64 guest, Mac host, microphone and speaker | BLOCKED | No hardware access; no mocked proof substituted |

Important resource finding: this cloud daemon reports **MemoryLimit=false, SwapLimit=false, CpuCfsPeriod=false, CpuCfsQuota=false, PidsLimit=false, CgroupDriver=none**. Earlier functional requests returned real responses, but their `3g` flag did not establish a bound. The final code now refuses that runtime before model startup. No later real inference through the hardened code is claimed. A proper native guest must pass both daemon capability and actual worker-kernel checks.

Functional diagnostic timings: cold chat turns 25.804–37.527 seconds; authenticated HTTP chat 36.322 seconds including sampling; cancel/verified worker disappearance 0.862 seconds. Observed controller peak at chat completion: 24,543,232 bytes. The daemon-reported raw memory peak was 3,781,988,352 bytes, includes cache and may reflect a shared/unbounded cgroup here. It is **not model RSS or a verified memory ceiling**. Docker PIDs are outside this process namespace, so process/model RSS is recorded as null, not zero. These Linux observations are not Mac M1 results or a paired performance-improvement claim.

Failed attempts and fixes are retained honestly: the first live recall attempt failed and lacked useful response diagnostics; the harness now preserves failed progress, the worker requests exact identifier copying, and three new randomized conversations passed without retry-until-success logic. Small-model factual mistakes remain possible. A full-discovery import-path collision introduced by an archive test was fixed by restoring its temporary script path. Actual archive extraction caught a relative/canonical path comparison issue missed by the initial unit fixture; normalization fixed it before Mac delivery. Source review also caught the backup acceptance script rewriting historical tracked evidence; output now goes to a private runtime artifact, leaving old reports intact. Resource measurement first exposed inaccessible PIDs and then unsupported cgroups; neither was turned into a false zero-RAM or resource PASS.

Commands actually used, from this checkout (live diagnostic commands apply to the pre-hardening source above):

```sh
$ python3 -m unittest discover -s tests -q
$ python3 scripts/verify_guardian_kernel.py --output runtime/mac-readiness/x86-kernel-proof.json
$ python3 scripts/test_chat_live.py
$ python3 scripts/test_guardian_tools_live.py
$ python3 scripts/test_chat_backup_live.py --output runtime/mac-readiness/backup-live-evidence.json
$ python3 scripts/verify_dashboard_http.py
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ node --check src/igris/web/control.js
$ bash -n packaging/macos/bootstrap_guest.sh
$ git diff --check
```

Pinned assets were fetched with the existing guarded fetcher; x86 dependencies installed with the committed hash lock and checked with uv. ARM64 wheels were downloaded using pip's explicit cp314/aarch64 binary targets and `--require-hashes`; none was imported or executed as ARM proof. The image was rebuilt from the pinned Ubuntu index and exact libgomp package. The retained runtime profile records its exact derived image ID; the old committed profile was not weakened to accept an arbitrary image.

## n8n remediation — BLOCKED, optional and independent

The existing quarantine was preserved. The original committed lock was hash-verified/reconstructed; fresh audit reproduced **172 affected entries: 6 critical, 82 high, 81 moderate, 3 low**. Current maintained/stable n8n **2.48.4** was evaluated through a new metadata-only lock: **7 critical/77 high**. Reviewed same-major patch candidates for form-data, fast-xml-parser v4/v5 and tar v7 reduced critical entries to **one**, but **80 high** entries remain. The remaining critical tar **6.2.1** instances are under cacache, node-gyp and sqlite3; changing those to a different major without compatibility proof is not accepted. npm's proposed n8n 1.17.0 major downgrade was rejected. No `audit fix --force`, runtime install, workflow activation or quarantine clearing occurred.

No safe, verified compatible dependency solution has been established. Candidate compatibility and real isolated workflow/cancellation acceptance remain BLOCKED. The exact counts, ranges, applied patch candidates and raw audit/lock hashes are in [mac-n8n-audit.json](../validation/mac-n8n-audit.json). Public advisories/package metadata were queried; no credentials or customer content sent. This optional blocker does not create a core n8n dependency or stop core Mac work.

## Security review and remaining limits

Default-deny Guardian, exact target/arguments/scope/intent, owner-only decisions, TTL/one-time consumption, path containment, native-tool prohibition and owned launch ledgers remain. No generic shell/file mutation/browser/network tool was enabled. Host setup commands are trusted owner operations, never model tools. Model workers receive neither host homes/sockets nor approval/credential stores. Specialists retain the shared model and permissions; Ops source/read-only disposable-target behavior is unchanged. Its live optional runtime was not reinstalled/retested this turn and is not declared ARM64-compatible.

Same-user/admin Python/SQLite/manifest tampering, rollback, kernel vulnerabilities and hostile local browser access are not independently sandboxed. Receipts prove checks of a particular environment, not resistance to a malicious host owner. Abrupt guest loss may retain owned-launch/foreground recovery records; do not delete them or kill matching process names blindly. Unknown cleanup blocks authority. Host/guest cancellation, physical microphone shutdown and actual resource return still need Mac tests. OS speech-service memory is not an IGRIS-owned process to kill.

## Delivery and next executable gate

Changed code covers the native runtime/kernel, existing adapters/controller/dashboard, native voice helper/client, Mac bootstrap/lifecycle and focused tests. Documentation, asset/advisory inventories, source-bound live diagnostics and current pending-work tracking are added. Models, virtual environments, compiled helpers, private credentials and large downloads remain ignored. [Native setup/update/backup/shutdown/uninstall guidance](../delivery/native-mac-guide.md) distinguishes prepared commands from Mac-tested behavior.

The next required user action is to review the draft and run **only private configuration/Lima installation** on the actual Mac, returning the non-secret output. This is a new actionable gate, not another check that merely rediscovers the missing VM. No voice model or assistant is installed by that step. VM boot/native verification and per-language human tests follow only after actual outputs. Production readiness, spending, account connections, main merges and autonomous repairs remain outside scope.
