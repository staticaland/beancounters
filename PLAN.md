# Plan: Making the Test Repository More Realistic

This document outlines step-by-step improvements to make the beancounters test repository more realistic and useful for testing beancount importers.

## Current State Summary

- **3 importers**: SpareBank1 (CSV), DNB Mastercard (Excel), American Express (QBO)
- **21 test files**: 7 files per bank covering Jan-Jun 2025 + overlap files
- **No unit tests**: pytest is listed as dev dependency but unused
- **Limited diversity**: ~20 transactions per month with templated patterns
- **Basic CI**: GitHub Actions workflow runs extract but doesn't validate

---

## Phase 1: Expand Test Data Diversity

### 1.1 Add edge case transactions to SpareBank1 CSV files
- [ ] Add transactions with special characters in descriptions (æ, ø, å, &, quotes)
- [ ] Add transactions with very long descriptions (100+ characters)
- [ ] Add transactions with empty/missing optional fields
- [ ] Add zero-amount transactions (adjustments)
- [ ] Add transactions with unusual decimal amounts (3+ decimal places)

### 1.2 Add edge case transactions to DNB Excel files
- [ ] Add transactions with special characters and Unicode
- [ ] Add transactions with extremely large amounts (100,000+ NOK)
- [ ] Add transactions with very small amounts (0.01 NOK)
- [ ] Add transactions on weekend/holiday dates
- [ ] Add rows with partial data (missing columns)

### 1.3 Add edge case transactions to Amex QBO files
- [ ] Add transactions with long memo fields
- [ ] Add transactions with special XML characters (&, <, >, quotes)
- [ ] Add refund transactions (positive amounts)
- [ ] Add foreign currency transactions if supported
- [ ] Add transactions with unusual FITID formats

### 1.4 Increase merchant diversity
- [x] Add 20+ more unique merchant names to each bank's files
- [x] Add merchants that should NOT match existing patterns (test uncategorized)
- [x] Add merchants with similar names (test regex specificity)
- [x] Add merchants with inconsistent casing (KIWI vs Kiwi vs kiwi)

---

## Phase 2: Create Unit Test Infrastructure

### 2.1 Set up test directory structure
- [x] Create `tests/` directory
- [x] Create `tests/__init__.py`
- [x] Create `tests/conftest.py` with shared fixtures
- [x] Add `pytest.ini` or update `pyproject.toml` with pytest configuration

### 2.2 Create test fixtures
- [ ] Create `tests/fixtures/` directory
- [ ] Add minimal valid CSV sample for SpareBank1
- [ ] Add minimal valid Excel sample for DNB
- [ ] Add minimal valid QBO sample for Amex
- [ ] Add malformed/invalid samples for each format

### 2.3 Add importer configuration tests
- [x] Test that `get_importers()` returns expected number of importers
- [x] Test that each importer has correct account configuration
- [x] Test that pattern matching rules are properly defined
- [x] Test importer identification (file type detection)

---

## Phase 3: Add Pattern Matching Tests

### 3.1 Create SpareBank1 pattern tests
- [x] Test simple string matching (KIWI → Groceries)
- [x] Test regex patterns (REMA\s*1000)
- [x] Test field-based matching (to_account)
- [x] Test counterparty matching (salary)
- [x] Test default account assignment for unmatched transactions
- [x] Test case sensitivity behavior

### 3.2 Create DNB pattern tests
- [x] Test case-insensitive matching (starbucks)
- [x] Test balance forward skipping
- [x] Test multiple patterns for same category
- [x] Test pattern priority (most specific wins)

### 3.3 Create Amex pattern tests
- [x] Test pattern matching for all configured patterns
- [x] Test credit vs debit transaction handling
- [x] Test transactions that should remain uncategorized

---

## Phase 4: Add Integration Tests

### 4.1 Create end-to-end import tests
- [x] Test full import of SpareBank1 January file
- [x] Test full import of DNB January file
- [x] Test full import of Amex January file
- [x] Verify output is valid beancount syntax
- [x] Verify all transactions are present in output

### 4.2 Add deduplication tests
- [ ] Test that overlapping file imports identify duplicates
- [ ] Test duplicate detection across different files
- [ ] Test that unique transactions in overlap period are preserved
- [ ] Verify duplicate markers are correctly applied

### 4.3 Add validation tests
- [ ] Test that imported beancount files pass `bean-check`
- [ ] Test that account names are valid
- [ ] Test that amounts balance correctly
- [ ] Test that dates are in correct format

---

## Phase 5: Improve Test Data Realism

### 5.1 Add temporal patterns
- [ ] Add recurring transactions (same merchant, monthly)
- [ ] Add salary deposits on consistent dates (e.g., 25th of month)
- [ ] Add seasonal spending patterns (more shopping in December)
- [ ] Add vacation periods with travel-related spending

### 5.2 Add realistic amount distributions
- [ ] Grocery transactions: 100-800 NOK range
- [ ] Coffee transactions: 40-80 NOK range
- [ ] Subscription transactions: exact recurring amounts
- [ ] Salary: consistent amounts with occasional bonuses
- [ ] Create transactions that form realistic monthly budgets

### 5.3 Add inter-account transfers
- [ ] Add matching transfers between SpareBank1 checking and savings
- [ ] Add credit card payments from checking account
- [ ] Add mortgage payments from checking to mortgage account (recurring monthly)
- [ ] Add rent payments (alternative to mortgage for diverse scenarios)
- [ ] Add loan payments (car loan, student loan) from checking account
- [ ] Add automatic investment/savings transfers (recurring)
- [ ] Add utility bill payments (electricity, internet, water)
- [ ] Add insurance premium payments (car, home, health insurance)
- [ ] Ensure transfer pairs have matching amounts and dates

---

## Phase 6: Enhance CI/CD Pipeline

### 6.1 Add test execution to CI
- [x] Add pytest step to GitHub Actions workflow
- [ ] Configure test coverage reporting
- [ ] Add coverage threshold requirement (e.g., 80%)
- [ ] Upload coverage reports as artifacts

### 6.2 Add beancount validation to CI
- [ ] Add step to run `bean-check` on main.beancount
- [ ] Add step to validate all imported files
- [ ] Fail CI if any validation errors occur

### 6.3 Add import diff checking
- [ ] Store expected output for each test file
- [ ] Compare actual import output to expected
- [ ] Fail on unexpected changes (regression detection)

---

## Phase 6.4: Demo Queries in CI Summary

Display useful spending insights in the GitHub Actions summary using `bean-query`.

### 6.4.1 Create demo query scripts
- [ ] Create `scripts/` directory for query scripts
- [ ] Create `scripts/run-demo-queries.sh` to run all demo queries
- [ ] Add query: Monthly coffee spending
- [ ] Add query: Monthly transport/commute spending
- [ ] Add query: Subscriptions by month (streaming, music, internet, dev tools)
- [ ] Add query: Quarterly spending summary by category
- [ ] Add query: Top merchants by total spending

### 6.4.2 Format query output for GitHub summary
- [ ] Format results as markdown tables
- [ ] Add section headers and descriptions
- [ ] Handle empty results gracefully
- [ ] Add trend indicators (if possible)

### 6.4.3 Integrate with GitHub Actions workflow
- [ ] Add step to run demo queries after import
- [ ] Output query results to `$GITHUB_STEP_SUMMARY`
- [ ] Add collapsible sections for detailed breakdowns
- [ ] Include total counts and amounts

---

## Phase 7: Documentation and Examples

### 7.1 Add test writing guide
- [ ] Document how to add new test cases
- [ ] Document fixture usage patterns
- [ ] Document how to add new merchant patterns

### 7.2 Add troubleshooting examples
- [ ] Create sample problematic files that fail import
- [ ] Document common import errors and fixes
- [ ] Add examples of pattern matching debugging

### 7.3 Improve README
- [ ] Add section on running tests
- [ ] Add section on adding new test data
- [ ] Document the purpose of each test data file

---

## Phase 8: Advanced Testing Scenarios

### 8.1 Add malformed input tests
- [ ] Create CSV with wrong delimiter
- [ ] Create CSV with missing header row
- [ ] Create Excel file with wrong sheet name
- [ ] Create QBO with invalid XML
- [ ] Create files with wrong encoding (not UTF-8)

### 8.2 Add boundary condition tests
- [ ] Empty files (headers only)
- [ ] Single transaction files
- [ ] Files with 1000+ transactions
- [ ] Files spanning year boundaries (Dec → Jan)
- [ ] Files with transactions on leap day (Feb 29)

### 8.3 Add concurrency tests
- [ ] Test importing multiple files simultaneously
- [ ] Test file locking behavior
- [ ] Test output file collision handling

---

## Priority Order

For maximum impact, implement phases in this order:

1. **Phase 2** (Test Infrastructure) - Foundation for all other tests
2. **Phase 3** (Pattern Matching Tests) - Validates core functionality
3. **Phase 6.1-6.2** (CI Testing) - Catches regressions automatically
4. **Phase 1** (Edge Cases in Data) - Improves test coverage
5. **Phase 4** (Integration Tests) - End-to-end validation
6. **Phase 5** (Realistic Data) - Better simulation of real usage
7. **Phase 7** (Documentation) - Helps contributors
8. **Phase 8** (Advanced Scenarios) - Edge case handling

---

## Success Metrics

- [ ] All existing test data imports without errors
- [ ] Test coverage reaches 80%+
- [ ] CI catches import regressions
- [ ] Pattern matching accuracy is verified for all configured patterns
- [ ] Documentation enables easy contribution of new test cases
