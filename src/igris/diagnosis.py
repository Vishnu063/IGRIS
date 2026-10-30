"""Deterministic evidence-linked observations and explicitly tentative causes."""
from dataclasses import dataclass
from .adapters.contracts import ContractError
from .adapters.ops_monitoring import Monitoring


@dataclass(frozen=True)
class Finding:
    code: str
    claim: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class Diagnosis:
    source_origin: str
    export_digest: str
    observations: tuple[Finding, ...]
    hypotheses: tuple[Finding, ...]
    limitations: tuple[str, ...]


def diagnose(snapshot: Monitoring) -> Diagnosis:
    if type(snapshot) is not Monitoring:
        raise ContractError('Validated monitoring evidence required.')
    observations, hypotheses = [], []
    def observed(code, claim, field):
        observations.append(Finding(code, claim, (snapshot.ref(field),)))
    def possible(code, claim, field):
        hypotheses.append(Finding(code, claim, (snapshot.ref(field),)))
    if snapshot.health == 'unhealthy':
        observed('endpoint_failed', 'The source reports a failed configured endpoint policy.', 'monitor.healthy')
    elif snapshot.health == 'healthy':
        observed('endpoint_passed', 'The source reports the configured endpoint policy passed at its check time.', 'monitor.healthy')
    if snapshot.container_state in ('exited', 'stopped', 'dead'):
        observed('container_stopped', 'The source reports a stopped/dead container; this does not establish why it stopped.', 'report.snapshot.observations.state')
        possible('stop_cause_unknown', 'An application failure, deliberate stop or host/runtime event may explain the stop; more evidence is needed.', 'report.snapshot.observations.state')
    elif snapshot.container_state == 'running':
        observed('container_running', 'The source reports a running container; application health is a separate observation.', 'report.snapshot.observations.state')
    elif snapshot.container_state == 'restarting':
        observed('container_restarting', 'The source reports a container in restarting state.', 'report.snapshot.observations.state')
        possible('restart_failure', 'Startup or configuration failure may be recurring; verify timestamped logs and recent changes.', 'report.snapshot.observations.state')
    if snapshot.oom_killed is True:
        observed('oom_termination_reported', 'Docker reports an OOM termination; the allocating component and source of memory growth are not established.', 'report.snapshot.observations.oom')
        possible('memory_pressure', 'Memory limits, workload growth or host pressure may have contributed; compare limits and time-series usage.', 'report.snapshot.observations.oom')
    if snapshot.exit_code is not None and snapshot.exit_code != 0:
        observed('nonzero_exit', 'The source reports a nonzero exit code; it is not a root-cause proof.', 'report.snapshot.observations.exit_code')
        possible('application_error', 'An application error or external termination may explain this exit; inspect timestamped application evidence.', 'report.snapshot.observations.exit_code')
    if snapshot.restart_count is not None and snapshot.restart_count > 0:
        observed('previous_restarts', 'The source reports prior restarts; a cumulative count alone does not establish a current restart loop.', 'report.snapshot.observations.restart_count')
    meanings = {
        'memory': ('memory_exhaustion', 'A memory-related log signature may indicate allocation pressure; causation is unconfirmed.'),
        'disk': ('disk_exhaustion', 'A disk-space signature may indicate exhausted space or quota; verify actual filesystem metrics.'),
        'dns': ('dns_configuration', 'A DNS signature may indicate name resolution or network configuration trouble.'),
        'dependency': ('dependency_failure', 'A connection signature may indicate a dependency, routing or startup problem.'),
        'timeout': ('request_timeout', 'A timeout signature may indicate load, dependency delay or a network problem.'),
        'authorization': ('configuration_or_permissions', 'An authorization signature may indicate credentials, configuration or permission trouble.'),
        'image': ('image_configuration', 'An image-pull signature may indicate an image reference, registry or permission problem.'),
    }
    for signal, count in snapshot.signals:
        if count:
            code, claim = meanings[signal]
            observed('log_signature_' + signal, 'The source reports a bounded log-signature count; raw logs are not available.', 'report.deep_evidence.log_signals.' + signal)
            possible(code, claim, 'report.deep_evidence.log_signals.' + signal)
    if snapshot.health == 'unhealthy' and snapshot.container_state == 'running':
        possible('running_but_unhealthy', 'Application, dependency, endpoint/probe configuration or routing may be failing; running state alone does not select a cause.', 'monitor.healthy')
    return Diagnosis(snapshot.origin, snapshot.digest, tuple(observations), tuple(hypotheses),
                     ('Observations are confirmed only within the declared source; simulation/import is not independent live verification.',
                      'Log signatures and exit codes do not establish root cause; compare timestamps and causal evidence.') + snapshot.issues)
