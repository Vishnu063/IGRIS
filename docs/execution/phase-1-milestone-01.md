IGRIS EXECUTION REPORT

Phase: 1
Milestone: 1
Title: Audit the existing prototype and activate real Hermes inference

Status: PASS

Implemented:
- Audited all original 50 execution reports, delivery/reuse/security/integration records and actual selected controller, Guardian, Hermes, n8n, Ops Pilot, specialist, memory, dashboard and voice source/tests. Recorded baseline document hashes and actual-versus-simulated findings.
- Prepared a source-run Hermes inference profile using exact Python 3.14.9, 53 hash-locked dependencies and the existing copied Hermes source. No replacement agent/controller built.
- Verified actual AIAgent.run_conversation with licensed local Qwen3.5-2B Q4_K_M inference through a pinned llama.cpp CPU engine. No hosted model credentials or paid API used.
- Added manual-only cloud artifact preparation/probe scripts, a restricted ephemeral container, actual default-empty Guardian denial at native tool dispatch and atomic latest-outcome evidence.
- Preserved failed model/configuration attempts; removed only checksum-verified rejected-model cache files downloaded by this task.
- Fixed development-source bundle omission of Dockerfiles and added a stale-PASS evidence regression.

Files changed:
- README.md
- THIRD_PARTY_NOTICES.md
- docs/execution/README.md
- docs/execution/phase-1-milestone-01.md
- docs/validation/activation-audit-sources.json
- docs/validation/hermes-activation-audit.md
- docs/validation/hermes-activation-status.json
- docs/validation/hermes-inference-attempts.json
- docs/validation/hermes-inference-live.json
- docs/validation/hermes-runtime-dependencies.json
- integrations/hermes-inference/profile.json
- integrations/hermes-inference/requirements.in.txt
- integrations/hermes-inference/requirements.lock.txt
- integrations/hermes-inference/Dockerfile
- integrations/hermes-inference/README.md
- integrations/hermes-inference/LICENSE-model.txt
- integrations/hermes-inference/LICENSE-engine.txt
- scripts/fetch_hermes_probe_assets.py
- scripts/hermes_inference_worker.py
- scripts/run_hermes_inference_probe.py
- src/igris/artifacts.py
- tests/test_artifacts.py
- tests/test_hermes_probe_evidence.py
- runtime/* contains ignored local downloads/venv/cache/evidence, never committed.

Commands executed:
$ git status --short
$ git branch --show-current
$ git log -4 --oneline
$ python3 (read all 50 reports; inspect source/configuration, capabilities and versions without secret values)
$ uv python install 3.14.9 --install-dir runtime/python --no-bin --no-progress --system-certs
- uv catalog lacked that exact version; replaced this attempt with a verified upstream-pinned standalone archive, not an unverified Python version.
$ python3 (public HTTPS artifact acquisition, SHA-256 verification and safe data-filtered archive extraction)
$ UV_CACHE_DIR=runtime/uv-cache uv venv --python runtime/python3149/python/bin/python3.14 runtime/hermes-venv
$ UV_CACHE_DIR=runtime/uv-cache uv pip compile vendor/hermes-agent/pyproject.toml --python runtime/hermes-venv/bin/python --overrides runtime/upstream-overrides.txt --exclude-newer '3 days' --generate-hashes --only-binary :all: --output-file runtime/hermes-full-supported.lock --system-certs --no-progress --quiet
- Initial raw resolution omitted upstream overrides and falsely suggested a Pillow blocker; corrected source review and supported resolution succeeded (68 distributions).
$ UV_CACHE_DIR=runtime/uv-cache uv pip compile runtime/hermes-inference.in --python runtime/hermes-venv/bin/python --exclude-newer '3 days' --generate-hashes --only-binary :all: --output-file runtime/hermes-inference-reviewed.lock --system-certs --no-progress --quiet
$ UV_CACHE_DIR=runtime/uv-cache uv pip install --python runtime/hermes-venv/bin/python --require-hashes --only-binary :all: --system-certs --no-progress -r runtime/hermes-inference.lock
$ UV_CACHE_DIR=runtime/uv-cache uv pip check --python runtime/hermes-venv/bin/python
$ BUILDX_CONFIG=runtime/buildx env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt --tag igris-hermes-probe:milestone1 --file integrations/hermes-inference/Dockerfile integrations/hermes-inference
$ python3 scripts/fetch_hermes_probe_assets.py
$ python3 scripts/run_hermes_inference_probe.py
$ python3 -m compileall -q src scripts tests
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ git diff --check
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ git add (explicit milestone files)
$ git diff --cached --check
$ git commit (milestone implementation and evidence)
$ git push origin develop
- GitHub ref checked read-only before work and again after publication; no main merge or forced push.

Tests executed:
$ python3 -m unittest discover -s tests -q
$ python3 -m unittest discover -s tests -p test_hermes_probe_evidence.py -v
$ python3 -m unittest discover -s tests -p test_artifacts.py -v
$ python3 scripts/run_hermes_inference_probe.py
$ python3 scripts/fetch_hermes_probe_assets.py
$ UV_CACHE_DIR=runtime/uv-cache uv pip check --python runtime/hermes-venv/bin/python
$ PYTHONPATH=src python3 -m igris.guardian.scan

Test results:
- Passed: baseline 166 tests in 22.323s; final complete suite 167 tests in 21.646s after source/artifact changes. New actual-file regression proves failed preflight replaces an old PASS and never calls Docker.
- Passed: 53 installed distributions compatible; reviewed quarantined lock resolves the same installed versions. Full supported upstream core graph resolves 68 distributions using its own overrides.
- Passed: original copied Hermes imports in the restricted container; actual final AIAgent calls returned 31 for 18+13, 24 for random 12+12, and WINDOW for uppercase window. One real Hermes API call per answer. Native-engine direct control also returned 31.
- Passed: endpoint rejects unauthenticated inference; non-root execution; actual source-write rejection; actual missing external network route; empty tools; Guardian rejects dispatch; automatic package installs disabled; container removal independently checked.
- Passed: worker/profile evidence hashes verified, safe artifact cache checks, source/CI/delivery/compile/whitespace and final worktree/index configured credential-pattern scan.
- Staged formatting initially flagged upstream model-license CRLF line endings; normalized line endings/trailing whitespace in the copied notice without changing license text or terms, then reran checks. No scanner/formatting rules suppressed.
- Failed historically: missing native OpenMP library, incompatible initial model context, and multiple 0.8B arithmetic answers. Fixed/replaced within this milestone and retained in attempt history. The initial raw dependency-blocker diagnosis was corrected after applying existing upstream policy.
- Failed unresolved: none in the final tested inference profile. Broader competence/security/hardware validation is not implied.
- Skipped: hosted Actions, production, Mac and later integration milestones.
- Mocked: existing legacy contract/fixture suites and Docker-not-called assertion in the new preflight regression. The actual model/engine/SDK/Hermes live probe is not mocked.
- Not tested: full optional Hermes CLI/desktop/browser/document stack, comprehensive dependency vulnerability/licensing audit, long-context quality, sustained coding competence, full assistant chat, conversation memory, live n8n/Ops Pilot/specialists/voice, Mac hardware.

Security review:
- Default IGRIS flags/adapter remain disabled; no native execution tools granted. Copied source hashes and upstream security/version checks retained.
- Manual-only, offline non-root container; read-only mounts; no Docker socket/credentials mounted; dropped capabilities; no-new-privileges; 2 CPUs, 3 GiB memory, bounded PIDs/tmpfs and timeout/cleanup.
- Model endpoint is authenticated private container loopback. Ephemeral local credential is not placed in source, prompt, command arguments or evidence. No external model account needed.
- Public model/engine downloads have pinned hashes, source provenance and proper licenses. No TLS verification disabled; image build uses session CA as a secret mount and signed package repositories with pinned libgomp version.
- No money spent on external model APIs; no paid service activated, client contacted, Mac installation, production deployment or main merge. Self-review, not independent security certification.

Git commit:
- Commit containing this record; exact SHA supplied after commit/push and GitHub ref verification.

Known limitations:
- PASS covers the audited source-run reasoning profile and specific real checks, not a complete working assistant. The default product adapter, chat UI and persistent conversation connection remain future work.
- Current cloud answer times were about 13–23 seconds on two CPUs; no voice-latency, M1 RAM/storage or quality guarantee. A few passing prompts do not establish reliable arithmetic or coding competence.
- Existing 50-step delivery status remains historical; current milestone status is docs/validation/hermes-activation-status.json.
- Runtime artifacts/image are local development prerequisites, not committed binaries. The documented cloud rebuild can produce a new image ID that needs recording/revalidation. Clean-room setup and full optional-feature runtime have not been certified.
- Host Docker operator/kernel trust, unencrypted development state, regex redaction limits and incomplete upstream audit remain residual risks.

Next action:
- Connect the verified reasoning profile to the existing IGRIS controller under authenticated user control, retaining Guardian enforcement and disabled native tools; then add chat and approved conversation persistence as separate tested milestones.

Approval required:
- No for this authorized development milestone. Paid services, production, Mac installation, external client communication and main merge remain unauthorized.
