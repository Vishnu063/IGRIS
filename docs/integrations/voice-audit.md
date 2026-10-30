# VoiceStudio audit — Step 31

Read-only source review, revision 4e61c2782d51df5488b390699d2faa98be677090 of
[Vishnu063/VoiceStudio](https://github.com/Vishnu063/VoiceStudio/tree/4e61c2782d51df5488b390699d2faa98be677090).
Sources: README.md (925c322ee639542219605516a22e42d561b81c0f), backend/main.py
(8f582944fada174e16350fc3bb72030c1d6afc52), package.json
(41bfb4417272f3ef671c358e220e8744eae7d8f6), pyproject.toml, LICENSE,
LICENSE-NOTICE.md (f4bb1ac68a4f6e55d2923c129b876dc624b36ea3),
docs/install/macos.md (c1fa23ab6fc3ec2a1e1a595350d50ee90fa92e6b),
docs/engines/disk-usage.md (291cd0dbfde8a58561d075e10e08a40a6ad2aa27),
docs/api-auth.md (66fb39cb90ae401ab515caa0d57c5c5d645723d6), and
speech-platform.md (753c4a1ac56a15f205265b045b0b5740bc2485ee).
A guessed docs/api.md path returned 404; actual API/auth documentation above was
located via README and source directory listings. No capability was inferred
from the nonexistent file. Repository/configuration were not modified.

Upstream claims macOS 13.3+ Apple Silicon with MPS/MLX, minimum 8 GB RAM and
10 GB free disk, recommended 16 GB+ RAM and 20 GB+ SSD. These are upstream
requirements, not measurements on the owner's M1. On an 8 GB machine, the stated
minimum leaves little headroom for macOS, Hermes and a browser. Do not install
the default stack or keep several engines warm without measurement. First launch
can bootstrap dependencies and download roughly 2.4 GB of model weights; optional
sidecars may add gigabytes. No installer, model download or runtime import ran.

README distinguishes 16 TTS and 11 ASR options, engine-dependent language support
and a catalogue of 646 languages. A catalogue entry is not tested speech quality.
MLX Whisper targets Apple Silicon; low-power options have narrower language scope.
No engine was selected or claimed to support English/Hindi/Marathi here.

Documented local API: speech/transcriptions under /v1/audio, discovery at
/.well-known/voicestudio-speech, backend loopback port 3900. Native dictation
control on 3902 owns microphone start/stop and insertion. Local API is deliberately
ungated for loopback callers; remote gates differ for HTTP/WebSocket/admin.
Do not treat loopback as authentication or expose these interfaces publicly.
No microphone, sidecar, HTTP server or VoiceStudio service is connected to IGRIS.
backend/main.py performs startup/environment initialization; static review does
not justify importing it in the IGRIS controller process.

Application license is AGPL-3.0-only, with model/dependency licenses separate.
Modified network-served distributions can carry corresponding-source obligations;
review distribution terms before embedding code. VoiceStudio code is NOT copied
into IGRIS by this step. The user's requested reuse covers Hermes and Agency
Agents; those MIT copies remain separate. No paid commercial license is activated.

Result: audit complete. API connectivity, engine/model licenses, real multilingual
speech, physical microphone behavior, memory footprint and M1 compatibility remain
PENDING_EXTERNAL_VERIFICATION. Steps 32–35 implement/test interface logic only.
