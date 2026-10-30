# n8n orchestration contract — Step 14

Status: isolated contract implementation, NOT a connected n8n service. No n8n
installation, paid service, account, workflow activation or public endpoint.
Default N8nAdapter is disabled. Explicit local_contract mode supports only
http://127.0.0.1 with an operator-selected port and the fixed path
/webhook/igris-readonly. Remote hosts, localhost DNS, redirects, userinfo, query
strings and live modes are rejected. This is a trusted test harness, not a
production transport or SSRF boundary for arbitrary agent-selected endpoints.

## Contract version 1

Request fields (no extras): schema_version integer 1, mission_id lowercase
32-hex correlation ID, workflow exactly inspect_fixture, input with only an
application matching [a-z][a-z0-9-]{0,39}. Requests carry X-IGRIS-Key and a
SHA-256 Idempotency-Key derived from the canonical complete payload. The key
must be configured by the trusted operator, never supplied by a model or logged.

Response fields (no extras): schema_version integer 1, matching mission_id and
workflow, status completed/failed, output containing only a bounded summary.
JSON responses must fit 16 KiB. Duplicate keys and injected authority fields are
rejected; summaries are sanitized. Result origin is assigned simulated by the
client, never accepted from the service. A completed fixture is not proof of
application health or real workflow connectivity.

## Errors, timeouts, retries and idempotency

Per-socket I/O timeout is configurable up to 3 seconds; default 1 second.
This is not a hard whole-request deadline against malicious slow-drip peers.
A future live transport needs a process-level wall deadline and hardened TLS.
Retries are bounded to at most two (three total attempts), on transport errors
or 502/503/504 only. Authentication, redirects and invalid schema failures are
not retried. No response body, URL or credential is included in failure messages.

The only workflow is read-only and deterministic; repeating it has no mutation
side effects. The stable digest header helps correlate retries. It is not proof
that a real n8n deployment deduplicates requests. Mutating workflows are forbidden
until their actual side effects use Guardian, with separately verified provider
idempotency/reconciliation. A broad workflow approval cannot authorize arbitrary
nested operations. No cloud/production credentials are present.

Audit records retain at most 128 (mission ID, attempt number, HTTP status) tuples
and emit the same minimal event to the configured IGRIS logger. This is bounded
local evidence, not durable/tamper-resistant audit storage.

## Inactive workflow template

workflows/n8n-readonly-fixture.json contains a webhook → validation code → JSON
response chain. Header authentication is requested but no credential ID/value is
embedded. It must remain inactive. Before any future import/activation, verify
node-version compatibility and configure a private header credential for
X-IGRIS-Key. No activation is authorized here. Import success, real HeaderAuth
behavior and runtime node compatibility remain PENDING_EXTERNAL_VERIFICATION.

The validation code permits only fixture inspection and returns labeled simulated
evidence. It has no provider, shell, file-write or paid-operation node. Tests
execute this trusted JS function with Node, not the n8n interpreter.

## Verification

Tests use a synthetic authenticated HTTP server bound to 127.0.0.1 on an
OS-selected ephemeral port and shut it down afterward. These are real local
HTTP round trips against a fixture, not real n8n integration. The sandbox initially
refused socket creation; tests passed after the supported command-level network
permission was granted. Network permission is needed to run these tests in this
cloud environment; no checks are skipped to hide the restriction.
