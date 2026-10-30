# Restricted execution interface

Step 8 implements `guardian.executor.execute(policy, workspace, request)` as a
trusted launcher and `broker.py` as a short-lived independent process. Only the
request dictionary is untrusted. An agent MUST NOT control launcher policy,
workspace, Python executable, broker source or approval-store configuration.
A request contains `operation` and `arguments`; Step 10 additionally accepts
an optional `approval_id`. No other fields are accepted. No network listener.

The broker checks policy inside the process immediately before its fixed handler.
At Step 8, only `file.read` (one `path`) and `python.version` (no arguments) were
implemented. Step 10 adds approval-gated `file.create` for new text artifacts;
see approvals.md for current restrictions. No arbitrary argv, shell, command strings, arbitrary Python, Git,
cloud, deployment, financial, communication or unrestricted mutation execution is exposed.
Registered policy names alone do not enable handlers.

Reads are limited to 8192 bytes and ordinary UTF-8 text files with allowed
extensions. Paths are relative, ASCII, depth/length constrained; dot-prefixed
components and sensitive-name paths are denied. Descriptor-based O_NOFOLLOW
traversal and final-file validation reject symlinks, hardlinks, devices and FIFOs.
These rules reduce access, but are not general secret detection: safe-looking
files can contain secrets. Step 9 adds output sanitization, but patterns cannot identify every secret.
Do not use this interface on sensitive live data without the required deployment
isolation and a data-specific security review.

Subprocesses use fixed argv, `shell=False`, Python isolated/no-site mode, scrubbed
environments and a trusted workspace. The parent applies a 3-second wall timeout
and kills the broker process group on expiry. The broker applies 2 seconds CPU,
256 MiB address space, 64 descriptors, 1 MiB file size and disabled core dumps.
Failure to apply limits denies execution. Input is bounded to 16 KiB; replies
over 32 KiB are rejected. Unicode escaping may cause a smaller allowed file to
exceed the output cap; rejection is safe. No untrusted subprocess output producer
is allowed; adding one requires bounded streaming, process-count and egress review.

Verified on this Linux cloud Python runtime, not macOS. `resource` and no-follow
filesystem support are required; unsupported runtimes fail closed or cannot start.
No network sandbox is implemented by Python. Separate process independence is
verified; hostile same-user containment is not. See guardian-design.md before
any future deployment.

Tests use real local broker processes, files, symlinks/hardlinks, FIFO, fixed
subprocess and OS-limit inspection. Timeout handling alone uses a process test
double; this does not measure real timeout behavior or provider performance.
Inherited Python environment poisoning is tested with synthetic startup code.

Step 20 adds ops.recovery.fixture, an approval-gated local state simulator with
a fixed fixture path, lock and strict schema; it never executes Docker commands
or provider requests. See ../integrations/approved-recovery.md for limits.
