# Cost Guardian

Authorized budget is INR 0. Explicit integer paise, INR only; unknown prices,
positive estimates and paid-service activation (including a claimed free trial)
are denied. No runtime budget override or approval argument exists. Zero-cost
checks activate nothing and do not grant other permissions. Estimate inputs are
trusted operator data, not model assertions of free pricing.

Bounded in-memory audit covers API/cloud/infrastructure/resource estimates,
request/token/second/byte quantities, rejected and unknown requests. Estimated
totals include rejected requests to show potential demand; they are not spend.
Actual billing and spend remain unknown, because no billing/provider account is
connected. The gate is tested but no real model/cloud execution path exists to
claim billing enforcement across. Any future provider boundary must enforce this
gate immediately before activation, in addition to Guardian permissions and
action-bound approval. Source presence alone does not enforce external accounts.
