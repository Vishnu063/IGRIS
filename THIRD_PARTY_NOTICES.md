# Third-party source notices

IGRIS-specific code has no project-wide license grant selected in this repository.
Do not infer that upstream MIT licenses grant rights over all IGRIS-specific work.

- Hermes Agent, Nous Research and contributors: copied curated backend source
  subset under `vendor/hermes-agent`; its MIT license is preserved at
  `vendor/hermes-agent/LICENSE`. Pinned revision and original/local hashes,
  including IGRIS changes, are in `docs/integrations/hermes-source-manifest.json`.
  This is not the complete upstream distribution or an installed runtime.
- Agency Agents, upstream copyright holders/contributors: 15 verbatim selected
  definitions in `vendor/agency-agents`; its MIT license is preserved there.
  Adaptations under `integrations/agency-agents` retain attribution/provenance
  headers and methodology. The manifest maps originals, adaptations and hashes.
- Ops Pilot, VoiceStudio and the 20 assessed business tools were reviewed by
  read-only source/document inspection. They were not installed or copied as
  runtime dependencies. Short license excerpts in assessment evidence retain
  their source references; full terms and edition restrictions require review
  before integration. In particular VoiceStudio is AGPL-3.0-only, not MIT.

The default lightweight IGRIS `src` runtime uses Python's standard library.
The separate manual inference profile installs 53 hash-locked Python dependencies
under ignored runtime/, and runs the copied Hermes source in an offline container.
It uses llama.cpp b11960 (MIT, notice retained with the downloaded binary) and
Qwen3.5-2B Q4_K_M weights (Apache-2.0, original Qwen model plus public Unsloth
quantization). Exact repositories, revisions and hashes are recorded in
integrations/hermes-inference/profile.json. Original model license:
https://huggingface.co/Qwen/Qwen3.5-2B/blob/15852e8c16360a2fea060d615a32b45270f8a8fc/LICENSE.
The runtime downloads are not redistributed in Git. Each installed dependency
retains its own distribution license; a complete vulnerability/license audit is
not claimed. The remaining copied Hermes features refer to other optional
dependencies/services/models, which are not enabled by this profile.
Model weights, voice rights, trademarks, hosted services and client data are not
licensed by inclusion of these notices. No paid or production use is activated.

## Completion-plan optional runtime additions

These optional dependencies are not part of the standard-library core and no binary/model is committed. Keep upstream license files with any separately redistributed installation. The [license audit](docs/validation/license-audit.json) records metadata limitations and unresolved custom/unknown entries; it is not a blanket redistribution clearance.

- Mem0 2.2.1: Apache-2.0; MiniLM/Qdrant ONNX model: Apache-2.0; ONNX Runtime MIT. Local extraction is disabled, with no paid provider configured.
- Playwright 1.62.0: Apache-2.0; managed Chromium has BSD and many bundled third-party notices; Bubblewrap LGPL-2.0-or-later. No browser binary is redistributed in Git.
- Microsoft MarkItDown 0.1.9: MIT; Office/PDF/HTML dependencies retain their individual notices.
- Pydantic AI 2.64.0: MIT, inspected as a source wheel only and intentionally not integrated. Standalone Pydantic was used only for development evaluation.
- Handy 0.9.8 and Whisper weights: MIT; eSpeak NG 1.51: GPL-3.0-or-later. No actor voice cloning or model relicensing. Native Mac/audio acceptance is blocked.
- Lima 2.2.1: Apache-2.0; ARM64 candidates are metadata pins, not executed/distributed Mac binaries. CPython uses PSF licensing and llama.cpp MIT; Qwen3.5-2B weights retain Apache-2.0.
- n8n 2.45.7: Sustainable Use License plus differently licensed components, including enterprise packages not enabled by IGRIS. The current runtime is quarantined after dependency audit; no unrestricted commercial redistribution eligibility or paid features are claimed.
