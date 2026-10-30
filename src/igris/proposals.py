"""Draft proposals and bind review to exact content; no submission transport."""
from dataclasses import dataclass
import hashlib
import re

from .business import safe_text
from .guardian.policy import Denied
from .opportunities import nonnegative_int


@dataclass(frozen=True)
class Proposal:
    requirements: str
    scope: tuple[str, ...]
    effort_hours: int
    hourly_rate_paise: int
    hours_per_day: int = 4

    def __post_init__(self):
        object.__setattr__(self, 'requirements', safe_text(self.requirements))
        if type(self.scope) is not tuple or not 1 <= len(self.scope) <= 20:
            raise ValueError('Explicit scope required.')
        object.__setattr__(self, 'scope', tuple(safe_text(s, 512) for s in self.scope))
        for value in (self.effort_hours, self.hours_per_day):
            if not nonnegative_int(value, 100000): raise ValueError('Positive effort and capacity required.')
        nonnegative_int(self.hourly_rate_paise)

    def draft(self):
        estimate = (self.effort_hours * self.hourly_rate_paise * 120 + 99) // 100
        days = (self.effort_hours + self.hours_per_day - 1) // self.hours_per_day
        return (f'DRAFT — estimates require owner review\nRequirements: {self.requirements}\n'
                + 'Scope:\n' + '\n'.join('- ' + s for s in self.scope)
                + f'\nEstimated working days: {days}\nSuggested price: INR {estimate // 100}.{estimate % 100:02d}'
                + '\nAssumptions: supplied effort/rate, 20% contingency, excludes taxes and hosting.'
                + '\nDelivery: confirm scope; implement; test; obtain acceptance; prepare approved handover.'
                + '\nChanges, expenses and production deployment require separate approval.')


def submission_action(proposal, recipient_alias):
    if type(proposal) is not Proposal or type(recipient_alias) is not str or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', recipient_alias):
        raise ValueError('Reviewed proposal and trusted recipient alias required.')
    return {'operation': 'message.send', 'arguments': {
        'recipient_alias': recipient_alias, 'channel': 'unconfigured',
        'body_sha256': hashlib.sha256(proposal.draft().encode()).hexdigest()}}


class ProposalGate:
    def __init__(self, policy, workspace, approvals):
        self.policy, self.workspace, self.approvals = policy, workspace, approvals

    def request(self, proposal, recipient_alias):
        return self.approvals.request(self.policy, self.workspace, submission_action(proposal, recipient_alias))

    def rehearse(self, proposal, recipient_alias, approval_id):
        self.approvals.consume(approval_id, self.policy, self.workspace, submission_action(proposal, recipient_alias))
        return {'approval_validated_only': True, 'submitted': False}

    def submit(self, *args, **kwargs):
        raise Denied('External proposal submission unavailable; no transport authorized or connected.')
