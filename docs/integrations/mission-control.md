# Interactive local Mission Control

Task 7 extends the existing `make_server` dashboard API. Its original read-only
snapshot mode remains available. The interactive mode reuses `ChatService`,
`MissionController`, private SQLite conversation memory, `ApprovalReviews`,
`OwnerActions` and `ApprovalStore`. It adds a bounded background queue and a
small static interface, with no frontend framework or new AI framework.

## Explicit startup

Use the already prepared cloud Linux x86_64 runtime. No installation or service
starts merely by importing the dashboard. Create private random credentials once;
the helper refuses to overwrite an existing file and prints no password.
Open the private file locally to obtain the owner or viewer password. Never paste
it into chat, logs or source control.

```sh
$ python3 scripts/create_dashboard_accounts.py --output runtime/mission-control/accounts.json
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json
```

Open the printed `http://127.0.0.1:8765` address and authenticate with the browser's
Basic authentication prompt. Only that exact loopback host is accepted. HTTPS,
public hosting and remote access are not configured. The `--remember` flag is
explicit consent to private conversation storage. Stop with the emergency button
or Ctrl+C; there is no autostart or automatic restart.

To enable reviewed capabilities in a disposable development environment:

```sh
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json --tools-config runtime/guardian-demo/tools.json --enable-specialists --enable-n8n --ops-demo
```

The tools profile must be private, valid and separate from the approval databases.
The existing sample profile is not overwritten by this command. Tools that need
interactive decisions must be explicitly listed in its `approval_required` field.
The additional flags do not download/install runtimes. Missing dependencies fail
closed when requested. `--ops-demo` explicitly creates one tiny owned Docker
application and removes it on dashboard exit. Alternatively `--ops-instance`
accepts the private configuration of a supported disposable test target; arbitrary
production targets are not allowed. Remediation is unavailable.

## Behavior and boundaries

- Chat and recent conversation history come from real backend data. The display
  uses the existing six completed-pair history window; older complete exchanges
  remain stored in SQLite. No arbitrary caller-supplied system/history roles exist.
- Safe tool proposals come from real Hermes, then the existing restricted broker.
  A waiting conversation keeps its reservation until approved, rejected, expired
  or cancelled. The same proposal resumes without a second inference call.
- The owner selects a specialist, bounded n8n calculation or exact Ops Pilot target
  and reviews the complete action/arguments, target, risk, IDs and digest. Typed
  confirmation of the first twelve digest characters is required for either
  decision. Decisions use the same single-use expiring Guardian service as CLI.
- Two bounded queues hold at most eight ordinary jobs and eight decisions. One
  worker mutates controller state. While approval is pending, new inference waits,
  so approval/stop HTTP requests and expiry cleanup cannot be starved by inference.
- Viewer access excludes conversations, task/result bodies, approvals, CSRF values
  and logs. Owner POST requires valid authentication, exact Host/Origin, same-site
  request context, a per-account CSRF value and a strict bounded JSON schema.
  Duplicate Host/length/JSON fields and transfer encoding are rejected.
- Script/style loading is same-origin; model/user content is rendered with
  `textContent`, never HTML interpretation. CSP blocks third-party scripts,
  frames, form navigation and cross-origin connections. No browser microphone
  API, clipboard monitoring or automatic voice activation is used.
- Status distinguishes disabled/configured capabilities from verified prior
  executions. Ops health is a cached approved observation with its timestamp,
  not an unsolicited current production probe. Voice is explicitly not connected.
  The resource display reports this runtime, not the Mac.

## Stop and process ownership

Emergency stop rejects new work, cancels tracked runtime jobs and pending
approval authority, releases conversation reservations and requires explicit
process restart. Its HTTP response acknowledges a request; only the later stopped
status means cleanup finished. It does not stop an external monitored application.
The explicitly created Ops demo is removed when the dashboard process exits.

Workers now use a separate Docker create acknowledgement before start/attach.
Private launch records and exact ownership labels bind cleanup to immutable
container IDs. Unknown creation responses retain a private record and block
further launches; no start is issued without an acknowledged ID. Records never
contain approvals and are never replayed. Creation has a separate 30-second
bound; execution and cleanup have their existing deadlines. Cancellation cannot
promise instantaneous rollback of already started read-only work.

If creation is unconfirmed, stop IGRIS and review its private launch record under
`runtime/locks/launches` (or `runtime/ops/locks/launches` for a disposable target).
Verify the exact name, ownership marker and daemon state before removing only the
owned container and resolving the record. Do not blindly delete records or issue
start commands from them. Local database rollback, host-owner/Docker-admin access
and abrupt process/daemon failure remain outside full isolation guarantees.

## Evidence

The real browser acceptance runs in an explicitly created offline user/network
namespace with only loopback. The preinstalled Chromium retains its namespace and
Seccomp-BPF sandbox. Its self-report lists Yama ptrace protection as unavailable;
this is not an independent full-sandbox certification. Credentials and automated
owner clicks are fixtures; inference, Guardian, filesystem, n8n, Docker, Ops Pilot
and browser rendering are genuine.

```sh
$ unshare --user --map-current-user --keep-caps --net python3 scripts/test_mission_control_live.py
$ unshare --user --map-current-user --keep-caps --net python3 scripts/test_dashboard_layout_live.py
$ PYTHONPATH=src python3 scripts/test_dashboard_cli_live.py
$ PYTHONPATH=src python3 scripts/test_isolated_worker_live.py
$ PYTHONPATH=src python3 scripts/test_hermes_cancel_live.py
$ python3 -m unittest discover -s tests -q
```

Validation JSON records real chat, a real Hermes time proposal, approval before
execution, real n8n calculation, real healthy Ops monitoring, rejection, a mobile
viewport and stop during an actual specialist worker. The current compact UI is
also tested for authenticated conversation creation and rejection. Synthetic
proposal, clock acceleration and unknown-create tests are identified as fixtures
in unit tests; they are not live inference or physical hardware evidence.

Failed attempts retained in the execution report include a mistaken n8n test
field, the CLI's duplicate module/class identity and Docker automatic-removal /
late-creation races. Fixes preserve denial and ownership checks. Screenshots stay
in ignored `runtime/task7`, with hashes in validation data; no credentials or
model weights are committed. Physical mobile hardware, Safari, Mac M1, native
microphone/playback and internet-facing deployment remain unverified.
