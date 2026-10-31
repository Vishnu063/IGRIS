# Cloud review and local-library setup

Use the authorized GitHub/Codex cloud checkout, not the owner's Mac. Repository:
https://github.com/Vishnu063/IGRIS, branch `develop`. Nothing here starts a
production service or requires a package manager installation. This delivery is
a library prototype and test harness, not an end-user conversational application.

Verified environment: Linux x86_64, Python 3.12.14, Git 2.52.0, Node 24.19.0.
Use compatible Python 3.12 for these active-source checks; other versions are not
certified. Node is required for the isolated n8n JavaScript contract tests. Git
and loopback TCP permission are required for disposable Git/HTTP tests. Use tools
already present in the cloud environment. Do not install dependencies on the Mac.

From the repository root:

```sh
$ git status
$ git branch --show-current
$ python3 -m unittest discover -s tests -v
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ python3 -m compileall -q src tests scripts
$ git diff --check
```

Tests use temporary directories and synthetic data; they do not contact model,
billing, client, n8n or Docker services. HTTP tests bind ephemeral loopback ports.
If socket permission is unavailable, record that blocker rather than skip tests
and claim the same coverage. The credential scanner scans worktree and index,
including copied source, so it can take longer than unit tests. It prints only
finding locations/types, never matched values. Unknown secrets can evade it.

`config/development.json` and `config/test.json` keep every service feature false,
loopback binding and budget zero. `.env.example` documents two safe optional
variables; it is not loaded automatically. See docs/configuration/README.md.
No real credential is needed or requested. Feature flags are not permissions.

Library use is explicit and operator-driven. Add `src` to the Python module path
or use `PYTHONPATH=src` for an approved local script. MissionController requires
trusted route functions; routes are not accepted from a model/request. Do not
expose the trusted Git/scaffolding/backup/approval APIs directly to agents.
Memory and earnings need an owner-private directory (0700), new database files
(0600) and a trusted authenticated actor. Never use the approval store as memory.
Guardian's approval store must also be outside its approved project workspace.

Mission Control is a read-only prototype. A trusted operator supplies private
random accounts and a snapshot provider to `dashboard.make_server`; explicit
serving is required. It returns an ephemeral 127.0.0.1 listener. See
docs/architecture/mission-control.md. There is no bundled CLI, automatic service
manager, persisted mission queue, full chat UI or live health polling. No process
is started automatically by import, configuration or this delivery.

For a new development-source bundle path (existing output is never overwritten):

```sh
$ PYTHONPATH=src python3 -m igris.artifacts dist/igris-source-review.zip
```

The bundle includes source, copied Hermes subset, original/adapted Agency files,
MIT notices, tests, docs, safe examples and inactive workflows. It is explicitly
not production ready or a complete installable Hermes distribution. Generated
archives stay ignored by Git; the repository is the versioned deliverable.

Do not run the copied Hermes installer/CLI or install its requirements as part
of this setup. Its pinned runtime targets Python 3.14 and separate dependencies;
full startup, side effects, isolation and a genuinely authorized zero-cost model
need verification first. `activate_hermes` intentionally refuses. Hosted Actions
is manual-only and was not dispatched: source workflow validation does not prove
GitHub-hosted CI success or free account quota.
