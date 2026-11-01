# Optional owned-site browser inspection

Manual entry point (trusted owner terminal required):

```sh
$ PYTHONPATH=src python3 -m igris.integrations.playwright_cli --enable-runtime
$ python3 scripts/test_playwright_live.py
```

Disabled by default. Guardian's existing OwnerActions/ApprovalStore requires explicit single-use action/context-bound approval before `browser.inspect`. The only arguments are `site=owned_acceptance` and `action=inspect_and_screenshot`. No generic URL, selector, JavaScript, input, upload or submission operation exists. Hermes native browser tools remain disabled. This CLI capability is not automatically available to chat or the dashboard.

The Linux worker uses rootless Bubblewrap, a private PID/mount/user/network namespace and an owned loopback fixture. It mounts only OS libraries/programs, the reviewed Python runtime, Node binary, worker and fixture read-only, plus one private output directory. No home, credentials, controller database or Docker socket is mounted. Chromium's namespace and seccomp sandbox remains enabled and its real status is checked. Playwright routes permit only GET/HEAD to the exact owned root; external requests, other ports, POST and WebSockets are blocked. The screenshot is size-limited, hash-checked and stored privately under runtime/playwright. No binary artifacts are committed.

Playwright 1.62.0 (Apache-2.0), Chromium 154.0.8037.57 (BSD and bundled third-party licenses), Bubblewrap (LGPL-2.0-or-later) are preinstalled cloud dependencies. The profile pins actual executable, worker, fixture and Playwright package hashes. OS libraries remain part of the trusted managed environment; this profile is not a portable Mac distribution. No new downloads were needed. The worker has CPU/file-size limits and a 55-second parent deadline; cancellation kills only its tracked process group and the namespace init reaps descendants. It is not independently certified isolation. Same-user tampering and kernel vulnerabilities remain outside this boundary. Chromium reports Yama ptrace protection unavailable; namespace/seccomp protections were genuinely enabled.

Live acceptance exercises a real screenshot and three actual forbidden requests. Owner decisions are automated trusted test fixtures, not model authorization. Browser inspection does not imply real websites/accounts are enabled.
