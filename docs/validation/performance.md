# Performance and reliability — Step 48

Measured 2026-10-30 in managed **Linux x86_64**, 3 visible CPUs, Python 3.12.14.
Raw observations: `performance-step48.json`; reproducible bounded harness:
`scripts/measure_performance.py`. No provider, paid runner or Mac involved.

| Operation | Trials | Median |
|---|---|---|
| Fresh Python imports of lightweight core modules | 5 | 116.7 ms |
| One in-memory mission through valid states | 5 | 0.050 ms |
| Real scoped broker file read | 5 | 72.6 ms |
| Denied request followed by valid read | 5 | 158.5 ms |
| Two concurrent simulated specialist brokers, including replay denials | 3 | 282.8 ms |
| 1,000 plain log records | 5 | 7.07 ms |
| 1,000 records with secret-redacting formatter | 5 | 12.64 ms |

Observed parent peak RSS: 15,616 KiB (15.25 MiB). Largest completed child peak
RSS: 16,348 KiB (15.96 MiB). Parent CPU during harness: 0.173 seconds; aggregate
completed-child CPU: 2.898 seconds. These Linux getrusage peaks are not summed
concurrent/system memory or idle service budgets. Startup includes Python plus
selected local modules, not the copied Hermes runtime or speech models. No cache
flush or statistical confidence interval; shared cloud load can affect timing.

Six reliability assertion groups passed: mission success, real broker read,
recovery after denial, two concurrent fixture executions, replay refusal and
retained log redaction. Each concurrent job used an independent trusted scheduler
with its own one-batch slot. This tests no live model concurrency, and does not
raise the per-scheduler one-batch/two-role limit. The requests cause no external
actions. Logging measurements use in-memory output and ordinary event text;
the separate sensitive-message assertion verifies redaction remains enabled.

Full test suite at Step 47: 160 tests passed in 25.085 seconds. No production
traffic, long soak, memory leak, full dependency, heavy model, ASR/TTS, Docker
Desktop or thermal/energy test performed. The 8 GB/50 GB M1 target is **not
validated**. Later hardware testing must measure full selected stacks, startup
downloads/build peaks, swap, free storage, idle CPU, microphone behavior and
recovery before enabling any always-running service.
