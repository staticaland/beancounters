# Beancounters

Beancounters is a personal finance ledger demo for Norwegian Beancount importers and derived ledger support files.

## Language

**Split Expense**:
An expense paid in one transaction but allocated between the owner and one or more other people.
_Avoid_: Shared transaction, split transaction

**Receivable**:
Money another person owes back to the owner after the owner paid more than their share.
_Avoid_: Loan, IOU, debt

**Split Person**:
A named person who can owe a split share and is mapped to an opened receivable account in the ledger. Split person keys are simple case-insensitive slugs normalized to lowercase in generated output.
_Avoid_: Partner, friend, participant

**Split Annotation**:
User-owned metadata on an imported transaction that describes the share owed back by another person. A transaction may have multiple split annotations, and a `100%` split means the named person owes the full transaction amount.
_Avoid_: Split rule, YAML split, importer rule

**Split Note**:
Optional user-owned metadata on an imported transaction that explains the context for a split without affecting accounting. A split note is valid only on transactions with at least one split annotation.
_Avoid_: Group, project, settlement note

**Split Share**:
The portion of a transaction owed by another person in a split annotation. Percentages may be written with or without `%`, generated output uses the explicit `%` form, total split shares above `100%` are invalid, and owed amounts round to the currency precision with any remainder left in the owner's expense.
_Avoid_: Ratio, allocation amount

**Splittable Transaction**:
An imported transaction with exactly one expense posting that can be adjusted by split annotations.
_Avoid_: Eligible transaction, simple transaction

**Settlement**:
An incoming or outgoing payment that reduces a receivable balance with another person.
_Avoid_: Repayment match, reimbursement link

**Split Adjustment**:
A generated transaction that moves other people's owed shares from the owner's expense account to their receivable accounts. One splittable transaction produces one combined split adjustment, even when multiple split people owe shares.
_Avoid_: Rewritten import, corrected transaction

**Split Link**:
A deterministic Beancount link shared by an imported transaction and its generated split adjustments. Split links use provider transaction IDs when available and import fingerprints otherwise.
_Avoid_: Trace ID, adjustment ID

**Import Fingerprint**:
A deterministic identity for an imported transaction when the provider does not supply a stable transaction ID. Importers emit it as `import_fingerprint` metadata, derived from row content (never file name or line number) plus an occurrence counter for identical rows, so the same transaction keeps its identity across overlapping exports. Providers with real transaction IDs emit `provider_transaction_id` instead (Amex uses the OFX FITID).
_Avoid_: Hash, heuristic match, duplicate key
