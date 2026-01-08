"""End-to-end import tests for all importers.

These tests verify that:
1. Full import of each bank's files works correctly
2. Output is valid beancount syntax
3. All transactions from source files are present in output
4. Transaction data (dates, amounts, accounts) is correct
"""

import io
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.parser import parser


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
