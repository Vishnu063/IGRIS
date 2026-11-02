# On-demand and explicitly retained Ops Pilot

The default mode is Manual; construction/configuration never starts the connector. Its registered `ops.lifecycle` action includes exact `action`, `container_id` and configured `mode`. Guardian prepares/approves/consumes the original action and revalidates runtime/target/context. Natural-language or model-generated approval cannot authorize it.

Use the existing prepared cloud runtime and private dashboard accounts:

```sh
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json --ops-demo --ops-mode manual
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json --ops-demo --ops-mode on_demand
$ PYTHONPATH=src python3 -m igris.mission_control --remember --accounts-file runtime/mission-control/accounts.json --ops-demo --ops-mode monitoring
```

Choose one command/mode, not all three. `--ops-demo` explicitly creates the owned disposable application fixture; it is not Ops Pilot or a production service. The fixture is removed on dashboard exit. Manual/Monitoring first require **Prepare component start**, followed by exact owner approval. **Prepare read-only probe** gets another action-bound approval and reuses the live component. **Prepare component stop** shuts down the connector without stopping the application. On-demand needs only an approved probe and always stops the connector afterward. Browser cancellation and emergency stop remain authenticated/CSRF-protected and responsive.

For a separately existing, explicitly authorized disposable instance configuration, use the new owner terminal console:

```sh
$ PYTHONPATH=src python3 -m igris.integrations.ops_lifecycle_cli --enable-runtime --instance /absolute/private/instance.json --mode manual
```

The console begins with the component stopped. Internal commands are start, status, probe, stop and exit; each action goes through the separate controlling-terminal challenge. EOF/Ctrl+C/exit cleans the owned component. The original `igris.integrations.ops_cli --enable-runtime --demo` remains the prior explicit one-shot read-only workflow and was replayed against real running/stopped fixtures. It is not an automatically loaded integration.

The retained process is an actual Ops Pilot `Pilot` instance, with no background `Pilot.start()` poller. Startup acknowledgement, signed request/response sequence, original export correlation and target validation are checked. A retained worker has a 256 MiB memory ceiling, one CPU and 64 PID ceiling; the cloud observed RSS is much lower but is not a Mac promise. Sessions are bounded to sixteen probes/one hour and require explicit restart after expiry. Source changes or failed scope validation trigger owned-component cleanup; uncertain cleanup blocks later work. No arbitrary URLs/commands/repair methods, production access, full Docker socket or privilege escalation are exposed.

Verification:

```sh
$ python3 scripts/test_single_task_ops_live.py
$ python3 scripts/test_single_task_ops_failures.py
$ python3 scripts/test_ops_lifecycle_cli_live.py
$ unshare --user --map-current-user --keep-caps --net python3 scripts/test_single_task_ops_dashboard.py
$ python3 scripts/measure_single_task.py
```

Live tests use the actual pinned library, Docker application, proxy and Guardian. Owner inputs are explicitly automated trusted fixtures; inference is not mocked in the separate chat/UI acceptance. The failures script deliberately times out or terminates only an acknowledged owned connector, verifies cleanup and preserves the application until explicit fixture cleanup. No n8n service or external account is used.
