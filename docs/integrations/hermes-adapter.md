# Hermes adapter — Step 13

The IGRIS-owned HermesAdapter protocol accepts a bounded, sanitized PlannerRequest
and returns a validated Plan. It is not a copy of an upstream HTTP schema.
MockHermesAdapter supplies deterministic, clearly simulated proposals. Supported
routes are inspect_fixture and summarize; no tool call, permission, approval or
execution code is accepted from a response. The mock assigns its evidence origin;
responses cannot claim to be real.

Default selection is disabled. Selecting real returns an unavailable adapter
that raises AdapterUnavailable, with no automatic mock fallback. No Hermes
installation, provider call, credentials or live HTTP transport is enabled.
The Step 11 feasibility report documents real upstream interfaces and activation
prerequisites. A future live implementation needs a separately reviewed mapping
from its pinned upstream API and must not route around Guardian.

Contract tests cover typed requests, strict fields, size bounds, secret-like
text sanitization, injected authority fields, explicit simulation and honest
unavailable status. These tests verify IGRIS interfaces only. Network timeout
and compatibility tests await a verified live service; there is no hanging
network operation in the current mock/unavailable implementations.
