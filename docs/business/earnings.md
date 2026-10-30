# Earnings ledger

Private owner-only SQLite stores opportunity estimates, recorded proposal/client/
completion milestones, invoices, partial/full payments and expenses. INR integer
paise only, no floating point, FX, tax automation, bank or payment gateway.
Invoices require project completion; payment references are unique and total
payments cannot exceed an invoice. Confirmation requires an explicit trusted
owner assertion and non-sensitive evidence reference. No action here submits,
charges, spends or collects money. Historical expense recording needs no payment
execution permission because it executes no transaction.

`actual_profit_paise` means owner-recorded confirmed receipts minus confirmed
expenses; it excludes all estimated revenue and unpaid invoices. Confirmation is
not bank-verified. Tests use synthetic receipts only: no real earnings occurred.
Counts are per project/deal (clients_acquired counts acquisitions, not deduplicated
human identities). Changes/refunds, multi-currency, invoice scheduling and legal
accounting are outside this limited ledger. Do not store full financial documents
or personal information. Backups must remain private and follow retention rules.
