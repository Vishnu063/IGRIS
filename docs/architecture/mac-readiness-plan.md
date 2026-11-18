# Native ARM64 and Mac voice implementation plan

Baseline inspected 2026-11-17: develop `24196dad0094b60aec57450d0bd267a30dca4cd0`; draft PR #1 is open at `58276b6c7bfa4cf714683ae912b40170ebc946e5`. New branch `feat/mac-arm64-native-voice` starts from develop and reuses that exact commit, without duplicating its fixes or changing develop/main. A fresh standard-library suite had one missing Mem0 fixture error on develop; all 295 tests passed after PR #1. This environment supports Unix sockets and Docker; the previous three socket errors are historical and did not recur.

Inspection confirms explicit x86-only Guardian and inference gates, unconditional Mac startup denial, a Linux-specific voice path, existing private memory and exact approvals, lazy single-task scheduling, data-only backup, read-only Ops and optional quarantined n8n. Existing runtime assets are absent in this fresh checkout. Prior execution reports and evidence do not establish current live functionality.

Implementation order:

1. Separate reviewed x86_64/aarch64 Guardian syscall profiles; compare Linux v6.17 UAPI and actual guest headers. Add irreversible live restriction probes; preserve all exact scoped approval and process-cleanup controls.
2. Add an architecture-specific native ARM64 runtime preparation/transport path with pinned assets, ELF checks, dependency hashes, native image validation and boot/source-bound prerequisite evidence. No emulation fallback. Keep Mac startup gated by current real guest checks.
3. Prepare a dedicated reversible Lima installation/configuration and guest bootstrap, private loopback dashboard, bounded CPU/RAM/disk, no home sharing/Docker forwarding/autostart. Reuse current official supported binary installation, pinned to reviewed checksums. No Mac command is executed here.
4. Implement native explicitly requested microphone capture/transcription and installed-voice output with cancellation/permission/error handling, untrusted text submission to the existing authenticated controller and text fallback. No interception, clipboard access, implicit downloads or speech-based approvals.
5. Reproduce the exact quarantined n8n lock audit; evaluate a current maintained compatible candidate without changing/quarantine-bypassing the working core. Accept only freshly audited and actually isolated-tested runtime changes.
6. Run focused and regression/security checks, current live Linux checks where dependencies can be safely prepared, and publish source-bound evidence/pending work. Mac microphone/playback, ARM64 guest and measured M1 performance require actual user output; give short commands only for the next executable gate.

Reported Mac observations (owner supplied, not independently verified): ARM64 MacBook Air/8 GB, reported macOS 27.2.1 build 26B131, Python 3.12.10, Git 2.54.0, hardware virtualization=1, about 149 GiB free, no Homebrew/Lima/Docker in PATH. No installation or VM exists. No accounts, paid resources, production deployment or autonomous repairs are in scope.
