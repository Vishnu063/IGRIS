IGRIS EXECUTION REPORT

Task: 10 / 14
Title: MarkItDown documents
Status: PASS

Recorded: 2026-11-02T04:16:43.488822+05:30

Implemented:

- Optional MarkItDown 0.1.9 with 36 hash-locked Linux wheels in an isolated environment; five explicitly registered local converters, no plugins or paid providers.
- Existing Guardian owner approvals bind document hashes, workspace, arguments and converter runtime. Descriptor-safe allowlist, archive controls, networkless non-root worker, bounded redacted Markdown.
- Manual conversion CLI and optional real-Hermes summary; text is untrusted data and grants no tool rights.

Real versus simulated:

- Genuine generated PDF, DOCX, XLSX, PPTX and HTML files converted by actual MarkItDown; no mocked parsers.
- Real Hermes summarized all five extracts: Deployment region: Mumbai. Budget: 0 INR.
- Automated trusted owner approval inputs are test fixtures, not model approval.

Tests and results:

- 3 focused security tests PASS, covering traversal, absolute/sensitive paths, symlinks/hardlinks, archive traversal, entities, external relationships, macros, bombs and oversized inputs.
- Real conversions and heading/table structure PASS. HTML remote image and embedded instructions did not obtain network or tool authority.
- Actual malformed PDF parser failure and owned-worker cleanup PASS. A preliminary failure-test run coincided with another model worker; tightened assertion excludes RuntimeBusy and reran after inference completed.
- Initial DOCX fixture incorrectly used Title style; changed to a genuine heading and verified actual Markdown structure.
- Compile and whitespace checks PASS. Last full regression: Task 9, 263 PASS; changes here are an optional module and explicit permission registrations.

Security review:

- No generic filesystem or URL converter exposed. Native Hermes tools remain disabled; original three-tool broker unchanged.
- 4 MiB inputs, 32 MiB archive expansion, 500 members, 100:1 ratio; external OOXML relationships and embedded executables rejected.
- Docker network none, caps dropped, no-new-privileges, read-only mounts, 1 GiB memory, CPU/wall/file/output bounds; no approval DB or credentials mounted.

Performance:

- Live five-format conversion plus real summary: 112.021 seconds on Linux.
- Optional environment 243235172 bytes; converter RSS 176604–191684 KiB. Conversion operation timings exclude imports/container startup.

Known limitations:

- No OCR for scanned PDFs; partial/empty extraction possible. Output caps/truncation reported; summary CLI uses first 2500 characters.
- Strict archive limits reject some legitimate large/compressed or externally linked documents. No lossless layout guarantee.
- Manual CLI/API only; automatic chat attachment UI and Mac validation not claimed. Same-user, kernel and parser vulnerability risks remain.

External requirements:


Files changed:

- README.md
- docs/integrations/markitdown.md
- docs/validation/markitdown-failure-live.json
- docs/validation/markitdown-live.json
- integrations/markitdown/dependencies.json
- integrations/markitdown/profile.json
- integrations/markitdown/requirements-linux-x86_64.lock
- integrations/markitdown/worker.py
- scripts/test_markitdown_failure_live.py
- scripts/test_markitdown_live.py
- src/igris/guardian/approvals.py
- src/igris/guardian/policy.py
- src/igris/integrations/markitdown_cli.py
- src/igris/integrations/markitdown_runtime.py
- tests/test_documents_boundary.py

Commands executed:

$ python3 scripts/test_markitdown_live.py
$ python3 scripts/test_markitdown_failure_live.py
$ python3 -m unittest discover -s tests -p test_documents_boundary.py -q
$ git diff --check

Git commit:

- Verified implementation: 57619094d630584dd420a02d93cc5e61932ce44f
- This report is recorded in a following documentation commit; remote tip is checked after publication.

Git delivery:

Connected GitHub App publishes the exact staged tree using expected-head fast-forward; remote branch SHA is verified separately. Git CLI authentication unavailable.

Next task:

- 11

Approval required:

- No for authorized development/push. Mac access, production, main merge, paid services and new host privileges remain unauthorized.
