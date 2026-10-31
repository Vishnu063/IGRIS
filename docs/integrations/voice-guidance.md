# Voice integration handover

Audit: docs/integrations/voice-audit.md pins the actual VoiceStudio revision and
evidence. Nothing was installed or copied from VoiceStudio into a runtime. Its
AGPL-3.0-only license and model-specific licenses need review before reuse.

Implemented local pieces: language-route hints for English/Devanagari/mixed text,
explicit Hindi/Marathi preference to resolve shared-script ambiguity, push-to-talk
state/permission/deadline logic, licensed/original voice-style specification and
five filtered randomized greetings. Security claims are suppressed unless trusted
health probes establish them. No probe currently establishes all systems secure.
Quiet notification filtering is in igris.notifications.

Speech recognition, synthesis, translation, microphone capture and actual playback
are not connected. Text routing is not full language support. Romanized inputs
and shared Hindi/Marathi script can require confirmation. Push-to-talk tests use
a backend double; a real UI event loop must call the deadline check, show the
recording indicator, stop reliably and handle OS permission/crash errors.

Later integration must select a source-verified engine interface, privately
authenticated loopback transport, supported Apple Silicon runtime, voice/model
license and measured resource budget. Engine catalogue language counts are not
recognition-quality evidence. Test all requested languages with actual recordings
and original/properly licensed deep, calm, authoritative speech. Never send
sensitive audio/transcripts to an unknown-cost external provider or start capture
from an autonomous model instruction. See docs/delivery/mac-plan.md.
