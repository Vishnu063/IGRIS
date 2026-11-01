# Manual cloud Hermes inference profile

Scope: the Phase 1 Milestone 1 inference runtime, reused by
[Milestone 2 controller chat and memory](../../docs/integrations/hermes-chat.md).
Actual copied Hermes `AIAgent.run_conversation` uses licensed local CPU inference.
This is not the complete assistant, legacy planner adapter, desktop installation
or activation of specialist tools. Historical 50-step records remain unchanged.

Linux x86_64 development only. Mac execution is refused by the artifact helper.
Use existing `develop` checkout, uv, managed Docker and normal network/CA policy.
No root daemon restart or privileged container. All artifacts/venvs/cache are
under ignored runtime/. The fetch helper makes public HTTPS downloads, checks
pinned hashes and safely extracts archives; it starts no services. The model is
about 1.28 GB; fresh setup requires additional Python, dependency and image space.

From repository root, explicitly prepare the cloud environment:

```sh
$ python3 scripts/fetch_hermes_probe_assets.py
$ UV_CACHE_DIR=runtime/uv-cache uv venv --python runtime/python3149/python/bin/python3.14 runtime/hermes-venv
$ UV_CACHE_DIR=runtime/uv-cache uv pip install --python runtime/hermes-venv/bin/python --require-hashes --only-binary :all: --system-certs -r integrations/hermes-inference/requirements.lock.txt
$ UV_CACHE_DIR=runtime/uv-cache uv pip check --python runtime/hermes-venv/bin/python
```

The checked lock has 53 distributions and respects upstream's three-day supply
chain quarantine. It retains applicable upstream versions and deliberately omits
unused browser/web/document/graphics engines. The full core graph resolves with
upstream overrides (68 distributions); the initial raw Pillow conflict was a
check missing those overrides, not proof that upstream cannot install. Neither
profile resolution nor import proves untested features work.

Build the small, pinned-base image with the session CA as a build secret. Preserve
Docker configuration/registry credentials while selecting the managed local socket:

```sh
$ BUILDX_CONFIG=runtime/buildx env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt --tag igris-hermes-probe:milestone1 --file integrations/hermes-inference/Dockerfile integrations/hermes-inference
$ env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock image inspect igris-hermes-probe:milestone1 --format '{{.Id}}'
```

profile.json records the exact image verified in this workspace. A fresh rebuild
can have a different image ID even with the same recipe; review the built image,
record that exact local ID in the trusted profile and rerun acceptance. The
launcher never pulls a replacement or silently trusts a mutable tag. This is
operator setup, not an agent-exposed installer or permission decision.

Run the one-shot test explicitly:

```sh
$ python3 scripts/run_hermes_inference_probe.py
```

Requires supported Docker socket access; no host-process fallback. A new
non-root container has no external network or exposed ports, read-only source/
model mounts, dropped capabilities, no-new-privileges, two CPUs, 3 GiB memory and
bounded tmpfs/PIDs. Only a private authenticated loopback model endpoint exists
inside that container. Upstream safe-worker mode disables normal profile/plugin
startup; empty tools and default-empty IGRIS Guardian reject tool dispatch.
No model credential is needed; the ephemeral local credential is never printed.

Real regression/random arithmetic and uppercase answers are asserted. Model
quality failures are retained, never presented as successful connectivity proof.
Latest evidence is written atomically to runtime/hermes-inference-evidence.json;
new runs invalidate previous PASS evidence before preflight. Failure writes FAIL,
stop writes STOPPED. Successful evidence binds model/profile/worker hashes and
UTC time. Containers are removed after completion/failure/timeout; Ctrl+C requests
cleanup. No model stays running or starts on import, login or boot.

Even a passing probe establishes only the tested source-run inference path and
specific local controls. It does not certify arbitrary prompt safety, sustained
reasoning accuracy, 64K long-context quality, OS/kernel security, Mac M1 resource
use, voice or a fully connected assistant. See the activation audit and retained
attempt history. Full optional feature/dependency licensing and vulnerability
assessment remain separate. Public model/engine binaries are not redistributed
in Git; source notices and pinned license URLs identify their terms.
