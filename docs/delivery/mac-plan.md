# Later Mac M1 installation and verification plan — not executed

Target: Apple M1, 8 GB shared RAM, about 50 GB free disk, initial spending INR 0.
All hardware estimates remain unverified. No Mac package, app, model, daemon,
microphone permission or configuration has been installed or changed.

1. Obtain a separate owner request for Mac work. Record macOS version, free disk,
   current tools, CPU/memory and backup state using read-only checks first.
2. Select a reviewed IGRIS commit; review its unresolved security/licensing
   findings. Establish an isolated cloud/Linux execution boundary for agents and
   independent Guardian authority before exposing any real execution credentials.
3. Review the complete pinned Hermes release and dependency/runtime requirements.
   This repository carries a curated backend subset, not a standalone installer.
   Verify compatible Python 3.14 and missing assets in an isolated environment;
   audit import/startup/network/model side effects. Do not assume an empty tools
   list alone isolates the complete process.
4. Choose one genuinely zero-cost authorized model/provider option, verifying
   terms, limits, credential scope and hard spending controls. Unknown cost means
   blocked. Large local LLMs are unsuitable defaults for this 8 GB target.
5. Enable one service at a time. Run actual Hermes reasoning tests with tools
   disabled, then approved boundary tests. Keep cloud credentials outside model
   processes and never turn a feature flag into permission.
6. If needed, reuse an existing approved n8n instance. Test the inactive fixture
   workflow import, authentication, version, retention and exact contracts before
   real workflows. Do not expose loopback ports publicly or assume Docker Desktop
   networking matches Linux host networking.
7. Connect only the audited Ops Pilot read surface first. Verify actual target
   identity, freshness and health evidence. Mutations remain blocked until its
   execution boundary can enforce exact Guardian approval. Do not modify the
   separate Ops Pilot repository without new authorization.
8. Select a voice engine after reviewing VoiceStudio's AGPL-3.0-only terms and
   individual model/voice licenses. Measure download/storage/runtime peaks. Its
   stated 8 GB minimum is not proof that it fits with all other services. Prefer
   one small ASR/TTS engine on demand; no unauthorized actor cloning.
9. Physically test push-to-talk permission denial, explicit start, indicator,
   stop/cancel, maximum recording duration and crash recovery. Verify English,
   Hindi, Marathi and mixed speech using recordings; routing tests alone are
   insufficient. Never enable continuous listening by default.
10. Measure total RAM, swap, CPU, startup, latency, thermals and storage under the
    chosen combined workload. Test backup restoration, approval expiry/replay,
    service failure and user stop. Keep specialists lazy and bounded.
11. Review measured results before any optional background service. Keep production
    deployments, paid services and client communication separately approval-gated.

Cloud x86_64 performance is not transferable evidence for this Mac. If hardware,
storage, compatibility, permissions, license eligibility or zero-cost access is
unavailable, record BLOCKED/PENDING_EXTERNAL_VERIFICATION rather than weakening
controls. This document authorizes no installation or external activation.
