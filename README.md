# IGRIS — Personal AI Assistant

IGRIS is a cloud-first development prototype for software, automation, business
planning and DevOps work with a restricted independent execution broker.

## Actual implementation state

Tested local libraries provide mission control, Guardian permissions and exact
approvals, project/Git utilities, an authenticated read-only dashboard, business
records, private SQLite memory/earnings and backup restoration. The 15 specialist
definitions are copied and adapted from Agency Agents. A curated Hermes backend
source subset is copied and patched as the intended reasoning foundation.

**No live reasoning assistant or upstream integration is connected.** Hermes
startup/inference, installed n8n, Ops Pilot/Docker operations and speech engines
remain unverified. Specialist execution is a bounded simulation. Dashboard data
is supplied locally; no live service health is implied. Production deployment,
paid activation and external client submission remain disabled.

The authorized repository is `Vishnu063/IGRIS`; it is retained rather than
creating or renaming a repository to the suggested `igris-ai-assistant`.
Development takes place on `develop`. This cloud-first project must not install
software on the owner's Mac, activate paid services, or deploy to production.
The initial spending allowance is ₹0.

## Structure

- `src/igris/`: lightweight standard-library implementations and disabled adapters.
- `tests/`: local unit/security/integration tests with explicit simulations.
- `vendor/`, `integrations/agency-agents/`: copied source and adapted definitions.
- `workflows/`: inactive n8n definition and contract validation assets.
- `docs/architecture/`: design, local implementations and unresolved boundaries.
- `docs/governance/`: development and branch protection recommendations.
- `docs/execution/`: numbered execution evidence and status.

## Local verification

Run from the repository root:

```sh
$ python3 -m unittest discover -s tests -v
$ python3 scripts/check_ci.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ git diff --check
```

These checks exercise local implementation and explicit fixtures. They do not
establish live-service connectivity or Mac compatibility. Loopback tests need
socket permission. No package installation is needed for `src`/tests; Node is
used to verify workflow logic. See [configuration guidance](docs/configuration/README.md),
[integration matrix](docs/validation/integration-matrix.md),
[security results](docs/security/validation.md),
[cloud measurements](docs/validation/performance.md) and
[source notices](THIRD_PARTY_NOTICES.md). Hosted CI is manual-only and was not run.

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
single-use expiring approval. Real scoped mutations create new text artifacts;
recovery mutations are confined to simulator state. Production, spending and
external communications remain unavailable.

The [core controller](docs/architecture/controller.md) is a tested synchronous
in-memory library. No real reasoning service or autonomous assistant is active.

[Simulated orchestration](docs/integrations/orchestration.md) connects tested
controller and Guardian code to explicit Hermes/Ops Pilot mocks and a local n8n
contract fixture. Real service connections remain unverified and disabled.

Ops Pilot work through Step 20 includes a [read-only source audit](docs/integrations/ops-pilot-audit.md),
[monitoring export mapping](docs/integrations/ops-monitoring.md), evidence-linked
diagnosis and [proposal-only repair guidance](docs/integrations/repair-recommendations.md).
[Approved recovery](docs/integrations/approved-recovery.md) is tested only with an
explicit simulator; real Ops Pilot restarts remain blocked.

Development through Step 25 includes [project scaffolding](docs/development/projects.md),
a [reviewed sample application](docs/development/workflows.md), [local Git workflows](docs/development/git.md),
[manual-only CI preparation](docs/development/ci.md) and [production approval controls](docs/development/deployment.md).
These are trusted development utilities; no real production deployment is enabled.

The [15 specialist contracts](docs/specialists/README.md) have tested role boundaries
and [approval-gated simulated scheduling](docs/specialists/scheduling.md). They
are not connected live models; no separate Agent Builder is added.

The user-authorized [reuse correction](docs/revisions/reuse-correction.md) copies
and adapts Agency Agents definitions and Hermes backend source in this repo.
Real runtime activation is still unverified; these source copies replace the
earlier reference-only strategy. MIT notices and provenance manifests are retained.
