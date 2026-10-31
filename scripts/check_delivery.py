"""Verify repository handover contents without starting any external service."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from igris.config import load_settings

REQUIRED = (
    'README.md', 'THIRD_PARTY_NOTICES.md', '.env.example',
    'docs/architecture/overview.md', 'docs/architecture/hardware-budget.md',
    'docs/security/guardian-design.md', 'docs/security/permissions.md',
    'docs/security/execution.md', 'docs/security/approvals.md',
    'docs/security/validation.md', 'docs/security/cost-guardian.md',
    'docs/delivery/setup.md', 'docs/delivery/mac-plan.md', 'docs/delivery/final-report.md',
    'docs/delivery/status.json', 'docs/validation/integration-matrix.md',
    'docs/validation/code-review.md', 'docs/validation/performance-step48.json',
    'docs/integrations/ops-pilot-audit.md', 'docs/integrations/ops-monitoring.md',
    'docs/integrations/approved-recovery.md', 'docs/integrations/n8n.md',
    'docs/integrations/voice-audit.md', 'docs/integrations/voice-guidance.md',
    'docs/integrations/business-tools.md', 'docs/business/README.md',
    'docs/business/proposals.md', 'docs/business/delivery.md', 'docs/business/earnings.md',
    'docs/architecture/memory.md', 'docs/architecture/mission-control.md',
    'docs/architecture/backup-recovery.md', 'docs/specialists/README.md',
    'vendor/hermes-agent/LICENSE', 'vendor/agency-agents/LICENSE',
    'workflows/n8n-readonly-fixture.json', '.github/workflows/ci.yml',
)


def check():
    for name in REQUIRED:
        path = ROOT/name
        assert path.is_file() and not path.is_symlink() and path.stat().st_size > 0, name
    fields = ('Title:', 'Status:', 'Implemented:', 'Files changed:', 'Commands executed:',
              'Tests executed:', 'Test results:', 'Security review:', 'Git commit:',
              'Known limitations:', 'Next step:', 'Approval required:')
    for step in range(1, 51):
        text = (ROOT/f'docs/execution/step-{step:02d}.md').read_text()
        assert 'IGRIS EXECUTION REPORT' in text
        assert re.search(rf'Step:\s*0?{step}\s*/\s*50', text), step
        assert all(field in text for field in fields), step
        assert re.search(r'Status: (PASS|FAIL|BLOCKED|PENDING_EXTERNAL_VERIFICATION)\b', text), step
    for profile in ('development', 'test'):
        settings = load_settings(profile, environ={})
        assert settings.budget_inr == 0 and not any(vars(settings.features).values())
    workflow = json.loads((ROOT/'workflows/n8n-readonly-fixture.json').read_text())
    assert workflow['active'] is False
    assert workflow['nodes'][0]['parameters']['authentication'] == 'headerAuth'
    status = json.loads((ROOT/'docs/delivery/status.json').read_text())
    assert status['numbered_step_records'] == 50 and status['verified_tests'] == 166
    assert status['operational_assistant_status'] == 'PENDING_EXTERNAL_VERIFICATION'
    assert status['authorized_spending_inr'] == 0
    for key in ('live_model_connections_verified', 'paid_services_activated', 'production_deployed',
                'mac_installed', 'mac_m1_verified', 'hosted_github_actions_dispatched'):
        assert status[key] is False, key
    hermes = json.loads((ROOT/'docs/integrations/hermes-source-manifest.json').read_text())
    assert len(hermes['local_sha256']) == 2674
    for name, digest in hermes['local_sha256'].items():
        path = ROOT/'vendor/hermes-agent'/name
        assert not path.is_symlink() and path.resolve().is_relative_to(ROOT/'vendor/hermes-agent')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    agency = json.loads((ROOT/'integrations/agency-agents/manifest.json').read_text())
    assert len(agency['roles']) == 15
    for role, item in agency['roles'].items():
        original = ROOT/'vendor/agency-agents'/item['source']
        adapted = ROOT/item['adapted']
        assert hashlib.sha256(original.read_bytes()).hexdigest() == item['source_sha256'], role
        assert hashlib.sha256(adapted.read_bytes()).hexdigest() == item['adapted_sha256'], role
    print(f'PASS: {len(REQUIRED)} required deliverables, 50 report formats, disabled profiles/inactive workflow, truthful runtime status, 2674 Hermes hashes and 15 original/adapted specialist pairs.')


if __name__ == '__main__': check()
