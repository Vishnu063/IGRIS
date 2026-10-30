"""Evaluate supplied evidence, never invent listings or market demand."""
from dataclasses import dataclass

from .business import FOCUS, safe_text


def nonnegative_int(value, maximum=10**12):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Expected bounded nonnegative integer.')
    return value


@dataclass(frozen=True)
class Evidence:
    source: str
    observation: str
    origin: str  # sample or operator_supplied, not independently verified

    def __post_init__(self):
        if self.origin not in ('sample', 'operator_supplied'):
            raise ValueError('Unsupported evidence origin.')
        object.__setattr__(self, 'source', safe_text(self.source, 512))
        object.__setattr__(self, 'observation', safe_text(self.observation))


@dataclass(frozen=True)
class Opportunity:
    focus: str
    requirements: str
    feasible_score: int
    competition_score: int
    effort_hours: int
    expense_paise: int
    possible_revenue_paise: int
    risks: tuple[str, ...]
    demand_evidence: tuple[Evidence, ...] = ()

    def __post_init__(self):
        if self.focus not in FOCUS:
            raise ValueError('Unsupported focus.')
        object.__setattr__(self, 'requirements', safe_text(self.requirements))
        for value in (self.feasible_score, self.competition_score): nonnegative_int(value, 5)
        nonnegative_int(self.effort_hours, 100000)
        for value in (self.expense_paise, self.possible_revenue_paise): nonnegative_int(value)
        if type(self.risks) is not tuple or not 1 <= len(self.risks) <= 20:
            raise ValueError('Document risks.')
        object.__setattr__(self, 'risks', tuple(safe_text(r, 512) for r in self.risks))
        if type(self.demand_evidence) is not tuple or len(self.demand_evidence) > 20 or any(type(e) is not Evidence for e in self.demand_evidence):
            raise ValueError('Invalid evidence.')


def evaluate(opportunity):
    if type(opportunity) is not Opportunity:
        raise ValueError('Expected opportunity.')
    return {
        'research_status': 'supplied_evidence_requires_review' if opportunity.demand_evidence else 'needs_market_research',
        'evidence_origins': tuple(e.origin for e in opportunity.demand_evidence),
        'market_demand_verified': False,
        'feasibility_score': opportunity.feasible_score,
        'competition_score': opportunity.competition_score,
        'effort_hours_estimate': opportunity.effort_hours,
        'estimated_margin_paise': opportunity.possible_revenue_paise - opportunity.expense_paise,
        'spending_required': opportunity.expense_paise > 0,
        'currency': 'INR', 'estimated_only': True,
        'risks': opportunity.risks,
    }
