# Hermes Agent feasibility assessment — Step 11

Reviewed 30 October 2026 (Asia/Kolkata). Scope: static upstream documentation and
selected source, not installation, execution or a comprehensive security audit.
Hermes Agent is interpreted as NousResearch/hermes-agent; no similarly named
package is silently substituted.

## Evidence pinned to a revision

Upstream revision: `2d2808ee84549f9836b0056750265058e5488a8a`.
Every path below is relative to the
[pinned repository](https://github.com/NousResearch/hermes-agent/tree/2d2808ee84549f9836b0056750265058e5488a8a).

| Source path | Git blob SHA | Verified observation |
| --- | --- | --- |
| README.md | 1f5cfb9b49f78a09f94c04e12b38fec478dcc722 | CLI, gateway, model providers and multiple execution backends are documented |
| pyproject.toml | 83af45fb90b96b741f59b3bb33b89a63218d6dbb | Metadata range >=3.11,<3.15; comments clarify current runtime is 3.14; scripts include hermes and hermes-agent |
| LICENSE | 75410e73319c72cd3e991a501c5455eb78f38375 | MIT; retain notice when redistributing substantial upstream code |
| SECURITY.md | cea2a9a2e8869ac7a4b7307332b974a27e9fd27a | OS isolation is the adversarial boundary; plugins run with agent privileges |
| website/docs/getting-started/installation.md | bd1a6539237d9daa6924369790b2b4873329c661 | Managed Python 3.14, PM tool preparation, Apple Silicon macOS support claimed upstream |
| website/docs/developer-guide/architecture.md | 4d92e5c5668dc069c3fc904d4443373e1409ff2c | AIAgent in run_agent.py; Python library and API entry points documented |
| gateway/platforms/api_server.py | 90b020e8c5bfa21f8ad254f94dea19b6a9c53122 | Real API routes and Bearer authentication implementation inspected |
| website/docs/reference/cli-commands.md | baf1febbc5075d673e9b0d4de789ce5572a9d688 | One-shot/query-file CLI and headless serve commands documented |

Evidence fetched read-only with the GitHub connector. An oversized recursive-tree
lookup failed; selected pinned files were retrieved directly instead. No upstream
instructions, installers or code were executed or copied into IGRIS.

## Installation and compatibility

Current first-party runtime support is Python 3.14; the broader package metadata
range lets older installations run an updater, not a promise that current Hermes
runs under this workspace's Python 3.12.14. Do not import it into IGRIS's runtime.
Source installer prepares managed tools/dependencies and by default can download
Chromium and computer-use components. Optional extras/provider dependencies and
native libraries expand the footprint. Desktop adds Electron-related resources.
Do not run its installer, auto-updater, dependency preparation or setup here.

Upstream explicitly describes Apple Silicon macOS packages, but no M1 install,
8 GB memory suitability, disk footprint or real language engine was tested.
The Step 4 lightweight core estimate excludes Hermes. Keep a separate optional
process/host; no always-on full agent stack or local model is required by IGRIS.

## Verified interface candidates

- HTTP API source advertises POST /v1/chat/completions, /v1/responses and
  /v1/runs, plus model/capability endpoints. API source describes port 8642.
  `_check_auth` (around lines 1414–1436 at this revision) validates Bearer tokens
  against API_SERVER_KEY; normal startup requires a key. A no-key default-listener
  branch exists for tests/manual wiring, so a future adapter must independently
  require credentials and never infer authentication from a successful health GET.
- CLI docs describe scripted one-shot queries and query-file/stdin input. This
  is not a verified stable JSON result contract and may execute enabled tools.
- AIAgent is an internal Python facade, not a stable versioned SDK contract.
  Importing it loads agent dependencies and increases the trusted computing base.

A documented API exists; that does not establish a compatible deployed endpoint.
No URL/key/model, capabilities response, running service, TLS deployment, disabled
tool profile or cost evidence is available. Do not invent a /reason endpoint or
claim that OpenAI-shaped chat prevents Hermes's internal side effects.

## Security and licensing assessment

MIT permits commercial reuse subject to its notice and warranty terms. This is
not a review of every dependency, model license, hosted-provider contract or
customer-data term. No upstream code is redistributed in this step.

SECURITY.md says the default terminal backend executes on the host and explains
that terminal-only isolation does not confine plugin/code/MCP activity in the
agent process. Whole-process wrapping and network/credential restrictions are
required for untrusted input. Hermes's own heuristic approvals and redaction do
not replace independent Guardian enforcement. Equal trust among authorized API
callers is insufficient for IGRIS's capability separation without extra controls.

## Decision and next-step contract

Feasible as a future optional, isolated reasoning-only service. Implement an
IGRIS-owned typed planner interface and explicit mock in Step 13; default real
adapter must report unavailable, not silently fall back and claim success.
Proposals never grant permission or directly execute model-supplied actions.

Live activation remains PENDING_EXTERNAL_VERIFICATION: separately verify the
pinned installed version, authenticated capability/schema exchange, tool-disabled
and OS-isolated service, restricted egress, provider costs within ₹0, timeout/
cancellation behavior, log redaction and Guardian execution-boundary integration.
No paid model access, subscriptions, Mac installation or production work is
approved by this feasibility report. These live prerequisites do not block the
explicitly authorized mock-contract work in Steps 12–15.
