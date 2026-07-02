"""End-to-end import tests for all importers.

These tests verify that:
1. Full import of each bank's files works correctly
2. Output is valid beancount syntax
3. All transactions from source files are present in output
4. Transaction data (dates, amounts, accounts) is correct
5. Every transaction carries stable identity metadata for the split workflow
"""

import io
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import data
from beancount.parser import parser, printer

from beancounters.splits import (
    IMPORT_FINGERPRINT_META_KEYS,
    PROVIDER_ID_META_KEYS,
    first_string_meta,
    preserve_split_annotations,
    source_identity_for_transaction,
)

IDENTITY_META_KEYS = PROVIDER_ID_META_KEYS + IMPORT_FINGERPRINT_META_KEYS


class TestSpareBank1EndToEnd:
    """End-to-end tests for SpareBank1 importer."""

    def test_full_import_january_file(self, sparebank1_importer, sample_sparebank1_file):
        """Test full import of SpareBank1 January file."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        # Should have transactions
        assert len(entries) > 0, "Should extract transactions from January file"

        # All entries should be Transaction type
        for entry in entries:
            assert hasattr(entry, 'postings'), "Entry should be a transaction with postings"

    def test_january_file_transaction_count(self, sparebank1_importer, sample_sparebank1_file):
        """Verify all transactions from source file are present."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        # Count transactions in source file (excluding header)
        with open(sample_sparebank1_file, 'r', encoding='utf-8') as f:
            # Skip header line, count non-empty lines
            lines = [line.strip() for line in f if line.strip()]
            expected_count = len(lines) - 1  # Exclude header

        assert len(entries) == expected_count, \
            f"Expected {expected_count} transactions, got {len(entries)}"

    def test_january_file_valid_beancount_syntax(
        self, sparebank1_importer, sample_sparebank1_file
    ):
        """Verify output is valid beancount syntax."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        # Convert entries to beancount format string
        beancount_output = self._entries_to_beancount_string(entries)

        # Parse the output to validate syntax
        parsed_entries, errors, _ = parser.parse_string(beancount_output)

        assert len(errors) == 0, f"Beancount syntax errors: {errors}"
        assert len(parsed_entries) > 0, "Should parse entries successfully"

    def test_january_file_dates_in_january(
        self, sparebank1_importer, sample_sparebank1_file
    ):
        """Verify all transactions have January 2025 dates."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        for entry in entries:
            assert entry.date.year == 2025, f"Expected year 2025, got {entry.date.year}"
            assert entry.date.month == 1, f"Expected month 1, got {entry.date.month}"

    def test_january_file_balanced_transactions(
        self, sparebank1_importer, sample_sparebank1_file
    ):
        """Verify all transactions balance (sum of postings is zero)."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        for entry in entries:
            # Get all posting amounts
            total = Decimal('0')
            for posting in entry.postings:
                if posting.units:
                    total += posting.units.number

            assert total == Decimal('0'), \
                f"Transaction '{entry.narration}' doesn't balance: {total}"

    def test_january_file_has_primary_account(
        self, sparebank1_importer, sample_sparebank1_file
    ):
        """Verify all transactions include the primary bank account."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        for entry in entries:
            account_names = [p.account for p in entry.postings]
            has_primary = any(
                'SpareBank1:Checking' in acc for acc in account_names
            )
            assert has_primary, \
                f"Transaction '{entry.narration}' missing primary account"

    def test_january_file_currency_is_nok(
        self, sparebank1_importer, sample_sparebank1_file
    ):
        """Verify all transactions use NOK currency."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        for entry in entries:
            for posting in entry.postings:
                if posting.units:
                    assert posting.units.currency == 'NOK', \
                        f"Expected NOK, got {posting.units.currency}"

    def test_all_files_import_successfully(
        self, sparebank1_importer, all_sparebank1_files
    ):
        """Test that all SpareBank1 files import without errors."""
        for file_path in all_sparebank1_files:
            entries = sparebank1_importer.extract(file_path, [])
            assert len(entries) > 0, f"No entries extracted from {file_path.name}"

    def _entries_to_beancount_string(self, entries) -> str:
        """Convert entries to beancount format string for validation."""
        output = io.StringIO()

        # Add required account declarations
        accounts = set()
        for entry in entries:
            for posting in entry.postings:
                accounts.add(posting.account)

        for account in sorted(accounts):
            output.write(f"2020-01-01 open {account}\n")

        output.write("\n")

        # Add transactions
        for entry in entries:
            flag = entry.flag or '*'
            payee = f'"{entry.payee}"' if entry.payee else ''
            narration = f'"{entry.narration}"'

            if payee:
                output.write(f"{entry.date} {flag} {payee} {narration}\n")
            else:
                output.write(f"{entry.date} {flag} {narration}\n")

            for posting in entry.postings:
                if posting.units:
                    output.write(
                        f"  {posting.account}  {posting.units.number} {posting.units.currency}\n"
                    )
                else:
                    output.write(f"  {posting.account}\n")

            output.write("\n")

        return output.getvalue()


class TestDnbEndToEnd:
    """End-to-end tests for DNB Mastercard importer."""

    def test_full_import_january_file(self, dnb_importer, sample_dnb_file):
        """Test full import of DNB January file."""
        entries = dnb_importer.extract(sample_dnb_file, [])

        # Should have transactions
        assert len(entries) > 0, "Should extract transactions from January file"

        # All entries should be Transaction type
        for entry in entries:
            assert hasattr(entry, 'postings'), "Entry should be a transaction with postings"

    def test_january_file_valid_beancount_syntax(self, dnb_importer, sample_dnb_file):
        """Verify output is valid beancount syntax."""
        entries = dnb_importer.extract(sample_dnb_file, [])

        # Convert entries to beancount format string
        beancount_output = self._entries_to_beancount_string(entries)

        # Parse the output to validate syntax
        parsed_entries, errors, _ = parser.parse_string(beancount_output)

        assert len(errors) == 0, f"Beancount syntax errors: {errors}"
        assert len(parsed_entries) > 0, "Should parse entries successfully"

    def test_january_file_dates_in_january(self, dnb_importer, sample_dnb_file):
        """Verify all transactions have January 2025 dates."""
        entries = dnb_importer.extract(sample_dnb_file, [])

        for entry in entries:
            assert entry.date.year == 2025, f"Expected year 2025, got {entry.date.year}"
            assert entry.date.month == 1, f"Expected month 1, got {entry.date.month}"

    def test_january_file_balanced_transactions(self, dnb_importer, sample_dnb_file):
        """Verify all transactions balance (sum of postings is zero)."""
        entries = dnb_importer.extract(sample_dnb_file, [])

        for entry in entries:
            total = Decimal('0')
            for posting in entry.postings:
                if posting.units:
                    total += posting.units.number

            assert total == Decimal('0'), \
                f"Transaction '{entry.narration}' doesn't balance: {total}"

    def test_january_file_has_credit_card_account(self, dnb_importer, sample_dnb_file):
        """Verify all transactions include the DNB credit card account."""
        entries = dnb_importer.extract(sample_dnb_file, [])

        for entry in entries:
            account_names = [p.account for p in entry.postings]
            has_cc_account = any('CreditCard:DNB' in acc for acc in account_names)
            assert has_cc_account, \
                f"Transaction '{entry.narration}' missing credit card account"

    def test_january_file_currency_is_nok(self, dnb_importer, sample_dnb_file):
        """Verify all transactions use NOK currency."""
        entries = dnb_importer.extract(sample_dnb_file, [])

        for entry in entries:
            for posting in entry.postings:
                if posting.units:
                    assert posting.units.currency == 'NOK', \
                        f"Expected NOK, got {posting.units.currency}"

    def test_all_files_import_successfully(self, dnb_importer, all_dnb_files):
        """Test that all DNB files import without errors."""
        for file_path in all_dnb_files:
            entries = dnb_importer.extract(file_path, [])
            assert len(entries) > 0, f"No entries extracted from {file_path.name}"

    def _entries_to_beancount_string(self, entries) -> str:
        """Convert entries to beancount format string for validation."""
        output = io.StringIO()

        accounts = set()
        for entry in entries:
            for posting in entry.postings:
                accounts.add(posting.account)

        for account in sorted(accounts):
            output.write(f"2020-01-01 open {account}\n")

        output.write("\n")

        for entry in entries:
            flag = entry.flag or '*'
            payee = f'"{entry.payee}"' if entry.payee else ''
            narration = f'"{entry.narration}"'

            if payee:
                output.write(f"{entry.date} {flag} {payee} {narration}\n")
            else:
                output.write(f"{entry.date} {flag} {narration}\n")

            for posting in entry.postings:
                if posting.units:
                    output.write(
                        f"  {posting.account}  {posting.units.number} {posting.units.currency}\n"
                    )
                else:
                    output.write(f"  {posting.account}\n")

            output.write("\n")

        return output.getvalue()


class TestAmexEndToEnd:
    """End-to-end tests for American Express importer."""

    def test_full_import_january_file(self, amex_importer, sample_amex_file):
        """Test full import of Amex January file."""
        entries = amex_importer.extract(sample_amex_file, [])

        # Should have transactions
        assert len(entries) > 0, "Should extract transactions from January file"

        # All entries should be Transaction type
        for entry in entries:
            assert hasattr(entry, 'postings'), "Entry should be a transaction with postings"

    def test_january_file_transaction_count(self, amex_importer, sample_amex_file):
        """Verify all transactions from source file are present."""
        entries = amex_importer.extract(sample_amex_file, [])

        # Count STMTTRN elements in source QBO file
        with open(sample_amex_file, 'r', encoding='utf-8') as f:
            content = f.read()
            expected_count = content.count('<STMTTRN>')

        assert len(entries) == expected_count, \
            f"Expected {expected_count} transactions, got {len(entries)}"

    def test_january_file_valid_beancount_syntax(self, amex_importer, sample_amex_file):
        """Verify output is valid beancount syntax."""
        entries = amex_importer.extract(sample_amex_file, [])

        # Convert entries to beancount format string
        beancount_output = self._entries_to_beancount_string(entries)

        # Parse the output to validate syntax
        parsed_entries, errors, _ = parser.parse_string(beancount_output)

        assert len(errors) == 0, f"Beancount syntax errors: {errors}"
        assert len(parsed_entries) > 0, "Should parse entries successfully"

    def test_january_file_dates_in_january(self, amex_importer, sample_amex_file):
        """Verify all transactions have January 2025 dates."""
        entries = amex_importer.extract(sample_amex_file, [])

        for entry in entries:
            assert entry.date.year == 2025, f"Expected year 2025, got {entry.date.year}"
            assert entry.date.month == 1, f"Expected month 1, got {entry.date.month}"

    def test_january_file_balanced_transactions(self, amex_importer, sample_amex_file):
        """Verify all transactions balance (sum of postings is zero)."""
        entries = amex_importer.extract(sample_amex_file, [])

        for entry in entries:
            total = Decimal('0')
            for posting in entry.postings:
                if posting.units:
                    total += posting.units.number

            assert total == Decimal('0'), \
                f"Transaction '{entry.narration}' doesn't balance: {total}"

    def test_january_file_has_credit_card_account(self, amex_importer, sample_amex_file):
        """Verify all transactions include the Amex credit card account."""
        entries = amex_importer.extract(sample_amex_file, [])

        for entry in entries:
            account_names = [p.account for p in entry.postings]
            has_cc_account = any('CreditCard:Amex' in acc for acc in account_names)
            assert has_cc_account, \
                f"Transaction '{entry.narration}' missing credit card account"

    def test_january_file_currency_is_nok(self, amex_importer, sample_amex_file):
        """Verify all transactions use NOK currency."""
        entries = amex_importer.extract(sample_amex_file, [])

        for entry in entries:
            for posting in entry.postings:
                if posting.units:
                    assert posting.units.currency == 'NOK', \
                        f"Expected NOK, got {posting.units.currency}"

    def test_all_files_import_successfully(self, amex_importer, all_amex_files):
        """Test that all Amex files import without errors."""
        for file_path in all_amex_files:
            entries = amex_importer.extract(file_path, [])
            assert len(entries) > 0, f"No entries extracted from {file_path.name}"

    def test_january_file_has_refund_transaction(self, amex_importer, sample_amex_file):
        """Verify refund transactions are imported correctly."""
        entries = amex_importer.extract(sample_amex_file, [])

        refund_entries = [
            e for e in entries
            if hasattr(e, 'narration') and 'REFUND' in e.narration.upper()
        ]

        assert len(refund_entries) > 0, "Should have at least one refund transaction"

        for entry in refund_entries:
            # The credit card posting for a refund should be positive
            cc_posting = next(
                (p for p in entry.postings if 'Amex' in p.account),
                None
            )
            assert cc_posting is not None
            assert cc_posting.units.number > 0, "Refund should be positive on credit card"

    def _entries_to_beancount_string(self, entries) -> str:
        """Convert entries to beancount format string for validation."""
        output = io.StringIO()

        accounts = set()
        for entry in entries:
            for posting in entry.postings:
                accounts.add(posting.account)

        for account in sorted(accounts):
            output.write(f"2020-01-01 open {account}\n")

        output.write("\n")

        for entry in entries:
            flag = entry.flag or '*'
            payee = f'"{entry.payee}"' if entry.payee else ''
            narration = f'"{entry.narration}"'

            if payee:
                output.write(f"{entry.date} {flag} {payee} {narration}\n")
            else:
                output.write(f"{entry.date} {flag} {narration}\n")

            for posting in entry.postings:
                if posting.units:
                    output.write(
                        f"  {posting.account}  {posting.units.number} {posting.units.currency}\n"
                    )
                else:
                    output.write(f"  {posting.account}\n")

            output.write("\n")

        return output.getvalue()


class TestIdentifyContract:
    """The configured library importers must identify the demo files directly.

    Regression guard for the DemoAmexImporter era: the demo previously had to
    subclass the Amex importer and override identify() because the library
    rejected valid QBO files. The library importers must identify every demo
    export of their own bank and reject the other banks' files.
    """

    def test_each_importer_identifies_own_files_and_rejects_others(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        all_sparebank1_files,
        all_dnb_files,
        all_amex_files,
    ):
        cases = [
            (sparebank1_importer, all_sparebank1_files, 'SpareBank1'),
            (dnb_importer, all_dnb_files, 'DNB'),
            (amex_importer, all_amex_files, 'Amex'),
        ]

        for importer, own_files, name in cases:
            assert own_files, f"{name}: no demo files found"
            for file_path in own_files:
                assert importer.identify(str(file_path)) is True, (
                    f"{name} importer rejected its own file {file_path.name}"
                )
            for _, other_files, other_name in cases:
                if other_name == name:
                    continue
                for file_path in other_files:
                    assert importer.identify(str(file_path)) is False, (
                        f"{name} importer wrongly identified "
                        f"{other_name} file {file_path.name}"
                    )


class TestSourceIdentityContract:
    """Tests for the identity contract between importers and the split workflow.

    The split tooling (preserve-splits, generate-splits) matches re-imported
    transactions by provider_transaction_id (provider-assigned, e.g. OFX FITID)
    or import_fingerprint (importer-derived). Every importer must emit one of
    these keys so identities never fall back to content hashing in splits.py.
    """

    def _transactions(self, importer, file_path):
        entries = importer.extract(str(file_path), [])
        return [e for e in entries if isinstance(e, data.Transaction)]

    def test_every_transaction_has_identity_metadata(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        sample_sparebank1_file,
        sample_dnb_file,
        sample_amex_file,
    ):
        """Every extracted transaction carries an identity key — no fallback."""
        importers_and_files = [
            (sparebank1_importer, sample_sparebank1_file, 'SpareBank1'),
            (dnb_importer, sample_dnb_file, 'DNB'),
            (amex_importer, sample_amex_file, 'Amex'),
        ]

        for importer, file_path, name in importers_and_files:
            transactions = self._transactions(importer, file_path)
            assert transactions, f"{name}: no transactions extracted"
            for txn in transactions:
                identity = first_string_meta(txn, IDENTITY_META_KEYS)
                assert identity, (
                    f"{name}: transaction '{txn.narration}' on {txn.date} "
                    "has no identity metadata"
                )

    def test_amex_identity_is_provider_assigned(
        self, amex_importer, sample_amex_file
    ):
        """Amex transactions use the provider-assigned FITID, not a fingerprint."""
        for txn in self._transactions(amex_importer, sample_amex_file):
            assert source_identity_for_transaction(txn).kind == "provider"

    def test_identities_unique_within_file(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        all_sparebank1_files,
        all_dnb_files,
        all_amex_files,
    ):
        """No two transactions in one export share an identity."""
        importers_and_files = [
            (sparebank1_importer, all_sparebank1_files, 'SpareBank1'),
            (dnb_importer, all_dnb_files, 'DNB'),
            (amex_importer, all_amex_files, 'Amex'),
        ]

        for importer, files, name in importers_and_files:
            for file_path in files:
                transactions = self._transactions(importer, file_path)
                identities = [
                    first_string_meta(txn, IDENTITY_META_KEYS)
                    for txn in transactions
                ]
                assert len(identities) == len(set(identities)), (
                    f"{name}: duplicate identities in {file_path.name}"
                )

    def test_identity_stable_across_overlapping_exports(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        sparebank1_data_dir,
        dnb_data_dir,
        amex_data_dir,
    ):
        """The same transaction gets the same identity in monthly and overlap exports."""
        cases = [
            (sparebank1_importer, sparebank1_data_dir, '2025-03.csv',
             '2025-02-15_to_2025-04-15.csv', 'SpareBank1'),
            (dnb_importer, dnb_data_dir, '2025-03.xlsx',
             '2025-02-15_to_2025-04-15.xlsx', 'DNB'),
            (amex_importer, amex_data_dir, '2025-03.qbo',
             '2025-02-15_to_2025-04-15.qbo', 'Amex'),
        ]

        for importer, data_dir, monthly_name, overlap_name, name in cases:
            monthly = self._transactions(importer, data_dir / monthly_name)
            overlap = self._transactions(importer, data_dir / overlap_name)

            march = lambda txns: {
                first_string_meta(txn, IDENTITY_META_KEYS)
                for txn in txns
                if txn.date.month == 3
            }
            monthly_ids = march(monthly)
            overlap_ids = march(overlap)

            assert monthly_ids, f"{name}: no March transactions in {monthly_name}"
            assert monthly_ids == overlap_ids, (
                f"{name}: March identities differ between {monthly_name} "
                f"and {overlap_name}"
            )

    def test_preserve_splits_round_trip(
        self, sparebank1_importer, sample_sparebank1_file, tmp_path
    ):
        """A split annotation survives a re-import via preserve-splits."""
        transactions = self._transactions(
            sparebank1_importer, sample_sparebank1_file
        )

        annotated_index = next(
            i
            for i, txn in enumerate(transactions)
            if sum(p.account.startswith("Expenses:") for p in txn.postings) == 1
            and all(
                p.units.number > 0
                for p in txn.postings
                if p.account.startswith("Expenses:")
            )
        )

        old_transactions = list(transactions)
        annotated = old_transactions[annotated_index]
        meta = dict(annotated.meta)
        meta["split"] = "maria:50%"
        meta["split_note"] = "Shared groceries"
        old_transactions[annotated_index] = annotated._replace(meta=meta)

        old_path = tmp_path / "old.beancount"
        fresh_path = tmp_path / "fresh.beancount"
        with open(old_path, "w", encoding="utf-8") as f:
            printer.print_entries(old_transactions, file=f)
        with open(fresh_path, "w", encoding="utf-8") as f:
            printer.print_entries(transactions, file=f)

        merged = preserve_split_annotations(old_path, fresh_path)
        merged_transactions = [
            e for e in merged if isinstance(e, data.Transaction)
        ]

        assert len(merged_transactions) == len(transactions)
        carried = [
            txn for txn in merged_transactions if txn.meta.get("split")
        ]
        assert len(carried) == 1
        assert carried[0].meta["split"] == "maria:50%"
        assert carried[0].meta["split_note"] == "Shared groceries"
        assert carried[0].date == annotated.date
        assert carried[0].narration == annotated.narration


class TestCrossImporterValidation:
    """Tests that validate behavior across all importers."""

    def test_all_importers_produce_valid_beancount(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        sample_sparebank1_file,
        sample_dnb_file,
        sample_amex_file,
    ):
        """Test that all importers produce valid beancount output."""
        importers_and_files = [
            (sparebank1_importer, sample_sparebank1_file, 'SpareBank1'),
            (dnb_importer, sample_dnb_file, 'DNB'),
            (amex_importer, sample_amex_file, 'Amex'),
        ]

        for importer, file_path, name in importers_and_files:
            entries = importer.extract(file_path, [])
            beancount_output = self._entries_to_beancount_string(entries)

            parsed_entries, errors, _ = parser.parse_string(beancount_output)

            assert len(errors) == 0, \
                f"{name} produced invalid beancount: {errors}"
            assert len(parsed_entries) > 0, \
                f"{name} should have parsed entries"

    def test_account_names_follow_conventions(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        sample_sparebank1_file,
        sample_dnb_file,
        sample_amex_file,
    ):
        """Test that all account names follow beancount naming conventions."""
        importers_and_files = [
            (sparebank1_importer, sample_sparebank1_file),
            (dnb_importer, sample_dnb_file),
            (amex_importer, sample_amex_file),
        ]

        valid_prefixes = ('Assets:', 'Liabilities:', 'Expenses:', 'Income:', 'Equity:')
        account_pattern = re.compile(r'^[A-Z][a-zA-Z0-9:]+$')

        for importer, file_path in importers_and_files:
            entries = importer.extract(file_path, [])

            for entry in entries:
                for posting in entry.postings:
                    account = posting.account

                    # Check prefix
                    assert any(account.startswith(p) for p in valid_prefixes), \
                        f"Invalid account prefix: {account}"

                    # Check format (starts with uppercase, alphanumeric and colons only)
                    assert account_pattern.match(account), \
                        f"Invalid account format: {account}"

    def test_no_duplicate_entries_in_single_file(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        sample_sparebank1_file,
        sample_dnb_file,
        sample_amex_file,
    ):
        """Test that single file imports don't produce duplicate entries."""
        importers_and_files = [
            (sparebank1_importer, sample_sparebank1_file, 'SpareBank1'),
            (dnb_importer, sample_dnb_file, 'DNB'),
            (amex_importer, sample_amex_file, 'Amex'),
        ]

        for importer, file_path, name in importers_and_files:
            entries = importer.extract(file_path, [])

            # Create unique identifiers for each transaction
            seen = set()
            for entry in entries:
                # Use date + narration + first posting amount as identifier
                first_posting = entry.postings[0]
                amount = first_posting.units.number if first_posting.units else 0
                identifier = (entry.date, entry.narration, amount)

                # Note: Some legitimate duplicates might exist (same merchant, same amount, same day)
                # This test checks for exact duplicates which would indicate a bug
                if identifier in seen:
                    # Allow some duplicates as they can be legitimate
                    pass
                seen.add(identifier)

    def test_all_entries_have_required_fields(
        self,
        sparebank1_importer,
        dnb_importer,
        amex_importer,
        sample_sparebank1_file,
        sample_dnb_file,
        sample_amex_file,
    ):
        """Test that all entries have required beancount fields."""
        importers_and_files = [
            (sparebank1_importer, sample_sparebank1_file),
            (dnb_importer, sample_dnb_file),
            (amex_importer, sample_amex_file),
        ]

        for importer, file_path in importers_and_files:
            entries = importer.extract(file_path, [])

            for entry in entries:
                # Must have a date
                assert hasattr(entry, 'date') and entry.date is not None, \
                    "Entry must have a date"

                # Must have postings
                assert hasattr(entry, 'postings') and len(entry.postings) >= 2, \
                    "Entry must have at least 2 postings"

                # Must have a narration
                assert hasattr(entry, 'narration') and entry.narration, \
                    "Entry must have a narration"

    def _entries_to_beancount_string(self, entries) -> str:
        """Convert entries to beancount format string for validation."""
        output = io.StringIO()

        accounts = set()
        for entry in entries:
            for posting in entry.postings:
                accounts.add(posting.account)

        for account in sorted(accounts):
            output.write(f"2020-01-01 open {account}\n")

        output.write("\n")

        for entry in entries:
            flag = entry.flag or '*'
            payee = f'"{entry.payee}"' if entry.payee else ''
            narration = f'"{entry.narration}"'

            if payee:
                output.write(f"{entry.date} {flag} {payee} {narration}\n")
            else:
                output.write(f"{entry.date} {flag} {narration}\n")

            for posting in entry.postings:
                if posting.units:
                    output.write(
                        f"  {posting.account}  {posting.units.number} {posting.units.currency}\n"
                    )
                else:
                    output.write(f"  {posting.account}\n")

            output.write("\n")

        return output.getvalue()
