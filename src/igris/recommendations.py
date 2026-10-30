"""Proposal-only repair recommendations; no command execution or approval grant."""
from dataclasses import dataclass
from .adapters.contracts import ContractError
from .adapters.ops_monitoring import Monitoring
from .diagnosis import Diagnosis


@dataclass(frozen=True)
class Recommendation:
    code: str
    summary: str
    supported_operation: str | None
    required_permissions: tuple[str, ...]
    requires_owner_approval: bool
    risks: tuple[str, ...]
    prerequisites: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    source_origin: str
    execution_available: bool = False


def recommend(snapshot: Monitoring, diagnosis: Diagnosis) -> Recommendation:
    if type(snapshot) is not Monitoring or type(diagnosis) is not Diagnosis or diagnosis.export_digest != snapshot.digest:
        raise ContractError('Matching validated diagnosis and evidence required.')
    refs = (snapshot.ref('monitor.healthy'), snapshot.ref('report.snapshot.observations.state'))
    general = ('Source observations may be stale or incomplete; confirm current target and timestamps.',
               'Live recovery is disabled until Guardian enforcement exists at the actual provider boundary.')
    if snapshot.maintenance_active or snapshot.issues:
        return Recommendation('fresh_evidence_required', 'Collect fresh scoped evidence and confirm maintenance/monitor settings before considering a repair.',
                              None, ('read',), False, general,
                              ('Resolve incomplete/unknown state and owner maintenance intent.',), refs, snapshot.origin)
    eligible = (snapshot.health == 'unhealthy' and snapshot.container_state in ('exited', 'stopped', 'dead', 'restarting')
                and snapshot.restart_offered and snapshot.container_id is not None and snapshot.daemon_id is not None)
    if eligible:
        return Recommendation('review_restart', 'The source reports a stopped/restarting container. Review filtered logs and prepare an owner-approved restart option.',
                              'docker.restart', ('read', 'cloud'), True,
                              ('A restart may interrupt traffic, repeat the original fault or have an unknown outcome.',
                               'An intentional stop must not be mistaken for an outage.',
                               'No automatic restart rollback is supported.') + general,
                              ('Review the fresh exact Ops Pilot plan and immutable container/daemon identity.',
                               'Review resource/configuration evidence; do not treat a hypothesis as a confirmed cause.',
                               'Require separate provider approval plus Guardian authorization at dispatch.',
                               'Verify matching running container AND the configured endpoint after dispatch.'), refs, snapshot.origin)
    if snapshot.health == 'unhealthy' and snapshot.container_state == 'running':
        return Recommendation('investigate_application', 'The container runs but its endpoint fails. Investigate application, dependency and probe configuration; no supported restart recommendation is justified.',
                              None, ('read',), False, general,
                              ('Collect causal evidence and review recent changes before proposing edits.',), refs, snapshot.origin)
    return Recommendation('review_observations', 'Review current observations and target consistency; no supported repair is established.',
                          None, ('read',), False, general, ('Do not infer repair permission from monitoring access.',), refs, snapshot.origin)
