# Optional manually started warm inference

Default behavior remains one-shot inference. An explicit terminal session can keep the same verified local model process loaded:

```sh
$ PYTHONPATH=src python3 -m igris.chat --remember --warm-runtime
$ PYTHONPATH=src python3 -m igris.chat --remember --warm-runtime --tools-config /absolute/private/tools.json --interactive-approvals
$ python3 scripts/test_warm_hermes_live.py
```

`/exit`, EOF or Ctrl+C shuts down the tracked session. Each warm worker serves at most twenty requests, waits at most sixty seconds for its next request and has a fifteen-minute maximum lifetime checked by the transport. A stopped/expired worker never restarts itself; end the CLI and explicitly start a new session. No daemon, login item, launch agent or public endpoint is created.

Only the model process and Python imports stay warm. Each request constructs a fresh real Hermes `AIAgent`, with only its explicitly supplied recent conversation and selected specialist definition. The model server receives a complete new request; its normal matching-prefix cache is an inference optimization, not conversation memory or permission. SQLite remains authoritative for conversations. Native tools are empty and actual dispatch remains default-deny. Structured proposals return through the existing Guardian boundary and exact owner approvals; model workers receive neither workspace nor approval databases.

The container has the same pinned model, upstream Hermes source, 65536-token context, zero budget, non-root user, read-only mounts, network-none namespace, dropped capabilities, no-new-privileges, 3 GiB memory ceiling, two CPUs and bounded process count as one-shot inference. Original model/archive/source integrity checks run at startup and before each request. A private random HMAC key goes only over the owning process's pipe, never arguments, files, prompts or logs. Request/response signatures, monotonically increasing sequence numbers, schema/correlation checks, input/output bounds and deadlines reject foreign/malformed frames. There is no generic command, filesystem or network operation.

One warm process reserves the existing cross-process heavy-runtime slot for its lifetime. Mem0 indexing, n8n, Ops Pilot workers and other inference calls cannot run concurrently through that slot. The CLI explicitly rejects combining `--warm-runtime` with `--enable-mem0`; choose one-shot mode for that workflow. The dashboard continues using its tested one-shot background queue. Warm mode is optional and is not silently enabled for the dashboard or all specialists.

## Measurements and tradeoffs

The live evidence records paired cold/warm arithmetic prompts, startup/model-readiness/import breakdown, actual inference timings, actual model peak RSS, persistent recall, fresh-conversation isolation, Guardian-approved real time execution and real cancellation. The regression suite overlapped the first cold sample; its timing has that additional system-load confound. The second cold sample and paired warm requests were collected after it completed. These small Linux samples demonstrate behavior in this environment and are not a stable performance SLA or Mac M1 benchmark. Startup is reported separately and must be included when considering short sessions.

The current model is already Q4_K_M quantized (1280835840 bytes). Serving context remains at Hermes' required 65536 tokens; upstream context/integrity controls were not disabled to obtain speed. Smaller models may reduce RAM but the existing 2B model already needs carefully scoped specialist tasks and can make serious reasoning errors. No untested smaller model replaces the default, no paid service is activated and no extra model download is justified within the constrained remaining disk budget. This plan's improvement comes from measured runtime reuse rather than a quality- or security-reducing model change.

Same-user/administrator tampering, kernel vulnerabilities, local database rollback and model hallucination remain limitations. This is a constrained worker architecture, not independently proven complete sandboxing. A process crash can leave an owned-launch ledger requiring explicit operator review; restart cannot resume pending approval authority.

Recorded Linux values: two cold calls 69.477/60.868 s, warm calls 36.904/40.111 s and startup 11.178 s. Totals including warm startup were 130.345 s cold versus 88.193 s warm (32.34% reduction). Per-request mean reduction excluding startup was 40.91%. Model readiness took 4.334 s; framework imports 2.246 s; unchanged host integrity preflight 2.539 s. Generation plus fresh-agent construction remained the dominant measured component. Model peak reached 2871968 KiB (about 2.74 GiB), so no memory reduction is claimed. Guardian time authorization took 6.200 ms and execution 0.408 ms. Active warm worker cancellation and verified removal took 2.901 s.

Timing collection preceded the final transport mutex and nested CLI-cleanup hardening; its exact source hashes are preserved in warm-hermes-live.json. The final transport then passed a separate real `11` response plus valid-payload forged-MAC and signed-replay rejection in warm-protocol-live.json, four focused protocol checks and the full 271-test suite. This distinction preserves the measured source evidence rather than relabeling an earlier run.
