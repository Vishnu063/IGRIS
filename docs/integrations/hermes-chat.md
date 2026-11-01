# Manual Hermes chat and persistent conversation memory

Phase 1 Milestone 2 adds an explicit chat route to the existing MissionController.
It uses the same isolated Hermes AIAgent/local Qwen inference verified in
Milestone 1. This route is separate from the legacy disabled Hermes planner
adapter; no existing mock planner is relabeled as a live service.

This is a local terminal interface operated by the authenticated cloud OS user.
The trusted logical actor is `owner`. It is not a public API, remote login system,
web dashboard, voice implementation or multi-tenant authentication boundary.
Existing n8n/Ops Pilot/specialist simulations remain unchanged.

## Start explicitly

First prepare the [verified Linux cloud runtime](../../integrations/hermes-inference/README.md).
No package installation is required for the host controller. Run from the repo root:

```sh
$ PYTHONPATH=src python3 -m igris.chat --remember
$ PYTHONPATH=src python3 -m igris.chat --remember --resume
$ PYTHONPATH=src python3 -m igris.chat --list
```

`--remember` explicitly consents to private plaintext storage of validated chat
messages in ignored `runtime/chat/chat.sqlite3`. Without that flag, chat refuses
to run. `--list` does not infer or store a message. Storage directory must be
private (0700), database 0600, same OS owner, without symlinks/hardlinks. The
persisted logical owner must match on reopen. Do not paste credentials or customer
information; recognized sensitive input is rejected before inference/storage.
Regex detection is incomplete and is not encryption or a guarantee of privacy.

Type `/history`, `/sessions`, `/forget` or `/exit`. `/forget` deletes the current
conversation and its exchanges and opens a new empty session. SQLite secure
deletion is enabled; copies, filesystem snapshots and backups require separate
handling. A backup is not deleted by forgetting the live conversation.

For a single bounded request, use `--once --json` and enter the message on stdin,
then EOF. Prompts are not supplied as process arguments:

```sh
$ PYTHONPATH=src python3 -m igris.chat --remember --resume --once --json
```

`--session` accepts an owned session ID; `--resume` selects the newest-created
session. Optional `--state-dir` must name a private directory controlled by the
operator. Creation, conversation selection and output are controlled by trusted
CLI arguments, never model instructions. No shell commands are parsed from chat.

## Request, inference and persistence

1. ChatService verifies the owner and Guardian read/file-modification permissions
   for trusted host storage. It validates text and creates an ordinary controller
   mission with fixed `chat` routing.
2. A SQLite transaction reserves a request bound to conversation and mission IDs.
   Only one unfinished request per conversation is permitted across processes.
3. Only the latest six completed user/assistant pairs, at most 16 KiB of UTF-8
   content, are supplied. Individual texts are bounded to 4096 characters/8192
   bytes and the whole transport packet to 32 KiB. The history schema cannot
   contain system/tool roles or authority fields. Older history stays stored
   until explicitly forgotten; it is not all sent to the model.
4. A global nonblocking file lock and runtime container label check allow only
   one inference worker. Hash-checked artifacts/source and the pinned existing
   image are required; no automatic download, image pull or host fallback occurs.
5. A fresh restricted offline container receives one validated JSON request on
   stdin. It mounts only required code/model/runtime read-only, never the database,
   Docker socket, host home, credentials or other conversations. Hermes receives
   plain dialogue history; no history can change Guardian or grant permissions.
6. The model runs real local CPU inference. Response/model identity, correlation,
   API-call count and controls are checked. Generated control characters are
   removed and recognized sensitive output redacted before display/storage.
7. A matching pending exchange is atomically completed before the controller
   reports verified success. Failed/blocked/interrupted requests have no completed
   assistant response and never enter the model's subsequent history.

Mission state is still the existing in-memory controller; completed exchanges,
mission/request IDs and provenance persist in SQLite. There is no vector search,
Mem0 integration, arbitrary document recall, durable background job runner or
restart of unfinished missions. A hard crash/kill can leave a pending request
and/or container. Those block further work and require operator review; no
automatic lease expiry/replay can duplicate an action. Normal Ctrl+C requests
worker removal and marks the unfinished exchange failed. SIGKILL/host failure
cannot guarantee cleanup. A stuck session must be reviewed before explicit
operator abort; no model-controlled recovery or blanket cleanup exists.

The inherited `ConversationMemory.backup(owner, destination)` makes a private
SQLite snapshot, including chat tables. Reopen it with the same owner for restore.
This API is tested; the older generic configuration ZIP backup is not a chat
backup CLI. Backups contain private plaintext messages and must be protected.

## Guardian and runtime boundary

Native Hermes tools remain empty. An actual override of Hermes tool dispatch
calls default-empty Guardian and denies execution; each worker tests that boundary.
The host storage policy is never passed to the model. Empty tools and a system
message are defense layers, not the only protection: non-root identity, no external
network, read-only mounts, no capabilities, no-new-privileges and explicit resource/
time limits constrain the actual process. Even a misleading model answer grants
no command, deployment, financial or communication capability.

Fresh model startup is deliberate for now. One turn may take tens of seconds on
two cloud CPUs; this has not been validated on a Mac M1. Only Linux x86_64 is
currently supported by the pinned runtime. No service is enabled on import,
boot or login, and no container stays running after normal completion.

The trusted OS/Docker operator, reviewed local profile/code and kernel remain
part of the trust boundary. Same-user malicious code can bypass Python objects;
this is not isolation from a compromised host. Upstream/dependency vulnerabilities,
model hallucination, unknown-secret leakage and prompt injection that affects
answer quality remain residual risks. No claim of general prompt-injection
immunity, complete assistant functionality or Mac readiness is made.

## Reproduce acceptance

```sh
$ python3 -m unittest discover -s tests -p test_chat.py -v
$ python3 scripts/test_chat_live.py
```

The first uses explicitly labeled backend/protocol fixtures and real disposable
SQLite. The second uses actual CLI processes, fresh offline containers, actual
Hermes inference and a randomized synthetic codeword. It asserts cross-process
recall, a separate conversation's isolation, persisted ownership, backup/restore,
explicit forgetting, real SIGINT and container removal. It creates and deletes
its own private test directory. Latest evidence in ignored
`runtime/chat-live-evidence.json` becomes RUNNING before testing and FAIL/STOPPED
on failure; old PASS is not retained as a current result. A reviewed successful
snapshot and implementation hashes live in
[chat-live.json](../validation/hermes-chat-live.json). Milestone 1 evidence remains
historical and bound to its own commit rather than rewritten for this refactor.
