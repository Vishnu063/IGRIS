from types import MappingProxyType
from .contracts import Specialist

PROFILES = MappingProxyType({
    'frontend': Specialist('frontend', 'frontend_plan', 'Frontend implementation plan',
                          ('Review supplied UI requirements and accessibility.', 'Propose scoped components and browser tests.')),
    'backend': Specialist('backend', 'backend_plan', 'Backend API plan',
                         ('Define input validation and authorization boundaries.', 'Propose API contracts and failure tests.')),
    'mobile': Specialist('mobile', 'mobile_plan', 'Mobile application plan',
                        ('Identify target platforms and offline needs.', 'Keep SDK installs, purchases and device validation pending.')),
    'ai_engineer': Specialist('ai_engineer', 'ai_plan', 'AI integration plan',
                             ('Specify an evaluation dataset and uncertainty.', 'Do not invoke paid inference or download models.')),
    'devops': Specialist('devops', 'devops_plan', 'DevOps change plan',
                        ('Review declared environment and rollback evidence.', 'Keep production, cloud costs and execution approval-gated.')),
})
