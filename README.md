# beancounters

Demo project showing how to use Norwegian Beancount importers together.

## Included Importers

- **beancount-no-sparebank1** - SpareBank 1 deposit accounts (CSV)
- **beancount-no-dnb** - DNB Mastercard (Excel)
- **beancount-no-amex** - American Express Norway (QBO)

## Demo Data

The `data/` directory contains sample bank statements:

```
data/
├── sparebank1/transactions.csv    # SpareBank 1 CSV export
├── dnb/statement.xlsx             # DNB Mastercard Excel export
└── amex/activity.qbo              # American Express QBO export
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
uv run import-transactions extract data/ > imports/2025-02.beancount
```

### 4. View in Fava

```bash
uv run fava main.beancount
```

Open http://localhost:5000 in your browser.

## Project Structure

```
beancounters/
├── pyproject.toml
├── main.beancount           # Main ledger file
├── data/                    # Demo bank statements
│   ├── sparebank1/
│   ├── dnb/
│   └── amex/
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
