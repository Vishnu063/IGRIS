# Mission Control

Standard-library, read-only HTTP dashboard, loopback IPv4 only, OS-selected port.
No process/service starts on import. A trusted operator passes accounts and a
trusted snapshot provider to `dashboard.make_server`, then explicitly serves.
Use private random credentials of at least 32 characters; never put them in
URLs, source, chat or logs. HTTP Basic permits the browser's native sign-in;
plain HTTP is restricted to loopback. No external hosting, TLS or remote access
is configured. Do not bind publicly or forward it without a separate design.

Owner sees pending approval references; viewer cannot see that section. Both
roles see sanitized IGRIS/Guardian status, missions, agents, n8n, Ops Pilot,
projects, errors and warnings. Snapshots contain summaries, never prompts,
customer details, secrets or full action bodies. There is no approve/execute
endpoint. All POST operations deny. Host is exact loopback:port to restrict DNS
rebinding. HTML is escaped, CSP forbids scripts/frames, responses are no-store,
HTTP access logging is disabled. Unknown provider health defaults to unverified;
source/provider failure returns 503. Never map a configured service to healthy.

Tests use real ephemeral loopback HTTP and synthetic identities/data. This is a
local prototype, not a production server. No login throttling, idle connection
DoS hardening, persistent sessions or automatic service probes are implemented.
The snapshot provider remains trusted operator code; authenticated read access
does not establish source truth or give execution authority.
