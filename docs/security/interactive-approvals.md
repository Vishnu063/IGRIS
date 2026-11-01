# Interactive owner approvals

Task 1 extends the existing Guardian; no new privileged tool or second policy
engine is introduced. Normal chat and tool mode still default to no interactive
issuer. To opt in on an actual controlling terminal:

```sh
$ PYTHONPATH=src python3 -m igris.chat --remember --tools-config runtime/guardian-demo/tools.json --interactive-approvals
```

The private profile must explicitly list the chosen existing tool under
approval_required. The demo from Milestone 3 has that list empty; review/edit your
own private profile to require get_current_time, for example. This flag does not
change policy or make an unregistered operation executable.

Hermes emits its proposal once and exits its offline container. Guardian's
preparation phase validates policy, arguments and scope without executing a
handler. The trusted owner service freezes operation, full arguments, actor,
target, scope/mission/request binding and action digest. It creates an existing
ApprovalStore request with 300-second expiry. The mission waits and its private
conversation reservation remains active; overlapping turns are rejected.

A separate /dev/tty channel displays the exact review and read-only risk. Type
APPROVE followed by the displayed twelve-character digest challenge, or REJECT.
Chat stdin, voice, documents, model output and generic text saying APPROVE are
never decision sources. No controlling terminal means failure, not approval.
The owner must respond within sixty seconds. EOF, invalid input, timeout and
Ctrl+C cancel/reject without execution and release the conversation reservation.

Approval resumes the SAME immutable proposal and IDs without another inference.
The existing broker revalidates the current scope and consumes the exact approval
once immediately before its fixed handler. Changed scope/arguments, forged,
expired, rejected or used approvals deny. Terminal decisions, closure, preparation
and execution are audited without raw action bodies. Displayed action data is
escaped and recognized sensitive content is not eligible for owner review.

ApprovalReviews prepare/decide/cancel and ChatService decide/resume/cancel are
trusted host interfaces for the later authenticated dashboard. They are not
model tools. Pending snapshots are process-local; restart never restores execution
or reuses an approval. A hard crash can leave a conversation lease requiring
operator review, as before. Private SQLite remains mutable by its OS owner;
this is not hostile same-user containment. No real client/production/money action
is enabled. Automated PTY decisions are synthetic owner test input; live tests
use actual Hermes, terminals, SQLite and the Guardian broker.
