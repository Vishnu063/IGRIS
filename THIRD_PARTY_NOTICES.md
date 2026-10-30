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

The active lightweight IGRIS `src` runtime uses Python's standard library. The
uninstalled copied Hermes source lists its own separate dependencies and may
refer to third-party services/models with additional licenses and costs. Those
dependencies and their vulnerabilities/licenses have not been fully resolved.
Model weights, voice rights, trademarks, hosted services and client data are not
licensed by inclusion of these notices. No paid or production use is activated.
