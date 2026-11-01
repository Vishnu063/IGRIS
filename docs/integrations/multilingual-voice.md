# Manual multilingual voice: tested scope and gaps

Handy v0.9.8 exposes text and timings but no language metadata. Its multilingual
Whisper Small catalogue includes English, Hindi and Marathi; catalogue support
is not recognition-quality evidence. The existing script router is reused.
`language_review` labels script guesses low confidence and requests explicit
selection. Hindi and Marathi share Devanagari; Romanized conversation is also
ambiguous. No calibrated automatic spoken-language detector is claimed.

Select --language en, hi or mr to request a reply in that language. The model
instruction guides language only; it grants no tool authority. Guardian remains
the actual execution boundary. Finalized transcription never becomes approval.
Handy's file pipeline was verified with synthetic English speech in Task 2;
Hindi/Marathi human recognition, command preservation and mixed speech remain
unverified. FLEURS preview requests for all three languages returned HTTP 501;
no substitute fabricated recordings or quality scores were used.

The optional eSpeak NG 1.51+dfsg-12build1 formant synthesizer generated real PCM
WAVs for all three languages inside a pinned, offline, non-root container.
Reviewed upstream 1.51 README, command source and GPLv3 COPYING. It is free local
software, GPL-3.0-or-later, not an actor clone. Dependencies retain their packaged
copyright/source notices. No binary or model weight is committed. Redistribution
must preserve applicable notices and corresponding-source obligations.

Delivery rate 150 and pitch 35 target a measured, lower speaking style. This is a
robotic low-memory fallback, not verified natural/professional voice quality.
Installed native Mac voices are preferred for later authorized Mac testing;
no Mac voice API or physical speaker was accessed here.

The worker accepts at most 240 plain characters and produces at most 30 seconds /
1.5 MB WAV. Markup, phoneme brackets and controls are rejected. Text travels via
bounded stdin JSON to the worker, then a private fixed UTF-8 text file to eSpeak;
there is no shell, SSML, model-selected voice identifier or arbitrary file path.
CPU, RAM, PID, wall-clock and file limits apply. Only the speech profile permits
up to 2 MiB transport output for base64 audio. The original three-tool Guardian
broker and its execution restrictions are unchanged.

A failed attempt revealed PulseAudio initialization requesting a 64 MiB memfd,
hitting the existing 2 MiB file limit before synthesis. An unprivileged trace
confirmed ftruncate/EFBIG/SIGXFSZ. The fixed worker disables Pulse autospawn and
shared memory in a private client config and retains the original limit. No
host audio socket/device, network, approval database or credential is mounted.

All five existing startup greetings remain registered. Security-status claims
are filtered by trusted verification flags; --greeting uses the conservative
unverified state. It runs only on an explicit CLI launch/flag, not login/startup.
With --speak it generates an eligible greeting WAV. It does not claim playback.

$ PYTHONPATH=src python3 -m igris.voice --remember --audio-workspace runtime/handy/audio --file sample.wav --language en --speak --speech-directory runtime/speech/audio --greeting

This requires the explicitly prepared Handy image. For storage safety its tested
image was archived to a task-owned checksum-verified temporary archive and removed
from Docker after Task 2. runtime/handy/archive.json identifies that cache. It is
not a portable installation asset or evidence of current microphone readiness.
The VFS storage driver needs substantial image-copy space; restore/rebuild only
after checking free disk, and verify the exact image ID. Original Hermes assets
were preserved. The speech image remains installed; both features default off.

--mute suppresses speech; --mute-microphone rejects recording. The capture API
also supports mute/stop/cancel, with no automatic resume after unmute. Ctrl+C
cancels the owned worker and runs all cleanup callbacks even if microphone stop
fails. Generated microphone audio is deleted; explicitly requested speech WAVs
remain private until owner deletion. No playback process auto-starts.

$ python3 -m unittest discover -s tests -p test_speech.py -q
$ PYTHONPATH=src python3 scripts/test_speech_live.py
$ PYTHONPATH=src python3 scripts/measure_speech_live.py

Evidence in docs/validation records actual WAV hashes, model replies and measured
Linux timing/RSS. RSS high-water values include the pre-exec Python baseline;
they are not total container peak memory or Mac measurements. The end-to-end
human microphone -> recognition -> answer -> audible playback acceptance is
**BLOCKED**, as are native-speaker quality and actual M1 resource validation.
