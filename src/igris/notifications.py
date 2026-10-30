"""Quiet-operation filtering; returns local data, never sends external messages."""
from .adapters.contracts import safe_text
EVENTS=frozenset({'approval_needed','critical_issue','security_event','milestone','completed','blocked'})

def notification(event, message, *, meaningful=False):
    if type(event) is not str:raise ValueError('Invalid event.')
    if event not in EVENTS:return None
    if event=='milestone' and meaningful is not True:return None
    return {'event':event,'message':safe_text(message,1024),
            'priority':'high' if event in ('approval_needed','critical_issue','security_event','blocked') else 'normal'}
