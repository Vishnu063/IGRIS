# Optional scoped Mem0 memory

Task 8 adds real Mem0 2.2.1 with FastEmbed 0.9.1, local MiniLM ONNX embeddings
and embedded Qdrant. The existing standard-library SQLite conversation store
remains authoritative and unchanged in format. A separate private facts database
reuses `Memory` storage/validation and binds owner, project and conversation.
No conversations are automatically imported, extracted, or sent to Mem0.

## Preparation and use

The optional Linux x86_64 environment is separate from the verified Hermes
runtime. Fifty wheel hashes and model provenance are pinned under
`integrations/mem0`. The initial wheel download is about 76 MiB; the model is
about 88 MiB on disk. Setup checks storage, uses wheels without build hooks,
checks existing assets rather than overwriting differences, and starts no service.

```sh
$ python3 scripts/prepare_mem0.py --prepare
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json --enable-mem0
$ PYTHONPATH=src python3 -m igris.chat --remember --resume --enable-mem0
```

Mission Control now defaults to the same `runtime/chat` state directory as text
chat. An explicit `--state-dir` can reuse another existing private conversation
store. No old directory is deleted or silently migrated. Unscoped knowledge from
older stores requires owner review before assigning a project/conversation.
The dashboard account file remains separate and private.

Select a conversation, prepare a concise fact, then review and confirm its exact
Guardian action. Assumptions and owner-verified facts are separate; a verified
fact needs evidence. Correction increments the revision and invalidates previous
verification. Deletion requires the current revision. Review and deletion are
owner-only; neither model output nor transcription can approve a change.

After explicit enablement, normal chat queries relevant approved facts from its
selected conversation/project. Facts are appended as bounded untrusted user-data
context. They grant no permissions or system roles. The original user request and
normal conversation history remain preserved. The reply metadata identifies the
backend and exact fact IDs/revisions used. Disabled/unavailable indexing has an
explicit SQLite keyword fallback; it is never called semantic retrieval.

## Security and compatibility decisions

- Guardian `memory.manage` requires explicit action-bound owner approval and
  scoped file-modify permission. Safe `memory.search` requires an explicitly
  configured read policy, matching owner and a valid conversation. The original
  three-tool broker rejects both names; its scope is not widened.
- Facts are scoped in SQLite before indexing. The index token includes owner,
  project, conversation and fact-store identity. Each worker mounts only that
  scope's derived index and a read-only approved-facts snapshot. The authoritative
  SQLite database, other conversations, approvals and credentials are not mounted.
- Retrieved IDs/revisions are rechecked against current SQLite rows. Deleted,
  stale, foreign or duplicated references do not return their old content.
  Current text always comes from SQLite. Cache updates also compare text hashes.
- All Mem0 LLM factory slots are registered to a fail-closed extraction class.
  `infer=False` is mandatory. The supported `lmstudio` configuration name is an
  internal compatibility alias, not a connected LM Studio service: Mem0's current
  Pydantic validator rejects custom names. No generative/extraction provider is
  activated. Hermes remains the sole reasoning framework.
- The supported FastEmbed slot uses a reviewed adapter with a pinned local path,
  CPU provider, one thread, offline-only loading and an explicit 256-token check.
  Extra tokens cause an explicit fallback rather than silent model truncation.
  Other embedding/vector factory providers are unavailable in this worker.
- Dense Qdrant disables optional sparse/BM25 model downloads. Telemetry and its
  remote notices are disabled before imports. No hosted vector DB, API credential,
  paid extraction model or background server is used.
- The separate reviewed worker profile permits writes only to one private hashed
  index directory. Network remains absent; source/model/packages are read-only;
  privileges/capabilities are dropped; memory, CPU, processes and time are bounded.
  Ordinary workers still reject writable-state parameters.

The pinned embedding model is English-focused. Hindi/Marathi semantic quality is
not verified. Scores are ranking values, not calibrated probabilities. Facts are
limited to 512 characters, 1,000 per conversation/project and 10,000 per store.
Sensitive-value filtering remains heuristic; it is not a general DLP guarantee.

SQLite and its derived vector cache do not share a transaction. An approved
SQLite change may already be committed if indexing is interrupted. Review current
facts before retrying after cancellation; no automatic rollback or re-execution
is claimed. Source revision checks keep stale cache data out of retrieval.
Deletion removes logical access and normal Mem0 entries, but forensic disk erasure
and removal from older backups are not guaranteed. Same-user host/DB tampering,
Docker administration and hard failures remain limitations.

## Evidence

```sh
$ PYTHONPATH=src python3 scripts/test_mem0_live.py
$ unshare --user --map-current-user --keep-caps --net python3 scripts/test_mem0_dashboard_live.py
$ python3 -m unittest discover -s tests -q
$ PYTHONPATH=src python3 -m igris.guardian.scan
```

The real test saves explicit synthetic owner facts, retrieves Mumbai from a
hosting-location query, rejects extraction, starts new isolated Mem0 workers,
reopens SQLite, and feeds actual approved memory into real Hermes. The generated
answer identifies Mumbai. Correction, deletion, source-scope denial, unchanged
prior conversation context and SQLite fallback are verified. Backend restart is
a new isolated worker process; the parent test reopens its service objects.
A fresh disposable wheel installation reproduces the package fingerprint.
Browser acceptance verifies no save before approval and rejection of deletion.

Owner decisions/credentials/facts are test fixtures; Mem0, embeddings, Qdrant,
SQLite, Guardian, browser and Hermes execution are real. Synthetic protocol,
clock and malformed/mount-profile tests are separately labelled. No Mac or
non-English semantic quality is claimed. Dependencies remain optional and are
reviewed further for vulnerabilities/licenses in Task 14.
