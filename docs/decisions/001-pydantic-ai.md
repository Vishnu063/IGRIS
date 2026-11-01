# ADR 001 — Retain Hermes and Guardian; do not add Pydantic AI

Status: accepted for this completion plan. Evaluation date/version is bound to the accompanying live evidence, Pydantic AI 2.64.0 and Pydantic 2.13.4.

## Context

Hermes already runs the reasoning loop, typed request/reply contracts and role-conditioned specialists. Guardian independently parses proposals, authorizes operations, binds immutable scope to owner decisions and consumes execution leases. A second agent framework must offer measurable value without introducing another dispatch or approval boundary. The core deliberately needs only the standard library; optional workers isolate their dependencies.

## Evidence

The real PyPI metadata and hash-verified `pydantic-ai-slim` wheel were inspected without executing third-party agent instructions. The wheel exposes `Agent` output types and toolsets: useful structured output/retry facilities, but another orchestration abstraction around functionality already handled by Hermes. Both packages are MIT-licensed and require Python >=3.11. The full distribution depends on slim with provider, CLI, evaluations, MCP, web and Logfire extras. Slim itself declares eight base dependencies, including a graph framework, HTTP client, pricing data and telemetry API. Their presence alone does not activate a paid service, but adds dependencies without a demonstrated need here.

[Recorded comparison](../validation/pydantic-ai-evaluation.json) runs eight representative real validations against Guardian and standalone strict Pydantic models. Valid time/file requests pass; extra fields, shell operations, absolute/traversal paths and Boolean paths fail. Pydantic's normal JSON validator accepts a duplicate operation key that Guardian's strict parser rejects. An integration would still need the existing unique-key decoder and actual filesystem/approval enforcement. These examples do not claim exhaustive schema equivalence.

Five fresh-process Linux import samples measured median 0.0493 seconds for the current Guardian parser and 0.1261 seconds for standalone Pydantic. This compares import overhead only, not throughput or model inference. Pydantic AI's import/RAM was not measured because it was not installed or imported; the audited slim wheel was 2754541 bytes compressed and contains 416 Python source files. No invented full-install size or framework startup benchmark is presented.

## Decision and consequences

Do not integrate Pydantic AI or create a parallel agent runtime. Retain Hermes as the sole reasoning framework and Guardian as the sole authorization system. No provider, MCP server or observability account is configured. Keep strict JSON parsing, explicit dataclass/type checks, finite operation registration and execution-time permissions.

Standalone Pydantic remains a possible optional schema convenience if future contracts become sufficiently complex to demonstrate reduced errors or meaningful maintenance savings. Such a change must preserve duplicate-key rejection, strict types, extra-field denial, independent authorization, exact approval binding and the standard-library core. Schema validation does not establish sandboxing, permissions or prompt-injection resistance.

Reproduction (requires already installed optional Pydantic for this development analysis; it is not a core dependency):

```sh
$ python3 scripts/evaluate_pydantic_ai.py
$ git diff --check
```

No model inference was needed for this documentation/evaluation task, no second framework was activated and no live Pydantic AI integration is claimed.
