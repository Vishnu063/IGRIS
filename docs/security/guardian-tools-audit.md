# Milestone 3 pre-implementation audit

Baseline: develop, 308fdfd71ccd42d50a488379d2b34abed71fdd6a; clean initial working tree.
Read the original 50 records' implementation/security/limitations, missing middle
records in full, both activation reports, README, architecture/security boundaries
and actual chat/controller/memory/broker/approval/adapters/scheduler source.
Baseline document/source hashes are in ../validation/guardian-tools-audit-sources.json.
This is self-review, not independent certification.

Before: ChatService validates a real reply, stores a completed exchange and returns
a verified controller outcome. No model proposal is sent to Guardian. The native
Hermes turn_tool_round invokes AIAgent._execute_tool_calls; reasoning_session
subclasses that method to require default-empty Guardian permission and deny.
Native tool lists are empty. No native OS tool is enabled.

Existing Guardian: Policy defaults empty; executor launches isolated/no-site Python
with scrubbed environment and three-second deadline; broker applies resource
limits, fixed handlers and descriptor-based no-follow text access. The legacy
file.read capability lacks an explicit per-file allowlist, and no time/list tool
exists. Existing file.create/fixture capabilities must not become chat tools.
ApprovalStore has real SQLite exact action/actor/workspace/environment/version
binding, expiry and atomic single-use consumption. It has no authenticated human
approval UI; model-visible approval issuance/decision must remain unavailable.
Early schema/permission denials currently lack persistent audit rows. Approval
records are development/test data, not production authorization. No real owner
approval or existing privilege will be imported from chat/history.

Bypass review: specialist scheduling runs only reviewed fixture batches through
Guardian; real specialist models are unavailable. n8n is an authenticated loopback
contract fixture with no real activation; Ops Pilot mutations stay unavailable.
Trusted project/Git/development Python utilities can run processes as the OS user
but are not model tools and must remain unreachable. The host Docker launcher is
trusted and not exposed to model JSON. No arbitrary command path is present in
current chat. Same-user malicious code can bypass Python APIs or edit databases;
this remains a host trust limitation. There is no verified hostile-host sandbox.

After (implementation decision): reuse executor/broker, Policy and ApprovalStore.
Add a dedicated tools-only startup profile that cannot reach legacy handlers.
Hermes emits one bounded JSON proposal using normal real inference; native tools
remain disabled. Only the broker parses/authorizes it. The trusted host supplies
actor, immutable policy, scope and correlation; none comes from model/history.
Only get_current_time, list_workspace_files and read_workspace_file may execute,
with exact schemas, explicit operation/directory/file allowlists, protected audit
storage and existing single-use approvals strengthened with execution/scope
binding. Approval-required chat requests remain blocked because no interactive
human approval interface is available. No issuance method is exposed to chat.

Model remains in the existing fresh offline non-root read-only container, without
the approved test workspace or approval/audit/chat databases mounted. Guardian
executes bounded read-only tools outside that model container in its existing
short-lived process. Record all proposal decisions, including malformed/unknown
operations, without raw arguments, paths, bodies or secret values. No shell,
network/browser, file modification, deployment, Git or paid capability is enabled.
