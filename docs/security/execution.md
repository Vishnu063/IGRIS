# Restricted execution interface

Step 8 implements `guardian.executor.execute(policy, workspace, request)` as a
trusted launcher and `broker.py` as a short-lived independent process. Only the
request dictionary is untrusted. An agent MUST NOT control launcher policy,
workspace, Python executable, broker source or approval-store configuration.
A request must contain exactly `operation` and `arguments`. No network listener.

The broker checks policy inside the process immediately before its fixed handler.
Only `file.read` (one `path`) and `python.version` (no arguments) are implemented
at this step. No arbitrary argv, shell, command strings, arbitrary Python, Git,
cloud, deployment, financial, communication or mutation execution is exposed.
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
