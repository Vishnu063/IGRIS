# IGRIS — Personal AI Assistant

IGRIS is a planned assistant for software development, automation, business work,
and DevOps operations with independent security enforcement.

## Actual implementation state

Foundation only, with tested configuration, Guardian policy and a restricted
local execution broker. No assistant, adapters, dashboard, voice service or
business automation is implemented. No real integration has been verified.

The authorized repository is `Vishnu063/IGRIS`; it is retained rather than
creating or renaming a repository to the suggested `igris-ai-assistant`.
Development takes place on `develop`. This cloud-first project must not install
software on the owner's Mac, activate paid services, or deploy to production.
The initial spending allowance is ₹0.

## Structure

- `src/igris/`: strict configuration loader; assistant runtime remains future work.
- `tests/`: foundation and configuration verification.
- `docs/architecture/`: proposed component boundaries and data flows.
- `docs/governance/`: development and branch protection recommendations.
- `docs/execution/`: numbered execution evidence and status.

## Foundation verification

Run from the repository root:

```sh
$ python3 -m unittest discover -s tests -v
$ git diff --check
```

These checks verify the repository foundation and configuration, not assistant
functionality. See [configuration and secrets guidance](docs/configuration/README.md).
Integration and security enforcement implementation belong to later steps.

## Architecture

See [the proposed architecture](docs/architecture/overview.md). This design is
not evidence that its components or security controls are implemented.

Hardware targets, unverified resource estimates and the ₹0 policy are documented
in [hardware and budget constraints](docs/architecture/hardware-budget.md).

[Guardian security design](docs/security/guardian-design.md) records the threat
model and required deployment isolation. Design alone does not enforce security.

[Restricted execution](docs/security/execution.md) documents the narrow tested
broker interface and its deployment limitations.

[Secrets protection](docs/security/secrets.md) describes tested redaction and the
local source/index credential scanner, including detection limits.

[Approval controls](docs/security/approvals.md) bind a reviewed exact action to a
single-use expiring approval. Only new text artifacts have a mutation handler;
production, spending and external communications remain unavailable.

The [core controller](docs/architecture/controller.md) is a tested synchronous
in-memory library. No real reasoning service or autonomous assistant is active.
