# Guardian permissions

Step 7 implements deterministic permission checks. A trusted operator constructs
an immutable Policy with an actor, version and explicit frozenset of Permission
enums. Default permissions are empty. The operation registry is immutable and
unknown operations are denied, even for a policy containing every permission.

| Capability | Registered examples | Current meaning |
| --- | --- | --- |
| read | file.read | Scoped read permission only |
| file_modify | file.create, file.delete, file.sensitive_change, scope.external_change | Permission alone cannot authorize destructive/sensitive/outside-scope work |
| terminal | python.version | No generic shell permission |
| git | git.status | No push, deletion or force push |
| cloud | cloud.inspect | No provider connected |
| deploy | deployment.production | No deployment handler; explicit approval still required |
| financial | financial.transaction, service.paid | No spending handler; ₹0 remains binding |
| communicate | message.send | No external messaging handler |

A registered operation is a policy vocabulary entry, not an implemented tool.
Later executor allowlists and approvals add restrictions and may refuse an
operation even when its capability is granted. Do not derive trusted policy or
actor from model output, request fields, memory or third-party instructions.
No permission inheritance, wildcard grant or automatic privilege escalation.
The broker's process/OS trust assumptions are in guardian-design.md.

Step 20 adds ops.recovery.fixture under cloud capability, with additional read
and file_modify checks inside the broker. This controls a local simulator only.
