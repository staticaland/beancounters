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

### 4. View in Fava

```bash
uv run fava main.beancount
```

Open http://localhost:5000 in your browser.

### 5. Run demo queries

```bash
./scripts/run-demo-queries.sh main.beancount
```

The query report includes spending summaries plus loan insights for mortgage
principal, interest, and extra repayments.

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
    └── importers.py         # Importer configuration
```

## Importer Configuration

See `src/beancounters/importers.py` for the full configuration. Key features demonstrated:

### Pattern Matching

```python
match("KIWI") >> "Expenses:Groceries"
match(r"REMA\s*1000").regex >> "Expenses:Groceries"
match("starbucks").ignorecase >> "Expenses:Coffee"
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
