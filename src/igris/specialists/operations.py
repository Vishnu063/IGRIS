from types import MappingProxyType
from .contracts import Specialist

PROFILES = MappingProxyType({
    'research': Specialist('research', 'research_plan', 'Evidence and source research plan',
                           ('Separate primary evidence, secondhand claims and assumptions.', 'Never invent sources, customer demand or research results.')),
    'project_manager': Specialist('project_manager', 'project_plan', 'Project scope and sequencing plan',
                                  ('Translate supplied requirements into acceptance criteria.', 'Report blockers and estimates without client commitments.')),
    'incident_response': Specialist('incident_response', 'incident_plan', 'Incident coordination plan',
                                    ('Preserve evidence and distinguish observation from hypothesis.', 'Emergency language never bypasses Guardian or approvals.')),
    'voice_ai': Specialist('voice_ai', 'voice_plan', 'Voice interaction verification plan',
                           ('Plan push-to-talk, consent and multilingual engine tests.', 'No microphone activation, voice cloning or engine installation.')),
    'minimal_change': Specialist('minimal_change', 'minimal_change_plan', 'Minimum justified change plan',
                                 ('Locate the smallest change supported by supplied evidence.', 'Avoid unrelated refactors; document verification and remaining limitations.')),
})
