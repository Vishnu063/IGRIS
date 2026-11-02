# Completion integration and acceptance matrix

Evidence labels distinguish actual runtime execution, prior live acceptance, fixtures and unavailable hardware. Existing task reports retain their original source/version evidence. Automated owner inputs are trusted test fixtures, not AI approval.

| Capability | Actual evidence and limits | Record |
| --- | --- | --- |
| Hermes chat and controller | Live final verification | [final-guardian-live.json](final-guardian-live.json) |
| Conversation persistence and data-only recovery | Live final verification; old approvals not restored | [chat-backup-live.json](chat-backup-live.json) |
| Guardian tools, exact approvals and prompt-injection boundary | Live final verification, 24 sanitized audit rows | [final-guardian-live.json](final-guardian-live.json) |
| Handy file transcription | Real Task 2 synthetic-audio acceptance; current cloud image archived/storage blocked; physical microphone blocked | [handy-live.json](handy-live.json) |
| English/Hindi/Marathi speech | Actual Task 3 local WAV synthesis/greetings; human ASR quality, automatic spoken LID and Mac playback unverified | [multilingual-voice-live.json](multilingual-voice-live.json) |
| n8n | BLOCKED: previously real Task 4 workflow now quarantined after dependency audit | [n8n-quarantine-live.json](n8n-quarantine-live.json) |
| Ops Pilot | Live final read-only monitoring of one disposable Docker app; remediation disabled | [final-ops-live.json](final-ops-live.json) |
| 15 specialists | 15 distinct real scoped Task 6 tasks; one final frontend replay passed; advisory quality limited | [specialists-live.json](specialists-live.json) |
| Mission Control | Real Task 7 chat/tools and current authenticated mobile layout, approvals and Mem0 UI; n8n shown blocked | [final-dashboard-layout.json](final-dashboard-layout.json) |
| Mem0 | Real Task 8 semantic retrieval; current owner-approved UI indexing and rejected deletion verified | [final-mem0-dashboard-live.json](final-mem0-dashboard-live.json) |
| Playwright | Live final owned-site inspection/screenshot, forbidden requests and cancellation; no general browsing | [final-playwright-live.json](final-playwright-live.json) |
| MarkItDown | Real Task 10 five-format fixture conversion and actual Hermes summary; no OCR | [markitdown-live.json](markitdown-live.json) |
| Pydantic AI | Real source/validation evaluation; intentionally not integrated | [pydantic-ai-evaluation.json](pydantic-ai-evaluation.json) |
| Warm inference | Real Task 12 cold/warm measurements and final signed transport tests; default stays one-shot | [warm-protocol-live.json](warm-protocol-live.json) |
| Mac M1 | BLOCKED: configuration preparation tested, no hardware/ARM64 execution | [mac-package-cloud.json](mac-package-cloud.json) |
| Emergency stop | Current actual worker cancellation/removal, plus dashboard stop/CSRF/replay regression tests | [final-cancel-live.json](final-cancel-live.json) |

Regression unit tests include explicit mock/fixed adapters where named; those are not counted as live connectivity. The real Guardian timeout test injects a short deadline but runs and kills an actual broker process. No external user account, customer/production service, human microphone recording or target Mac was used. Hosted GitHub Actions were not dispatched.
