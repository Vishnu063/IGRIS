# Mac Lima download trust repair

Follow-up: actual owner output at `5b0407d` confirmed both archive checks and successful native Lima installation. A later native VZ guest boot also passed. The earlier retry requirement below is historical; do not install/configure again. Continue with the [VM policy inspection/correction gate](mac-vm-policy.md). Assistant/kernel/inference/voice acceptance is still pending.

Date: 2026-11-18 IST. Tested implementation: `2205149d4f150cc721078eef00b4d98bf7c16601`. Overall native installation remains **BLOCKED pending owner retry**, not complete.

Owner terminal output establishes that the exact `e6ff965` review worktree and private Mac configuration were created successfully. The first Lima download then raised Python `SSLCertVerificationError: unable to get local issuer certificate`. No archive was accepted and no VM/assistant was started by these commands. The underlying Python CA-bundle/proxy configuration has not been independently inspected; no global certificate changes are necessary for this repair.

The native installer now explicitly selects `/usr/bin/curl`, using macOS's system trust configuration instead of the Python framework's trust store. Curl configuration files are disabled so they cannot silently introduce insecure flags. Certificate checks remain enabled; initial URLs and redirects must use HTTPS; credential-bearing URLs are rejected. Downloads have independent byte/deadline bounds, SHA-256 checks and owned-process cleanup. No TLS bypass, global Python/certifi install, Homebrew or Keychain modification is performed.

Lima archives are extracted into a private staging directory. Both downloads/extractions must succeed before the new installation directory is created. A second-download failure therefore preserves configuration/user files and leaves no partial Lima installation. Existing installation directories still refuse overwrite. The three configured manifest files match the owner's recorded hashes exactly; **do not repeat configure**.

Validation:

- PASS: 320 tests, zero failures/skips, in 25.694 seconds in the working checkout and 25.896 seconds in a separate clean checkout at the implementation commit.
- PASS: native-transport selection, Python HTTPS compatibility, checksum mismatch, unsafe URLs, cache preservation, streamed-size rejection, TLS-failure exit and real fixture-process deadline/reaping tests. Native platform/device behavior is simulated only where labelled; no Mac execution is claimed.
- PASS: real Linux system-curl HTTPS transfer of the authoritative 31,792-byte Linux header with matching SHA-256, and a real redirected Lima SHA256SUMS transfer with its pinned hash. These are Linux transport checks, not proof of Mac trust or software installation.
- BLOCKED: the earlier full release-archive probe reached its configured 180-second deadline. It was not recorded as a successful transfer. Native Mac archive download/version execution still needs the owner's output.
- PASS: source/index credential scanning, CI/delivery/provenance and diff whitespace. An initially literal synthetic credential-URL fixture triggered scanning; it was constructed from components instead, preserving the same rejection test without weakening scanning.

Commands:

```sh
python3 -m unittest discover -s tests -p test_asset_download.py -v
python3 -m unittest discover -s tests -p test_mac_archive.py -v
python3 -m unittest discover -s tests -q
python3 scripts/check_ci.py
python3 scripts/check_delivery.py
PYTHONPATH=src python3 -m igris.guardian.scan
git diff --check
```

Files: `scripts/fetch_hermes_probe_assets.py`, `scripts/mac_vm.py`, `tests/test_asset_download.py`, `tests/test_mac_archive.py`; accompanying operator guide/progress and [transport evidence](../validation/mac-tls-retry.json). Existing asset pins, configured manifest files, Guardian, resource gates and quarantine are unchanged. No model/VM was launched during this repair.

Next: fetch the updated feature branch into the existing Mac review worktree, fast-forward to the delivered exact SHA and retry only `install-lima --allow-changes --allow-downloads`. Return non-secret output. Do not recreate the worktree or configure again. Native VM/kernel, real inference and human voice acceptance remain separate later gates.
