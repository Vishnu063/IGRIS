# Apple M1 preparation package — hardware acceptance BLOCKED

No Mac was accessed, modified or installed. This is a reviewed **preparation package**, not a working ARM64 IGRIS release. Existing live evidence is Linux x86_64. The current Guardian kernel filter and worker preflight intentionally reject ARM64; changing platform strings or using x86 emulation would not verify the required security boundary.

## What is prepared

A standard-library native Python utility creates only private manifest-listed configuration files after a separate future owner authorization. It refuses existing destinations and modified files. A dedicated Lima 2.2.1 profile specifies Apple VZ, aarch64, two CPUs, estimated 4 GiB RAM and sparse 16 GiB disk. It does not inherit a default template: host mounts are explicitly empty, no Docker socket is forwarded, all ports except the planned authenticated loopback dashboard are ignored, and no provisioning/autostart scripts run. `LIMA_HOME` is scoped only to the invoked child process under the IGRIS preparation directory. Existing Lima/Colima profiles and global Docker context are untouched.

The asset manifest pins actual native macOS/Linux ARM64 Python 3.14.9, llama.cpp b11960 CPU archives and Handy 0.9.8 aarch64 DMG checksums. Ubuntu's dated ARM64 VM image has a pinned digest. These are download **candidates, not executed binaries**; none was downloaded or installed on a Mac. Do not use the Linux x86_64 environments, container IDs, wheel locks or `.so` files on ARM64. The review-only AArch64 syscall table is disabled and is not installed into Guardian.

## Future owner-authorized preparation

The following commands are instructions for a later Mac session with explicit permission. They were not run on the target machine. First review the release limitations and retain backups. Existing native Python >=3.11 and an explicitly reviewed Lima 2.2.1 installation are required; no Homebrew or package installation is automatic.

```sh
$ python3 scripts/mac_package.py plan
$ python3 scripts/mac_package.py preflight
$ python3 scripts/mac_package.py configure --allow-changes
$ python3 scripts/mac_package.py start-vm --allow-changes
$ python3 scripts/mac_package.py stop-vm --allow-changes
$ python3 scripts/mac_package.py uninstall --allow-changes
```

`preflight` reports BLOCKED until actual acceptance is completed. `start-vm` prepares an otherwise unprovisioned guest, **not IGRIS**; it can download the pinned VM image and allocate the estimated resources, so use it only after the later explicit authorization. `start` remains fail-closed and cannot be unlocked by editing a manifest. Configuration lives under `~/Library/Application Support/IGRIS`. Uninstall removes only unchanged manifest-listed preparation files, preserves unrelated user files and refuses to remove control files while VM state exists. Stop and back up the dedicated VM before any later owner-approved VM deletion. No recursive deletion or modification of other applications is scripted.

## Exact remaining implementation/hardware gates

1. Authorized M1 access; macOS version, 8 GiB memory, available storage, VZ permissions and Lima schema/runtime validation. Linux YAML parsing is only a syntax check.
2. A reviewed native ARM64 Docker worker image and architecture-specific dependency locks. The candidate VM intentionally installs no Docker daemon or packages. Transfer only reviewed source/assets into the guest through an explicitly approved mechanism; no home sharing workaround.
3. Verify the AArch64 syscall numbers against guest headers, implement its architecture check, and run real denied network/process/io_uring probes before enabling Guardian. Run real tool/approval, replay, containment and emergency-stop tests inside that guest. The disabled table alone is not enforcement.
4. Run the actual ARM64 llama/Python/Hermes assets, retain context and integrity checks, measure inference and peak total VM/native RAM, swap and thermals. Only then review enabling an ARM64 runtime profile in source.
5. Native Handy headless file transcription, explicit microphone start/stop and OS permission denial. Use multilingual Whisper Small; no global shortcut/accessibility/clipboard capture. Delete temporary WAV files by default. The existing verified Handy adapter is Linux-only; a native adapter still needs implementation and verification on the Mac.
6. Inspect installed licensed Mac voices with the OS voice list. Do not download voices automatically. English/Hindi/Marathi synthesis/playback and licensed human speech recognition need separate native-speaker acceptance. eSpeak NG is the low-memory local fallback with disclosed formant quality; no actor cloning. The five security-filtered greetings already exist in source but Mac playback is untested.
7. Native browser Mission Control can use the planned loopback forward only after authenticated backend startup is verified. Keep credentials private; approvals come from owner controls, never transcripts. Test logout, stop, cancellation and no startup at login/reboot.

## Resource estimates — unverified on M1

The Linux model has reached about 2.74 GiB RSS; VM limit starts at 4 GiB, leaving the other 4 GiB nominally for macOS, native interface and on-demand speech. Memory is shared and this is not proof it fits without swap. Model disk 1.28 GB, multilingual ASR weights about 465 MB; Python/dependencies, guest OS and caches add several GB. Plan 10–20 GB initial working space with a 16 GiB sparse guest disk; about 50 GB available should leave headroom but must be measured. Run one heavy optional service at a time, keep n8n/browser/semantic indexing disabled until needed, and retain the zero-spending policy. Do not enable login items, background capture or automatic service restarts.
