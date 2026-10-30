# Proposal assistance

`Proposal` produces a reviewable scope, estimated working days and suggested INR
price using supplied effort and rate, plus a disclosed 20% contingency. These are
heuristics, not market quotes. Delivery includes requirements, implementation,
tests, acceptance and approved handover; tax/hosting/change requests need review.

`ProposalGate` requests owner review bound to the proposal SHA-256 and recipient
alias. Changing either invalidates the single-use expiring approval. The trusted
owner reviews the actual draft locally, not only its hash. A rehearsal validates
approval without sending. `submit` always denies: there is no email, platform or
client transport. Neither a draft nor an approval counts as a submitted proposal.
