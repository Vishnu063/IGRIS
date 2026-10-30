from types import MappingProxyType
from .contracts import Specialist

PROFILES = MappingProxyType({
    'security_privacy': Specialist('security_privacy', 'security_review', 'Security and privacy review plan',
                                   ('Identify trust boundaries and personal-data flows in supplied material.',
                                    'Separate confirmed evidence from hypotheses; no security certification.')),
    'testing': Specialist('testing', 'test_plan', 'Targeted testing plan',
                          ('Select meaningful positive and negative cases.', 'Report real, simulated and untested coverage separately.')),
    'code_reviewer': Specialist('code_reviewer', 'code_review', 'Code review plan',
                                ('Link findings to supplied code and impact.', 'Do not merge, approve execution or invent test results.')),
    'ui_ux': Specialist('ui_ux', 'ux_plan', 'UI and accessibility review plan',
                        ('Review user journeys, labels and accessibility.', 'Recommend only requirements justified by the supplied scope.')),
    'database': Specialist('database', 'database_plan', 'Database design and recovery plan',
                           ('Propose schema validation and recoverability tests.', 'No migration, deletion, failover or restore without separate execution controls.')),
})
