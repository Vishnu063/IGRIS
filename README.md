# IGRIS — Personal AI Assistant

IGRIS is a planned assistant for software development, automation, business work,
and DevOps operations with independent security enforcement.

## Actual implementation state

Foundation only. No assistant, Guardian, adapters, dashboard, voice service, or
business automation is implemented. No real integration has been verified.

The authorized repository is `Vishnu063/IGRIS`; it is retained rather than
creating or renaming a repository to the suggested `igris-ai-assistant`.
Development takes place on `develop`. This cloud-first project must not install
software on the owner's Mac, activate paid services, or deploy to production.
The initial spending allowance is ₹0.

## Structure

- `src/igris/`: reserved for future application source.
- `tests/`: foundation verification.
- `docs/governance/`: development and branch protection recommendations.
- `docs/execution/`: numbered execution evidence and status.

## Foundation verification

Run from the repository root:

```sh
$ python3 -m unittest discover -s tests -v
$ git diff --check
```

These checks verify the repository foundation only, not assistant functionality.
Future architecture, configuration, and implementation belong to later steps.
