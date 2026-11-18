# Native Mac VM boot and forwarding policy correction

Date: 2026-11-18 IST. **Overall assistant acceptance: BLOCKED.** Tested final source: `a218f618015160ab4f9c6a93e1162dcb0bdd7fb3`; policy implementation: `6388f331c3a0dae1e3218924114ba87e15d04664`. [Evidence](../validation/mac-vm-policy.json) distinguishes owner terminal output, cloud verification and simulated Lima responses.

The owner updated the review checkout to `5b0407dd8f835a71dd28b97e72fbd0ea4d406b21`. Both pinned Lima 2.3.0 archives passed integrity validation and the native installer returned successfully, including its exact version check. The subsequent native VZ/aarch64 boot completed all five readiness gates. The pinned Ubuntu ARM64 image downloaded and the dedicated disk expanded to 24 GiB. These are actual owner-supplied terminal results; the agent has no remote Mac access. No inference, Guardian kernel receipt, guest bootstrap, microphone or playback result has yet been supplied.

## Findings and implementation

The boot log exposed an unrequested UDP 5353 forward from wildcard guest listeners to **host loopback**, not evidence of a public host listener. Lima 2.3.0's `FillPortForwardDefaults` defaults an omitted `guestIP` to `127.0.0.1` and omitted `proto` to `any`. Its `forwardingAddresses` function deliberately skips a loopback-specific ignore rule for wildcard guest listeners. The appended automatic fallback therefore forwarded mDNS. This is an address-matching defect in our original configuration, not a TCP-only default. The source references and exact upstream Git blobs are recorded in the evidence.

The packaged policy now specifies TCP only for the dashboard and an explicit any-protocol ignore rule with `guestIP: 0.0.0.0` and `guestIPMustBeZero: false`. This covers unspecified and specific guest interfaces. The deprecated Rosetta section was replaced by `vmOpts.vz.rosetta`, with both flags explicitly false. Validation inspects these effective flags, exact dashboard ranges, catch-all forwarding and absence of socket/reverse/static forwards and host block devices. The warning alone did not establish that emulation was enabled.

The new owner-only `inspect-vm` command prints finite policy fields and an instance-config hash; it omits environment variables, proxy configuration, credentials, paths and keys. It does not run guest commands. The old reviewed configuration remains eligible only for inspection, stopping and an explicit `migrate-vm --allow-changes` operation. All normal startup/bootstrap paths require the corrected configuration.

Migration recognizes only the exact original shipped YAML, preserves private snapshots, stops the dedicated profile and uses upstream `limactl edit --tty=false --set` with one fixed expression. It compares the entire before/after effective configuration, permits only the intended changes and updates the preparation manifest. It leaves the VM stopped. Unknown YAML, concurrent changes or partial/interrupted work block continuation. Failure attempts bounded cleanup of this pinned private profile and checks its stopped state; unknown cleanup is reported as unverified. It never replaces a VM disk, creates a profile, restores authority, starts a model, installs a guest package or automatically retries a partial migration. An owner-modified or Lima-normalized YAML requires actual inspection before a further migration is authorized by the code.

## Verification

- **PASS:** 331 tests, zero failures/skips, 25.745 seconds on Linux x86_64/Python 3.12.14. Focused Mac packaging tests: 19 in 0.079 seconds. This turn's full suite was not replayed in a separate clean checkout; the earlier 320-test clean result belongs to its earlier source commit.
- **PASS:** source/index credential scan, CI structure, delivery/provenance and diff whitespace checks.
- **PASS (real disposable files):** symlink/hardlink/write-permission/size rejection, private snapshots, unknown-file preservation, manifest gating, original disk and owner-note sentinel preservation.
- **PASS (simulated Lima responses):** effective Rosetta rejection, forwarding tamper rejection, explicit stop/edit order, no restart, idempotent completed migration, failed edit, interruption, exact effective-config comparison and startup denial after partial failure. These fixtures are not native VM or socket-forwarding acceptance.
- **BLOCKED:** additional Linux Lima CLI probe: one slow transfer was interrupted and a bounded retry timed out after 30 seconds. Task-owned partial files were cleaned. No CLI, VM or live socket-forwarding success is claimed for that probe.
- **NOT TESTED:** actual Mac effective-config inspection, migration, absence of subsequent 5353 forwarding, host resources after stop, guest ARM64 kernel/runtime/inference, human voice and playback.

Commands executed in the cloud:

```sh
python3 -m unittest discover -s tests -p 'test_mac*.py' -q
python3 -m unittest discover -s tests -q
python3 -m compileall -q scripts/mac_package.py scripts/mac_vm.py scripts/mac_vm_policy.py tests/test_mac_vm_policy.py
python3 scripts/check_ci.py
python3 scripts/check_delivery.py
PYTHONPATH=src python3 -m igris.guardian.scan
git diff --check
```

An initial focused test failed because its original instance fixture represented only deprecated Rosetta fields and unnormalized ranges. The fixture was updated to the reviewed Lima effective schema, and the original configuration is now separately tested as denied. An initial direct class import duplicated four discovered tests; importing its module removed duplication before the final 331-test run. The setup CLI also loaded its entry module twice when a helper imported it, yielding distinct exception classes. A single entry-module alias and actual subprocess test now ensure helper denials return concise BLOCKED/exit 2 without a traceback. No test was skipped or security check weakened.

Files: `packaging/macos/lima.yaml`, immutable original `packaging/macos/migrations/lima-v1.yaml`, `scripts/mac_package.py`, `scripts/mac_vm.py`, new `scripts/mac_vm_policy.py`, `tests/test_mac_archive.py`, new `tests/test_mac_vm_policy.py`, this report/evidence and the guide/progress updates.

## Security limits and next action

Guardian and native model tools were not broadened. No n8n/runtime/model/account or production action was enabled. The migration is a trusted owner setup command, not an AI tool. Same-user/admin configuration, executable or database tampering is not independently prevented by these local manifests; no claim of full sandboxing is made. The ordinary native receipt and actual resource enforcement gates still apply.

Next: update the existing Mac review checkout, obtain sanitized `inspect-vm` output, and stop only the dedicated profile while awaiting review. Apply the migration only after the real configuration is recognized. Then boot and confirm the corrected forwarding policy before guest package/runtime preparation. No repeated configure/install-lima is needed. Mac execution is required for this next gate; repository development and normal feature-branch pushes remain authorized. Native assistant and human voice acceptance are still BLOCKED.
