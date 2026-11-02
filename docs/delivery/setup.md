# Current cloud startup and verification

Use the existing authorized `develop` checkout. No Mac installation, production deployment, paid API or automatic startup is authorized. The standard-library core needs the existing Python >=3.12; the verified optional Hermes worker uses its separately pinned Python 3.14.9/Linux x86_64 environment, Docker image and GGUF model. A clone alone does not contain ignored model weights or installed optional packages: follow [the reviewed runtime preparation](../../integrations/hermes-inference/README.md) and [chat setup](../integrations/hermes-chat.md) before claiming it works elsewhere.

Manual chat, retaining sanitized history only with explicit consent:

```sh
$ PYTHONPATH=src python3 -m igris.chat --remember
$ PYTHONPATH=src python3 -m igris.chat --remember --resume
$ PYTHONPATH=src python3 -m igris.chat --remember --warm-runtime
```

Type `/exit`, send EOF or press Ctrl+C to stop. Warm mode is bounded, reserves the shared worker slot and never restarts itself; use one-shot mode with Mem0 or other heavy optional workers.

Restricted tools and a separate owner terminal decision channel:

```sh
$ python3 scripts/create_guardian_test_workspace.py
$ PYTHONPATH=src python3 -m igris.chat --remember --tools-config runtime/guardian-demo/tools.json --interactive-approvals
```

The helper refuses an existing destination. Inspect the private profile and explicitly set its `approval_required` list if needed before startup; the flag does not grant authority. Only time, allowlisted listing and file reading can be proposed. Native Hermes shell/filesystem/network tools remain disabled. Review the exact action and enter the controlling-terminal challenge; chat, documents and transcripts cannot approve.

Local Mission Control:

```sh
$ python3 scripts/create_dashboard_accounts.py --output runtime/mission-control/accounts.json
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json
```

The generator preserves existing files, writes random credentials privately and does not print them. Retrieve them only as the local owner; never commit or share that file. Default dashboard: http://127.0.0.1:8765, authenticated owner/viewer roles, CSRF and Origin/Host checks. The emergency-stop control cancels tracked IGRIS jobs and invalidates pending authority; it does not stop unrelated applications. Ctrl+C shuts down the local server. Start it again explicitly after stop; no login/reboot service exists.

Optional manually configured specialist, Mem0, approved browser and document entry points are described in their integration documents. Defaults remain off. **n8n is currently quarantined** after dependency audit: `--enable-n8n` cannot override the runtime block. Ops Pilot supports only the explicitly owned disposable read-only fixture, never automatic production remediation. Handy file transcription was genuinely tested earlier, but its cloud image is archived due storage constraints; sufficient free space, explicit image restoration and renewed checks are required before another cloud voice run. Physical microphone, natural English/Hindi/Marathi quality and Mac playback remain blocked.

Data-only backup, with a private existing parent directory and an output that does not already exist:

```sh
$ python3 scripts/backup_chat.py create --state-dir runtime/chat --file runtime/chat/snapshot.json --approve-data-operation
$ python3 scripts/backup_chat.py restore --state-dir runtime/chat/restored --file runtime/chat/snapshot.json --expected-sha256 COPY_THE_RECORDED_SHA256 --approve-data-operation
```

Stop active requests before backup. Restore uses a new directory and a fresh empty approval database; it never imports credentials, security policy, queued missions, pending authority or semantic indexes. Existing credentials/configuration stay separate. Backups are private plaintext sanitized data, not encrypted vaults; deletion does not erase older copies. Orphan facts from deleted conversations are excluded and are not resurrected.

Verification from repository root:

```sh
$ python3 -m unittest discover -s tests -q
$ python3 scripts/check_ci.py
$ python3 scripts/check_delivery.py
$ PYTHONPATH=src python3 -m igris.guardian.scan
$ git diff --check
```

These regression checks include explicit fixtures; separate live evidence is identified in the current final matrix. GitHub-hosted Actions remain manual and were not dispatched. See [Mac preparation and exact blockers](mac-package.md) for later authorized target-hardware work. No Linux cloud result establishes M1 compatibility.
