# Core controller — Step 12

MissionController accepts bounded text requests and named trusted routes, creates
unique mission IDs, tracks immutable snapshots/history, handles approval waits,
and returns sanitized reports. It is a synchronous in-memory library, not a
network interface, authentication server, durable queue or scheduler.

The trusted actor and route callables come from operator startup. Do not accept
callables/import paths/identity from a model or request. A route is trusted code;
any execution it performs must use Guardian. No model or provider is connected.

States progress requested → planned → ready → running → verifying → succeeded.
Handlers can instead produce blocked, failed or approval_required outcomes.
Success requires a verified outcome and explicit local/real/simulated origin.
Simulation can succeed only as a labeled simulation. Unknown evidence cannot
succeed. Handler exceptions return a fixed sanitized error rather than details.
Terminal missions cannot rerun. Awaiting approval requires a reference to resume,
but that reference is not validated or granted authority by the controller:
Guardian must recheck it at the actual side-effect boundary.

Approval requests are represented by a registered handler's real/synthetic pending
request ID, not by automatically approving anything. Step 15 will exercise the
real local approval store and broker with a simulated integration mission.
No persistence, multi-user isolation, cancellation, background timeout or thread
safety is claimed; use one owner and one synchronous call at a time. Handlers
must bound their own I/O, and persistence is deferred to the memory/state steps.
