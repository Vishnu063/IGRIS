# Optional Handy input

Reviewed upstream MIT source at `cjpais/Handy` tag v0.9.8, commit
`14f6f0d31cb22a4268acfbddba3052820fd0a06e`. Reviewed cli.rs, lib.rs,
managers/model.rs, transcribe.rs and tauri.conf.json. Its documented headless
`--transcribe-file FILE --model small --json` interface accepts 16 kHz mono
16-bit PCM WAV. It bypasses microphone, tray, shortcuts and clipboard insertion.
IGRIS uses this public interface, never accessibility or keyboard interception.
The upstream JSON contains timings and text, **no detected language**.

The Linux release needs GTK/WebKit even in headless mode. It runs with a private
virtual display inside a non-root, read-only, network-disabled container. This
is larger than a bare Whisper library; measure Mac deployment separately.
No model worker receives state, approvals, credentials, microphone devices or
Docker socket. Only one audio snapshot, the checked model and fixed worker are
mounted read-only. CPU/RAM/PID/output/time limits and owned-container cleanup
apply. The same global slot serializes ASR and Hermes. Root on the host and
same-user parent-process modification remain outside this isolation claim.

Whisper Small is multilingual (catalogue includes en/hi/mr), MIT weights;
model checksum and exact upstream release package checksum are pinned in
`integrations/handy/profile.json`. The original blob.handy.computer download
returned HTTP 403 / Cloudflare 1010. The official whisper.cpp Hugging Face mirror
serves the exact same checksum at a pinned revision. Downloads retain TLS and
proxy policy. Optional assets stay ignored under runtime/handy, never Git.

Manual preparation on the authorized Linux development machine:

$ python3 scripts/fetch_handy_assets.py

Build the Dockerfile explicitly with only the reviewed package in its context,
pin the resulting installed image ID in the profile, then import an owner-approved
WAV into a private directory (0700), file 0600. No automatic download/start occurs
on import. Audio must be at most 30 seconds / 1 MiB; paths, symlinks, hardlinks,
public permissions, incorrect encoding and truncated frames fail closed.

$ PYTHONPATH=src python3 -m igris.voice --remember --audio-workspace runtime/handy/audio --file sample.wav

Use --tools-config with the existing restricted Guardian profile to enable tool
proposals. --interactive-approvals still reads **only the controlling terminal**;
transcription can never approve an action. Chat memory remains owner-scoped SQLite.
Voice is never an autostart service. Imported audio is preserved; temporary
microphone recordings and worker snapshots are deleted after use/cancellation.

The optional ManualCapture backend lazily imports sounddevice only after manual
start plus --allow-microphone. It is **not installed or hardware-verified** here.
OS permission denial, missing audio package/device and cancellation return text
fallback. No physical microphone or Mac was accessed. A later Mac package must
pin and test native audio dependencies before claiming usable physical input.

$ PYTHONPATH=src python3 -m igris.chat --remember

Tests using callback fixtures do not prove hardware capture. A synthetic WAV
transcribed by actual Handy proves the file interface, not natural-speech quality.
