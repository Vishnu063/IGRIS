"""INR 0 planning gate. Does not activate services or assert real billing data."""
from dataclasses import dataclass

from .guardian.policy import Denied
from .opportunities import nonnegative_int


@dataclass(frozen=True)
class CostEstimate:
    category: str
    amount_paise: int | None
    quantity: int = 0
    unit: str = 'requests'
    paid_service: bool = False
    currency: str = 'INR'

    def __post_init__(self):
        if self.category not in ('api', 'cloud', 'infrastructure', 'resource') or self.unit not in ('requests', 'tokens', 'seconds', 'bytes'):
            raise ValueError('Unsupported cost category/unit.')
        if self.currency != 'INR' or type(self.paid_service) is not bool:
            raise ValueError('Explicit INR cost and service classification required.')
        if self.amount_paise is not None: nonnegative_int(self.amount_paise)
        nonnegative_int(self.quantity, 10**15)


class CostGuardian:
    """Trusted estimates only. A zero estimate is not external price verification.

    No approval parameter can increase the plan's zero budget. Future spending
    needs a separate owner-authorized budget and verified execution boundary.
    """
    @property
    def authorized_budget_paise(self): return 0

    def __init__(self): self._records = []

    def check(self, estimate):
        if type(estimate) is not CostEstimate: raise Denied('Verified cost estimate required.')
        allowed = estimate.amount_paise == 0 and not estimate.paid_service
        if len(self._records) >= 10000: raise Denied('Cost audit capacity reached.')
        self._records.append((estimate, allowed))
        if not allowed: raise Denied('INR 0 budget: unknown costs, paid services and positive spending denied.')
        return {'allowed_by_zero_budget_only': True, 'service_activated': False}

    def report(self):
        return {'currency': 'INR', 'authorized_budget_paise': 0,
                'estimated_requests': len(self._records),
                'rejected_requests': sum(not allowed for _, allowed in self._records),
                'unknown_estimates': sum(e.amount_paise is None for e, _ in self._records),
                'estimated_total_paise': sum(e.amount_paise or 0 for e, _ in self._records),
                'actual_billing_verified': False, 'actual_spend_paise': None}
