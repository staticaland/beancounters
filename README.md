# beancounters

Demo project showing how to use Norwegian Beancount importers together.

## Included Importers

- **beancount-no-sparebank1** - SpareBank 1 deposit accounts (CSV)
- **beancount-no-dnb** - DNB Mastercard (Excel)
- **beancount-no-amex** - American Express Norway (QBO)

## Demo Data

The `data/` directory contains the canonical generated Demo Dataset for a
synthetic 2025 household. It is checked in so the demo works immediately, but
the source of truth is the deterministic generator in
`scripts/generate_demo_data.py`.

The dataset covers salary, rent, savings transfers, debit-card spending,
credit-card purchases, refunds, subscriptions, groceries, transport, shopping,
travel, coffee, services, mortgage repayment, and uncategorized examples.
SpareBank 1 checking payments to DNB Mastercard and American Express line up
with the prior card activity where practical.

Each provider has twelve monthly exports plus one February 15 to April 15
overlap export for deduplication:

```
data/
├── sparebank1/
│   ├── 2025-01.csv
│   ├── ...
│   ├── 2025-12.csv
│   └── 2025-02-15_to_2025-04-15.csv
├── dnb/
│   ├── 2025-01.xlsx
│   ├── ...
│   ├── 2025-12.xlsx
│   └── 2025-02-15_to_2025-04-15.xlsx
└── amex/
    ├── 2025-01.qbo
    ├── ...
    ├── 2025-12.qbo
    └── 2025-02-15_to_2025-04-15.qbo
```

The generator also writes `generated/2025-mortgage.beancount`, which contains
the split principal and interest postings needed for mortgage repayment
analytics. Provider exports stay transaction-only importer inputs.

Regenerate the checked-in statement files after changing the scenario:

```bash
uv run python scripts/generate_demo_data.py
```

## Quick Start

### 1. Install dependencies

```bash
uv sync
```

### 2. Preview imports

```bash
# Preview all files
uv run import-transactions extract data/

# Preview specific importer
uv run import-transactions extract data/sparebank1/
uv run import-transactions extract data/dnb/
uv run import-transactions extract data/amex/
```

### 3. Import transactions

```bash
uv run import-transactions extract data/ > imports/2025.beancount
```

### 4. Preserve split annotations after re-importing

When you re-import the same provider exports, keep your user-owned split
annotations by merging them from the previous import output into the fresh one:

```bash
uv run import-transactions extract data/ > imports/2025.fresh.beancount
uv run preserve-splits imports/2025.beancount imports/2025.fresh.beancount > imports/2025.preserved.beancount
mv imports/2025.preserved.beancount imports/2025.beancount
```

### 5. Generate split adjustments

```bash
uv run generate-splits --config main.beancount --year 2025 imports/2025.beancount > generated/2025-splits.beancount
```

### 6. View in Fava

```bash
uv run fava main.beancount
```

Open http://localhost:5000 in your browser.

### 7. Run demo queries

```bash
./scripts/run-demo-queries.sh main.beancount
```

The query report includes spending summaries plus loan insights for mortgage
principal, interest, and extra repayments.

## Split Expense Workflow

The demo ledger defines one split person:

```beancount
2020-01-01 open Assets:Receivable:Maria NOK
2020-01-01 custom "split-person" "maria" Assets:Receivable:Maria
```

Add `split` metadata to imported transactions when another person owes part of
the expense. The annotation describes the other person's owed share, not your
remaining share.

Every imported transaction carries identity metadata that the split tooling
uses to recognize the same transaction across re-imports: Amex transactions
have a provider-assigned `provider_transaction_id` (the OFX FITID), while
SpareBank 1 and DNB exports carry no provider ID, so those importers emit a
deterministic `import_fingerprint` derived from the row content. Never edit
these values.

A 50% grocery split:

```beancount
2025-02-03 * "COOP EXTRA GRONLAND"
  import_fingerprint: "42621a0bb00b5bc474110bc9"
  split: "maria:50%"
  split_note: "Shared weekly groceries"
  Assets:Bank:SpareBank1:Checking  -892.30 NOK
  Expenses:Groceries                892.30 NOK
```

A 100% pass-through expense:

```beancount
2025-02-12 * "XXL SPORT ALNA"
  import_fingerprint: "255053a94062c640d39d0654"
  split: "maria:100%"
  split_note: "Bought for Maria"
  Assets:Bank:SpareBank1:Checking  -1249.00 NOK
  Expenses:Shopping:Sports          1249.00 NOK
```

`generate-splits` reads those annotations and writes generated adjustment
transactions to the year-scoped support file:

```bash
uv run generate-splits --config main.beancount --year 2025 imports/2025.beancount > generated/2025-splits.beancount
```

For re-imports, write fresh importer output to a temporary file, preserve the
annotations from the old imported ledger, then replace the import file with the
merged output:

```bash
uv run import-transactions extract data/ > imports/2025.fresh.beancount
uv run preserve-splits imports/2025.beancount imports/2025.fresh.beancount > imports/2025.preserved.beancount
mv imports/2025.preserved.beancount imports/2025.beancount
uv run generate-splits --config main.beancount --year 2025 imports/2025.beancount > generated/2025-splits.beancount
```

Settlement payments are normal imported and classified transactions. Classify a
payment from Maria against the same receivable account instead of using a
separate settlement matcher:

```beancount
2025-02-20 * "Overforing fra Maria"
  Assets:Bank:SpareBank1:Checking   446.15 NOK
  Assets:Receivable:Maria          -446.15 NOK
```

Split v1 intentionally does not cover exact amount splits, recurring/default
split rules, refund semantics, automatic settlement matching, or annotation helpers.
Keep those cases explicit in the ledger for now.

## Project Structure

```
beancounters/
├── pyproject.toml
├── main.beancount           # Main ledger file
├── scripts/
│   ├── generate_demo_data.py # Deterministic demo data generator
│   └── run-demo-queries.sh   # Markdown query report
├── data/                    # Demo bank statements
│   ├── sparebank1/
│   ├── dnb/
│   └── amex/
├── generated/               # Generated ledger support files
├── imports/                 # Imported transactions
└── src/beancounters/
    ├── importers.py         # Importer configuration
    └── splits.py            # Split annotation preservation and generation
```

## Importer Configuration

See `src/beancounters/importers.py` for the full configuration. Key features demonstrated:

### Pattern Matching

Common merchant rules are defined once in `COMMON_PATTERNS` and reused by each
importer. Bank-specific settlement, income, and transfer rules stay next to the
importer that needs them.

```python
COMMON_PATTERNS = [
    match("KIWI") >> "Expenses:Groceries",
    match(r"REMA\s*1000").regex >> "Expenses:Groceries",
    match("STARBUCKS").ignorecase >> "Expenses:Coffee",
    match("SAS") >> "Expenses:Travel:Flights",
]

DNB_PATTERNS = COMMON_PATTERNS + [
    match("Innbetaling") >> "Assets:Bank:SpareBank1:Checking",
]
```

### Amount-Based Rules

```python
when(amount < 50) >> "Expenses:PettyCash"
when(amount.between(100, 500)) >> "Expenses:Medium"
```

### Field Matching (SpareBank 1)

```python
field(to_account="11112222333") >> "Assets:Savings"
counterparty("56712345678") >> "Income:Salary"
```

## Related Projects

- [beancount-no-sparebank1](https://github.com/staticaland/beancount-no-sparebank1)
- [beancount-no-dnb](https://github.com/staticaland/beancount-no-dnb)
- [beancount-no-amex](https://github.com/staticaland/beancount-no-amex)
- [beancount-classifier](https://github.com/staticaland/beancount-classifier)
