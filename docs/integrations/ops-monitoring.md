# Ops Pilot monitoring mapping — Step 17

OpsMonitoringAdapter consumes the audited schema-version-1 /api/report export.
Default transport is disabled. parse_export accepts an explicitly supplied export
and labels it provided_export, not independently collected real evidence.
LocalReportTransport exercises only 127.0.0.1 GET /api/report with an explicitly
supplied private owner-session cookie; contract results stay simulated. No live
session is configured, no login URL is scraped, and no POST action exists here.

A trusted TargetBinding fixes exact container name, Docker context and health URL.
Mismatched targets, unsupported schema, exports over 64 KiB, invalid/future/stale
generation times and absent investigation objects are rejected. Health and
container collection freshness are evaluated separately within a five-minute
window; incomplete/stale sources become unknown. Disabled monitoring and unknown
maintenance state are explicit issues; unknown maintenance blocks repair advice.

Normalized output contains endpoint status, selected Docker state/immutable ID,
daemon identity, OOM/exit/restart metadata, allowlisted log-signature counts and
fixed issue codes. Every observation can reference the SHA-256 export digest and
its source field. Raw logs, alerts, customer text, arbitrary findings and other
unselected fields are not forwarded. Upstream supports last-100-line signature
counts, not a raw-log API. A failed collector is never a healthy system.

The HTTP implementation is a read-only loopback contract transport with a
one-second per-socket timeout, bounded JSON, no redirects and no automatic retry.
It is not a production/network sandbox or hard whole-request timeout. A future
live connection requires protected credentials, isolated transport, independently
verified source/version and least-privilege review; owner sessions are broad.
No real connectivity or M1 validation is claimed.

Tests use representative source-shaped exports and a synthetic local HTTP server.
They exercise cookie rejection, correct route, freshness, type/scope failures,
filtered logs and secret-like metadata exclusion. They do not run Ops Pilot or
Docker. Existing Step 15 mock remains explicit and compatible.
