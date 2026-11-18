# Native M1 setup and acceptance

Status: **prepared, not installed or verified on the owner's Mac**. Do not run all sections at once. First review the draft PR and execute only the next requested gate, then return its non-secret output. Historical Linux results do not establish ARM64, microphone or playback acceptance. Current evidence and exact commits are in [the readiness report](../execution/mac-readiness.md).

The owner reports an ARM64 MacBook Air with 8 GB RAM, virtualization support, Python 3.12.10 and about 149 GiB free. The reported macOS version/build remain owner observations, not independently verified facts. No Mac installation was performed remotely.

## 1. Private preparation and Lima

Use a separate Git worktree so existing `~/IGRIS` files and branch remain intact. The final delivery supplies its exact reviewed SHA. An existing worktree/preparation directory is preserved; stop and inspect rather than deleting it or forcing replacement.

```sh
$ git -C "$HOME/IGRIS" fetch origin feat/mac-arm64-native-voice
$ git -C "$HOME/IGRIS" worktree add --detach "$HOME/IGRIS-mac-review" origin/feat/mac-arm64-native-voice
$ cd "$HOME/IGRIS-mac-review"
$ python3 scripts/mac_package.py configure --allow-changes
$ python3 scripts/mac_package.py install-lima --allow-changes --allow-downloads
```

Effects: create private manifest-listed control files and install official Lima **2.3.0** binaries under `~/Library/Application Support/IGRIS/lima`, after published SHA-256 validation. About 90 MB compressed / 153 MB expanded for the two Lima archives. No Homebrew, global PATH edit, VM/model download, microphone, login item or assistant startup. Installation follows the upstream [supported binary method](https://github.com/lima-vm/lima/blob/v2.3.0/website/content/en/docs/installation/_index.md), with explicit checksums and safe extraction instead of piping into tar. Actual Mac execution/Gatekeeper acceptance is pending; do not disable security controls if macOS rejects execution.

## 2. Dedicated Linux ARM64 VM (after Gate 1 output)

```sh
$ python3 scripts/mac_package.py start-vm --allow-changes
$ python3 scripts/mac_package.py bootstrap-guest --allow-changes --allow-downloads --commit "$(git rev-parse HEAD)"
$ python3 scripts/mac_package.py prepare-runtime --allow-changes --allow-downloads
```

Effects: download the pinned Ubuntu ARM64 image; create only the dedicated `igris` profile in private `LIMA_HOME`; allocate **two CPUs, 4 GiB RAM, sparse 24 GiB disk**; install signed distro packages inside that guest and clone the exact reviewed IGRIS commit. Home sharing, socket forwarding, Rosetta, SSH-agent/X11 forwarding, containerd autostart and arbitrary port forwarding are disabled. The only application forward is guest/host loopback port 8765. Existing global Lima profiles and host Docker contexts are untouched.

Guest Docker is explicitly started when required, never installed on the Mac. Its service/socket/containerd autostart is disabled. The wrapper uses a fresh Docker group context, avoiding stale SSH supplementary-group membership. Preparation downloads the existing 1.28 GB architecture-independent GGUF, pinned ARM64 Python/llama archives and hash-locked binary dependencies. It never downloads voice models. Artifact/header review is not execution acceptance. Unknown/partial pre-existing preparation is preserved for review, not silently overwritten.

The native profile requires actual target headers, irreversible syscall probes, ARM64 ELF binaries and image metadata, reviewed sources and real CPU/memory/PID cgroup enforcement. Missing prerequisites stop activation; no x86 emulation, context-check bypass or host fallback exists. Optional x86-only integrations remain unavailable on ARM until separately accepted.

## 3. Accounts, tools and actual guest acceptance

Keep this shell-local variable; it does not replace any system HOME variable:

```sh
$ IGRIS_CONTROL="$HOME/Library/Application Support/IGRIS"
$ env LIMA_HOME="$IGRIS_CONTROL/vm-state" "$IGRIS_CONTROL/lima/bin/limactl" shell igris sh -c 'cd IGRIS && python3 scripts/create_dashboard_accounts.py --output runtime/mission-control/accounts.json && python3 scripts/create_guardian_test_workspace.py --require-approvals'
$ python3 scripts/mac_package.py verify-guest --allow-changes
$ python3 scripts/mac_package.py export-accounts --allow-changes
```

The account/workspace helpers refuse to overwrite existing paths. They create random private owner/viewer credentials and an isolated demonstration workspace whose three tools require exact owner approval. Credentials are copied to a private host file for the native frontend; they are never sent to a model or printed. Inspect them locally for browser sign-in, and never paste that file into chat.

Verification runs the complete regression suite, source scan, real randomized restart/recall, Guardian attack matrix, data-only restore and authenticated HTTP chat/cancel/logout tests. It can take many minutes. A new run archives the old acceptance receipt before testing; failure never preserves old authority as a new PASS. Host verification records actual VM-process RSS and host swap; the guest records sampled memory/swap. SSH interruption stops only this identity-checked dedicated VM, preserving its disk. That cleanup behavior still needs actual Mac testing.

Evidence is private under guest `runtime/arm64/acceptance.json`, guest `runtime/mac-readiness/`, and host `IGRIS/host-measurements.json`. A receipt describes that exact source/kernel/image; it grants no tool approval. Source/kernel/runtime changes invalidate startup until verified. Guest tests alone do not prove host fit or human voice usability.

## 4. Manual startup, shutdown and measurement

```sh
$ python3 scripts/mac_package.py start --allow-changes
```

This explicitly starts the existing reviewed VM if stopped, starts guest Docker, refreshes kernel/header proof, checks the current acceptance receipt and runs the authenticated dashboard in the foreground. Open `http://127.0.0.1:8765`. Chat is persisted in private guest SQLite; tools remain independently Guardian-controlled. No optional n8n/browser/Ops service starts during chat. Closing this terminal with Ctrl+C stops the dedicated VM after the backend exits, releasing its host resources. The dashboard's Emergency stop cancels tracked work; Log out and stop revokes cached Basic credentials until a manual process restart. Neither action grants authority to another task.

From a second terminal while testing:

```sh
$ python3 scripts/mac_package.py measure
$ python3 scripts/mac_package.py stop-vm --allow-changes
```

Measurement reads current Lima-owned process RSS and total Mac swap; shared pages can be counted twice. Compare before/during/after runs; do not substitute historical Linux RSS. The explicit stop command affects only this private profile. No unrelated user processes or global profiles are killed. Evaluate measured memory pressure, swap growth and latency before accepting the 8 GB target; the resource estimates are not a fit guarantee.

## 5. Native voice and human acceptance

Keep the dashboard running in the first terminal. Apple Command Line Tools/Swift SDK must already exist; the build helper checks without triggering a toolchain installation. If missing, report that blocker and review the Apple installation separately. No SDK/voice model is downloaded automatically.

```sh
$ python3 scripts/build_mac_voice.py --allow-changes
$ PYTHONPATH=src python3 -m igris.voice.native --capabilities
```

The helper is locally compiled for ARM64 with explicit microphone/speech usage descriptions and ad-hoc signing. Capabilities only list available on-device recognition and OS voices; they do not activate the microphone or prove language quality. Recognition refuses cloud fallback. If Hindi/Marathi on-device recognition or a corresponding installed voice is unavailable, record the exact language as BLOCKED and use text. Do not silently download a model, install an app or claim automatic detection.

For each available language, manually test a short human request (only one at a time):

```sh
$ PYTHONPATH=src python3 -m igris.voice.native --accounts-file "$IGRIS_CONTROL/dashboard-accounts.json" --language en --record 5 --allow-microphone --speak --play --greeting
$ PYTHONPATH=src python3 -m igris.voice.native --accounts-file "$IGRIS_CONTROL/dashboard-accounts.json" --language hi --record 5 --allow-microphone --speak --play
$ PYTHONPATH=src python3 -m igris.voice.native --accounts-file "$IGRIS_CONTROL/dashboard-accounts.json" --language mr --record 5 --allow-microphone --speak --play
```

Press Enter to start; recording is indicated and bounded. Ctrl+C cancels recording/transcription/playback. `--mute-microphone` rejects recording, and `--mute` disables speech. Temporary audio is deleted after success/failure/cancellation; deletion is not a forensic secure-erase guarantee. The authenticated VM reservation prevents competing foreground inference while native input/output is active. Transcripts cannot approve actions; use the separate dashboard's exact review controls. Network uncertainty cancels the native helper and leaves no assumed authority.

Native synthesis uses existing licensed OS voices with calm rate/pitch, never actor cloning. The five existing status-filtered greetings are reused. File generation, player exit and audible speaker output are separate facts. Report whether each real human request was recognized correctly, the answer stayed in the selected language, and actual speaker pronunciation/clarity was usable. Explicit selection is the supported mode; automatic detection is NOT implemented or verified. OS speech daemons are not killed as IGRIS-owned resources; actual retained RAM needs host measurement.

Text fallback, with no microphone or helper launch:

```sh
$ PYTHONPATH=src python3 -m igris.voice.native --accounts-file "$IGRIS_CONTROL/dashboard-accounts.json" --language mr --text
```

## 6. Update, backup, restore and uninstall

Stop active work before changing source or backing up. For a guest update to the reviewed feature tip, first inspect status and stop if there are edits:

```sh
$ python3 scripts/mac_package.py start-vm --allow-changes
$ env LIMA_HOME="$IGRIS_CONTROL/vm-state" "$IGRIS_CONTROL/lima/bin/limactl" shell igris git -C IGRIS status --short
$ env LIMA_HOME="$IGRIS_CONTROL/vm-state" "$IGRIS_CONTROL/lima/bin/limactl" shell igris git -C IGRIS fetch origin feat/mac-arm64-native-voice
$ env LIMA_HOME="$IGRIS_CONTROL/vm-state" "$IGRIS_CONTROL/lima/bin/limactl" shell igris git -C IGRIS merge --ff-only FETCH_HEAD
$ python3 scripts/mac_package.py verify-guest --allow-changes
```

Update the guest only to an exact reviewed commit and preserve local edits: inspect status, fetch, then use a normal fast-forward update. Never reset, force checkout, merge main or overwrite an existing runtime/profile. Re-run guest verification after source/runtime/kernel updates. A changed pinned Lima/configuration requires a reviewed migration; the preservation checks intentionally block silent replacement.

The existing owner backup CLI is tested on Linux with real recall after restore. For a running dedicated VM and idle chat:

```sh
$ env LIMA_HOME="$IGRIS_CONTROL/vm-state" "$IGRIS_CONTROL/lima/bin/limactl" shell igris sh -c 'cd IGRIS && python3 scripts/backup_chat.py create --state-dir runtime/chat --file runtime/owner-backup.json --approve-data-operation'
$ IGRIS_BACKUP="$(mktemp "$IGRIS_CONTROL/backup.XXXXXXXX")"
$ env LIMA_HOME="$IGRIS_CONTROL/vm-state" "$IGRIS_CONTROL/lima/bin/limactl" cp igris:IGRIS/runtime/owner-backup.json "$IGRIS_BACKUP"
$ chmod 600 "$IGRIS_BACKUP"
$ shasum -a 256 "$IGRIS_BACKUP"
```

Use a new guest backup filename if one already exists. `mktemp` creates a new private host destination, preserving existing files. Validate its hash against the backup CLI output. Restore with `scripts/backup_chat.py restore --state-dir <NEW-ABSENT-DIRECTORY> --file <PRIVATE-SNAPSHOT> --expected-sha256 <VERIFIED-DIGEST> --approve-data-operation` inside the guest. The restore refuses existing state, imports data only and creates empty approval authority. Credentials, pending work and semantic indexes are not restored. Never replace an existing chat directory to make restoration succeed; inspect/use the new restored directory explicitly. Mac filesystem transport and end-to-end restore still require target verification.

Uninstall requires a verified backup first. Stop the dedicated VM; review and, only if you intend to erase its guest data, use the pinned Lima binary with this private `LIMA_HOME` to delete **only `igris`**, with its ordinary interactive confirmation. No script automatically deletes VM disks or backups. Then:

```sh
$ python3 scripts/mac_package.py uninstall-lima --allow-changes
$ python3 scripts/mac_package.py uninstall --allow-changes
```

The first removes only unchanged manifest-listed Lima files after confirming no profiles remain; unknown files are retained. The second removes preparation files only when no VM/Lima state remains, otherwise it preserves them and blocks. Private control history, exported credentials, backups and any unknown files may therefore remain for owner review. The native voice build lives only in this review checkout's ignored `runtime/native-voice`; retain anything you need before removing the owned review worktree. No unrelated applications, login items or global Docker settings were installed or removed. Native uninstall is prepared, not Mac-tested.
