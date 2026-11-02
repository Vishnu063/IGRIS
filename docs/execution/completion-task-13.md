IGRIS EXECUTION REPORT

Task: 13 / 14
Title: Mac M1 installation package
Status: BLOCKED

Recorded: 2026-11-02T06:25:03.995801+05:30

Implemented:

- Native standard-library Mac preparation/preflight/VM start-stop/manifest-uninstall utility; nothing installed on an actual Mac.
- Pinned native macOS and Linux ARM64 Python/llama candidates, Handy aarch64 DMG, dated ARM64 Ubuntu VM image and Lima 2.2.1.
- Dedicated estimated 4 GiB/two-CPU/16 GiB sparse Lima profile, empty mounts/provisioning, no daemon socket forwarding or global Docker-context changes; per-child private LIMA_HOME.
- Review-only disabled AArch64 syscall candidate and explicit assistant-start gate. Existing runtime/Guardian correctly remains x86_64-only.

Real versus simulated:

- Four real disposable Linux filesystem/configuration tests and actual Linux preflight rejection; YAML syntax parsed.
- No Mac, microphone, speaker, ARM64 binary, Lima VM or ARM64 Guardian execution tested. Candidate metadata/checksums are not compatibility proof.

Tests and results:

- 4 preparation tests PASS: manifest roundtrip, unlisted-user-file preservation, existing/modified/VM-state protection, Linux/x86 denial and no-autostart configuration.
- Actual Linux preflight returns BLOCKED exit 2 and performs no installation. Compile, YAML syntax and whitespace checks PASS.
- Read pinned Lima defaults source: defaults/overrides can merge mounts; fresh private home used and unreviewed override files refused. Real Lima behavior remains a hardware acceptance requirement.

Security review:

- No Mac mutation in cloud execution. No Homebrew, package/bootstrap, model download, provisioning, login item, microphone or service activation.
- No flag or editable approval marker can enable unverified ARM64 assistant execution. No silent x86 fallback.
- Uninstall removes only unchanged generated manifest entries; preserves user files and refuses VM-state deletion/control removal.

Performance:

- All target estimates UNVERIFIED: 4 GiB VM/two CPUs/16 GiB sparse disk; model 1.28 GB, ASR ~465 MB plus guest/dependencies.
- Linux model peak ~2.74 GiB is not proof of fit, swap behavior, thermals or speed on M1.

Known limitations:

- This is a preparation package, not a working native ARM64 installation. Assistant start intentionally BLOCKED.
- Need ARM64 container image/dependency locks, verified kernel policy, actual native Handy/audio adapter and guest bootstrap; no false ready-to-run assistant claim.

External requirements:

- Explicit later owner authorization and access to target M1 Mac.
- Real native ARM64 assets, Docker guest setup and Guardian syscall/isolation tests before enabling runtime.
- Physical microphone/speaker permissions, human English/Hindi/Marathi quality tests, measured RAM/disk/latency and safe shutdown.

Files changed:

- README.md
- docs/delivery/mac-package.md
- docs/delivery/mac-plan.md
- docs/validation/mac-package-cloud.json
- packaging/macos/assets.json
- packaging/macos/guardian-arm64-candidate.json
- packaging/macos/lima.yaml
- scripts/mac_package.py
- tests/test_mac_package.py

Commands executed:

$ python3 -m unittest discover -s tests -p test_mac_package.py -q
$ python3 scripts/mac_package.py plan
$ python3 scripts/mac_package.py preflight
$ python3 -m compileall -q scripts/mac_package.py
$ git diff --check

Git commit:

- Verified implementation: 484de1e9b2b1cc381e8a622f965307ffce3233b5
- This report is recorded in a following documentation commit; remote tip is checked after publication.

Git delivery:

Connected GitHub App publishes the exact staged tree using expected-head fast-forward; remote branch SHA is verified separately. Git CLI authentication unavailable.

Next task:

- 14

Approval required:

- No for authorized development/push. Mac access, production, main merge, paid services and new host privileges remain unauthorized.
