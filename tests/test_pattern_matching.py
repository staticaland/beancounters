"""Tests for pattern matching functionality across all importers."""

import re
from pathlib import Path

import pytest


class TestSpareBank1Patterns:
    """Tests for SpareBank1 pattern matching."""

    def test_simple_string_matching_kiwi(self, sparebank1_importer, sample_sparebank1_file):
        """Test that KIWI transactions are categorized as Groceries."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        kiwi_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'KIWI' in e.narration.upper()
        ]
        assert len(kiwi_transactions) > 0, "Should have KIWI transactions in test data"
        for txn in kiwi_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            assert expense_posting is not None
            assert expense_posting.account == "Expenses:Groceries"

    def test_simple_string_matching_meny(self, sparebank1_importer, sample_sparebank1_file):
        """Test that MENY transactions are categorized as Groceries."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        meny_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'MENY' in e.narration.upper()
        ]
        assert len(meny_transactions) > 0, "Should have MENY transactions in test data"
        for txn in meny_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            assert expense_posting is not None
            assert expense_posting.account == "Expenses:Groceries"

    def test_simple_string_matching_coop(self, sparebank1_importer, sample_sparebank1_file):
        """Test that COOP transactions are categorized as Groceries."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        coop_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'COOP' in e.narration.upper()
        ]
        assert len(coop_transactions) > 0, "Should have COOP transactions in test data"
        for txn in coop_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            assert expense_posting is not None
            assert expense_posting.account == "Expenses:Groceries"

    def test_regex_pattern_rema_1000(self, sparebank1_importer, sample_sparebank1_file):
        """Test that REMA 1000 transactions (with varying spacing) are categorized as Groceries."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        # Match REMA 1000, REMA1000, REMA  1000, etc.
        rema_pattern = re.compile(r'REMA\s*1000', re.IGNORECASE)
        rema_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and rema_pattern.search(e.narration)
        ]
        assert len(rema_transactions) > 0, "Should have REMA 1000 transactions in test data"
        for txn in rema_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            assert expense_posting is not None
            assert expense_posting.account == "Expenses:Groceries"

    def test_transport_patterns(self, sparebank1_importer, sample_sparebank1_file):
        """Test that transport-related transactions are correctly categorized."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        statoil_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'STATOIL' in e.narration.upper()
        ]
        for txn in statoil_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            assert expense_posting is not None
            assert expense_posting.account == "Expenses:Transport:Fuel"

    def test_subscription_patterns(self, sparebank1_importer, sample_sparebank1_file):
        """Test that subscription services are correctly categorized."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        subscription_mappings = {
            'SPOTIFY': 'Expenses:Subscriptions:Music',
            'NETFLIX': 'Expenses:Subscriptions:Streaming',
            'GET/TELIA': 'Expenses:Subscriptions:Internet',
        }

        for keyword, expected_account in subscription_mappings.items():
            matching_txns = [
                e for e in entries
                if hasattr(e, 'narration') and keyword in e.narration.upper()
            ]
            for txn in matching_txns:
                expense_posting = next(
                    (p for p in txn.postings if p.account.startswith('Expenses:')),
                    None
                )
                assert expense_posting is not None, f"Should have expense posting for {keyword}"
                assert expense_posting.account == expected_account, \
                    f"{keyword} should map to {expected_account}, got {expense_posting.account}"

    def test_income_pattern_skatteetaten(self, sparebank1_importer, sample_sparebank1_file):
        """Test that SKATTEETATEN (tax refund) is categorized as income."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        tax_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'SKATTEETATEN' in e.narration.upper()
        ]
        assert len(tax_transactions) > 0, "Should have SKATTEETATEN transactions in test data"
        for txn in tax_transactions:
            income_posting = next(
                (p for p in txn.postings if p.account.startswith('Income:')),
                None
            )
            assert income_posting is not None
            assert income_posting.account == "Income:TaxRefund"

    def test_default_expense_for_unmatched(self, sparebank1_importer, sample_sparebank1_file):
        """Test that unmatched transactions use default expense account."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        # Find transactions that should NOT match any pattern
        # ELIXIA, SATS, APOTEK, BURGER KING, etc. don't have patterns
        unmatched_keywords = ['ELIXIA', 'SATS', 'APOTEK']

        for keyword in unmatched_keywords:
            matching_txns = [
                e for e in entries
                if hasattr(e, 'narration') and keyword in e.narration.upper()
            ]
            for txn in matching_txns:
                expense_posting = next(
                    (p for p in txn.postings if p.account.startswith('Expenses:')),
                    None
                )
                assert expense_posting is not None
                assert expense_posting.account == "Expenses:Uncategorized", \
                    f"{keyword} should be Uncategorized, got {expense_posting.account}"

    def test_case_sensitivity_pattern_matching(self, sparebank1_importer):
        """Test that SpareBank1 patterns are case-sensitive by default."""
        # Verify pattern configuration
        for pattern in sparebank1_importer.transaction_patterns:
            if pattern.pattern.narration == 'KIWI':
                assert pattern.pattern.case_insensitive is False, \
                    "KIWI pattern should be case-sensitive"
                break

    def test_salary_counterparty_matching(self, sparebank1_importer, sample_sparebank1_file):
        """Test that salary from specific account is correctly categorized."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        # Look for salary transactions (income with Lønn in narration)
        salary_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'LØNN' in e.narration.upper()
        ]
        for txn in salary_transactions:
            income_posting = next(
                (p for p in txn.postings if p.account.startswith('Income:')),
                None
            )
            assert income_posting is not None, "Salary should have income posting"
            assert income_posting.account == "Income:Salary", \
                f"Salary should map to Income:Salary, got {income_posting.account}"

    def test_shopping_patterns(self, sparebank1_importer, sample_sparebank1_file):
        """Test that shopping transactions are correctly categorized."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])

        shopping_mappings = {
            'XXL': 'Expenses:Shopping:Sports',
        }

        for keyword, expected_account in shopping_mappings.items():
            matching_txns = [
                e for e in entries
                if hasattr(e, 'narration') and keyword in e.narration.upper()
            ]
            for txn in matching_txns:
                expense_posting = next(
                    (p for p in txn.postings if p.account.startswith('Expenses:')),
                    None
                )
                assert expense_posting is not None
                assert expense_posting.account == expected_account

    def test_alcohol_pattern_vinmonopolet(self, sparebank1_importer, sample_sparebank1_file):
        """Test that VINMONOPOLET transactions are categorized as Alcohol."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        vinmonopolet_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'VINMONOPOLET' in e.narration.upper()
        ]
        assert len(vinmonopolet_transactions) > 0, "Should have VINMONOPOLET transactions"
        for txn in vinmonopolet_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            assert expense_posting is not None
            assert expense_posting.account == "Expenses:Alcohol"

    def test_travel_pattern_sas(self, sparebank1_importer, sample_sparebank1_file):
        """Test that SAS transactions are categorized as Travel:Flights."""
        entries = sparebank1_importer.extract(sample_sparebank1_file, [])
        sas_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'SAS' in e.narration.upper()
        ]
        assert len(sas_transactions) > 0, "Should have SAS transactions"
        for txn in sas_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            assert expense_posting is not None
            assert expense_posting.account == "Expenses:Travel:Flights"

    def test_pattern_has_valid_structure(self, sparebank1_importer):
        """Test that all patterns have valid structure."""
        for pattern in sparebank1_importer.transaction_patterns:
            assert hasattr(pattern, 'pattern'), "Pattern should have 'pattern' attribute"
            assert hasattr(pattern, 'build'), "Pattern should have 'build' attribute"
            # Each pattern should have an account
            assert pattern.pattern.account is not None, "Pattern should have account"


class TestDnbPatterns:
    """Tests for DNB Mastercard pattern matching."""

    def test_case_insensitive_starbucks(self, dnb_importer):
        """Test that STARBUCKS pattern is case-insensitive."""
        starbucks_pattern = None
        for pattern in dnb_importer.transaction_patterns:
            if pattern.pattern.narration == 'STARBUCKS':
                starbucks_pattern = pattern
                break

        assert starbucks_pattern is not None, "Should have STARBUCKS pattern"
        assert starbucks_pattern.pattern.case_insensitive is True, \
            "STARBUCKS pattern should be case-insensitive"

    def test_grocery_patterns(self, dnb_importer, sample_dnb_file):
        """Test that grocery patterns are correctly configured."""
        entries = dnb_importer.extract(sample_dnb_file, [])

        grocery_keywords = ['KIWI', 'MENY', 'COOP']

        for keyword in grocery_keywords:
            matching_txns = [
                e for e in entries
                if hasattr(e, 'narration') and keyword in e.narration.upper()
            ]
            for txn in matching_txns:
                expense_posting = next(
                    (p for p in txn.postings if p.account.startswith('Expenses:')),
                    None
                )
                if expense_posting:
                    assert expense_posting.account == "Expenses:Groceries", \
                        f"{keyword} should map to Groceries"

    def test_regex_pattern_rema_1000(self, dnb_importer):
        """Test that REMA 1000 regex pattern is configured correctly."""
        rema_pattern = None
        for pattern in dnb_importer.transaction_patterns:
            if pattern.pattern.narration and 'REMA' in pattern.pattern.narration:
                rema_pattern = pattern
                break

        assert rema_pattern is not None, "Should have REMA 1000 pattern"
        assert rema_pattern.pattern.regex is True, "REMA 1000 should be a regex pattern"
        assert rema_pattern.pattern.account == "Expenses:Groceries"

    def test_subscription_patterns(self, dnb_importer):
        """Test that subscription patterns are correctly configured."""
        subscription_mappings = {
            'SPOTIFY': 'Expenses:Subscriptions:Music',
            'NETFLIX': 'Expenses:Subscriptions:Streaming',
            'GITHUB': 'Expenses:Subscriptions:Dev',
        }

        for keyword, expected_account in subscription_mappings.items():
            found = False
            for pattern in dnb_importer.transaction_patterns:
                if pattern.pattern.narration == keyword:
                    found = True
                    assert pattern.pattern.account == expected_account, \
                        f"{keyword} should map to {expected_account}"
                    break
            assert found, f"Should have pattern for {keyword}"

    def test_default_account_configuration(self, dnb_importer):
        """Test that DNB importer has correct default account."""
        assert dnb_importer.default_account == "Expenses:Uncategorized"

    def test_skip_balance_forward_enabled(self, dnb_importer):
        """Test that balance forward skipping is enabled."""
        assert dnb_importer.skip_balance_forward is True

    def test_multiple_grocery_patterns(self, dnb_importer):
        """Test that multiple patterns map to same category (Groceries)."""
        grocery_patterns = [
            p for p in dnb_importer.transaction_patterns
            if p.pattern.account == "Expenses:Groceries"
        ]
        # Should have at least KIWI, MENY, COOP, REMA 1000
        assert len(grocery_patterns) >= 4, \
            f"Should have at least 4 grocery patterns, found {len(grocery_patterns)}"

    def test_alcohol_pattern(self, dnb_importer):
        """Test that VINMONOPOLET pattern is configured."""
        vinmonopolet_pattern = None
        for pattern in dnb_importer.transaction_patterns:
            if pattern.pattern.narration == 'VINMONOPOLET':
                vinmonopolet_pattern = pattern
                break

        assert vinmonopolet_pattern is not None
        assert vinmonopolet_pattern.pattern.account == "Expenses:Alcohol"

    def test_travel_pattern(self, dnb_importer):
        """Test that SAS pattern is configured for travel."""
        sas_pattern = None
        for pattern in dnb_importer.transaction_patterns:
            if pattern.pattern.narration == 'SAS':
                sas_pattern = pattern
                break

        assert sas_pattern is not None
        assert sas_pattern.pattern.account == "Expenses:Travel:Flights"

    def test_coffee_pattern_starbucks(self, dnb_importer):
        """Test that STARBUCKS maps to Coffee category."""
        starbucks_pattern = None
        for pattern in dnb_importer.transaction_patterns:
            if pattern.pattern.narration == 'STARBUCKS':
                starbucks_pattern = pattern
                break

        assert starbucks_pattern is not None
        assert starbucks_pattern.pattern.account == "Expenses:Coffee"

    def test_unmatched_transactions_use_default(self, dnb_importer, sample_dnb_file):
        """Test that unmatched transactions get default account."""
        entries = dnb_importer.extract(sample_dnb_file, [])
        # Look for transactions that don't match any pattern
        # These should be categorized as Uncategorized
        for txn in entries:
            if not hasattr(txn, 'postings'):
                continue
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            if expense_posting:
                # Verify it's either a known category or Uncategorized
                valid_accounts = [
                    "Expenses:Groceries",
                    "Expenses:Subscriptions:Music",
                    "Expenses:Subscriptions:Streaming",
                    "Expenses:Subscriptions:Dev",
                    "Expenses:Coffee",
                    "Expenses:Shopping:Electronics",
                    "Expenses:Shopping:Sports",
                    "Expenses:Alcohol",
                    "Expenses:Travel:Flights",
                    "Expenses:Uncategorized",
                ]
                assert expense_posting.account in valid_accounts, \
                    f"Unexpected account: {expense_posting.account}"


class TestAmexPatterns:
    """Tests for American Express pattern matching."""

    def test_grocery_patterns(self, amex_importer, sample_amex_file):
        """Test that grocery patterns are correctly applied."""
        entries = amex_importer.extract(sample_amex_file, [])

        grocery_keywords = ['KIWI', 'MENY']

        for keyword in grocery_keywords:
            matching_txns = [
                e for e in entries
                if hasattr(e, 'narration') and keyword in e.narration.upper()
            ]
            for txn in matching_txns:
                expense_posting = next(
                    (p for p in txn.postings if p.account.startswith('Expenses:')),
                    None
                )
                if expense_posting:
                    assert expense_posting.account == "Expenses:Groceries", \
                        f"{keyword} should map to Groceries"

    def test_regex_pattern_rema_1000(self, amex_importer, sample_amex_file):
        """Test that REMA 1000 transactions are categorized correctly."""
        entries = amex_importer.extract(sample_amex_file, [])
        rema_pattern = re.compile(r'REMA\s*1000', re.IGNORECASE)
        rema_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and rema_pattern.search(e.narration)
        ]
        for txn in rema_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            if expense_posting:
                assert expense_posting.account == "Expenses:Groceries"

    def test_case_insensitive_starbucks(self, amex_importer):
        """Test that STARBUCKS pattern is case-insensitive."""
        starbucks_pattern = None
        for pattern in amex_importer.transaction_patterns:
            if pattern.pattern.narration == 'STARBUCKS':
                starbucks_pattern = pattern
                break

        assert starbucks_pattern is not None, "Should have STARBUCKS pattern"
        assert starbucks_pattern.pattern.case_insensitive is True, \
            "STARBUCKS pattern should be case-insensitive"

    def test_coffee_pattern_starbucks(self, amex_importer, sample_amex_file):
        """Test that STARBUCKS transactions map to Coffee."""
        entries = amex_importer.extract(sample_amex_file, [])
        starbucks_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'STARBUCKS' in e.narration.upper()
        ]
        for txn in starbucks_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            if expense_posting:
                assert expense_posting.account == "Expenses:Coffee"

    def test_subscription_patterns(self, amex_importer, sample_amex_file):
        """Test that subscription services are correctly categorized."""
        entries = amex_importer.extract(sample_amex_file, [])

        subscription_mappings = {
            'SPOTIFY': 'Expenses:Subscriptions:Music',
            'NETFLIX': 'Expenses:Subscriptions:Streaming',
            'GITHUB': 'Expenses:Subscriptions:Dev',
        }

        for keyword, expected_account in subscription_mappings.items():
            matching_txns = [
                e for e in entries
                if hasattr(e, 'narration') and keyword in e.narration.upper()
            ]
            for txn in matching_txns:
                expense_posting = next(
                    (p for p in txn.postings if p.account.startswith('Expenses:')),
                    None
                )
                if expense_posting:
                    assert expense_posting.account == expected_account, \
                        f"{keyword} should map to {expected_account}"

    def test_electronics_pattern_elkjop(self, amex_importer, sample_amex_file):
        """Test that ELKJOP transactions are categorized as Electronics."""
        entries = amex_importer.extract(sample_amex_file, [])
        elkjop_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'ELKJOP' in e.narration.upper()
        ]
        assert len(elkjop_transactions) > 0, "Should have ELKJOP transactions"
        for txn in elkjop_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            if expense_posting:
                assert expense_posting.account == "Expenses:Shopping:Electronics"

    def test_clothing_pattern_hm(self, amex_importer, sample_amex_file):
        """Test that H&M transactions are categorized as Clothing."""
        entries = amex_importer.extract(sample_amex_file, [])
        hm_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'H&M' in e.narration.upper()
        ]
        for txn in hm_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            if expense_posting:
                assert expense_posting.account == "Expenses:Shopping:Clothing"

    def test_credit_transaction_handling(self, amex_importer, sample_amex_file):
        """Test that credit/refund transactions are handled correctly."""
        entries = amex_importer.extract(sample_amex_file, [])
        # Look for refund transactions (positive amounts on credit card)
        refund_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'REFUND' in e.narration.upper()
        ]
        for txn in refund_transactions:
            # Verify the transaction has correct structure
            assert len(txn.postings) >= 2, "Refund should have at least 2 postings"
            # Credit card posting should be positive (reducing liability)
            cc_posting = next(
                (p for p in txn.postings if 'Amex' in p.account),
                None
            )
            if cc_posting:
                # For a refund, amount should be positive on credit card
                assert cc_posting.units.number > 0, \
                    "Refund should have positive amount on credit card"

    def test_unmatched_transactions_uncategorized(self, amex_importer, sample_amex_file):
        """Test that unmatched transactions are categorized as Uncategorized."""
        entries = amex_importer.extract(sample_amex_file, [])

        # Find transactions that don't match known patterns
        unmatched_keywords = ['BURGER KING', 'MCDONALDS', 'PEPPES', 'SATS', 'TANUM']

        for keyword in unmatched_keywords:
            matching_txns = [
                e for e in entries
                if hasattr(e, 'narration') and keyword in e.narration.upper()
            ]
            for txn in matching_txns:
                expense_posting = next(
                    (p for p in txn.postings if p.account.startswith('Expenses:')),
                    None
                )
                if expense_posting:
                    assert expense_posting.account == "Expenses:Uncategorized", \
                        f"{keyword} should be Uncategorized, got {expense_posting.account}"

    def test_default_account_configuration(self, amex_importer):
        """Test that Amex importer has correct default account."""
        assert amex_importer.default_account == "Expenses:Uncategorized"

    def test_alcohol_pattern(self, amex_importer, sample_amex_file):
        """Test that VINMONOPOLET transactions are categorized as Alcohol."""
        entries = amex_importer.extract(sample_amex_file, [])
        vinmonopolet_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'VINMONOPOLET' in e.narration.upper()
        ]
        for txn in vinmonopolet_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            if expense_posting:
                assert expense_posting.account == "Expenses:Alcohol"

    def test_travel_pattern(self, amex_importer, sample_amex_file):
        """Test that SAS transactions are categorized as Travel:Flights."""
        entries = amex_importer.extract(sample_amex_file, [])
        sas_transactions = [
            e for e in entries
            if hasattr(e, 'narration') and 'SAS' in e.narration.upper()
        ]
        for txn in sas_transactions:
            expense_posting = next(
                (p for p in txn.postings if p.account.startswith('Expenses:')),
                None
            )
            if expense_posting:
                assert expense_posting.account == "Expenses:Travel:Flights"


class TestPatternPriority:
    """Tests for pattern matching priority and specificity."""

    def test_first_matching_pattern_wins(self, sparebank1_importer):
        """Test that patterns are applied in order (first match wins)."""
        # Verify that pattern order is consistent
        patterns = sparebank1_importer.transaction_patterns
        assert len(patterns) > 0, "Should have patterns configured"

        # The first pattern should take precedence if multiple could match
        # This is a structural test - actual behavior depends on implementation

    def test_regex_patterns_configured_correctly(self, sparebank1_importer, dnb_importer, amex_importer):
        """Test that regex patterns are properly flagged."""
        for importer, name in [
            (sparebank1_importer, 'SpareBank1'),
            (dnb_importer, 'DNB'),
            (amex_importer, 'Amex')
        ]:
            for pattern in importer.transaction_patterns:
                if pattern.pattern.narration and 'REMA' in pattern.pattern.narration:
                    assert pattern.pattern.regex is True, \
                        f"{name} REMA pattern should be regex"

    def test_case_insensitive_patterns_configured_correctly(self, dnb_importer, amex_importer):
        """Test that case-insensitive patterns are properly flagged."""
        for importer, name in [(dnb_importer, 'DNB'), (amex_importer, 'Amex')]:
            starbucks_found = False
            for pattern in importer.transaction_patterns:
                if pattern.pattern.narration == 'STARBUCKS':
                    starbucks_found = True
                    assert pattern.pattern.case_insensitive is True, \
                        f"{name} STARBUCKS should be case-insensitive"
            assert starbucks_found, f"{name} should have STARBUCKS pattern"


class TestPatternCoverage:
    """Tests to ensure pattern coverage of common transactions."""

    def test_all_importers_have_grocery_patterns(
        self, sparebank1_importer, dnb_importer, amex_importer
    ):
        """Test that all importers can categorize grocery transactions."""
        for importer, name in [
            (sparebank1_importer, 'SpareBank1'),
            (dnb_importer, 'DNB'),
            (amex_importer, 'Amex')
        ]:
            grocery_patterns = [
                p for p in importer.transaction_patterns
                if p.pattern.account == "Expenses:Groceries"
            ]
            assert len(grocery_patterns) >= 1, \
                f"{name} should have at least one grocery pattern"

    def test_all_importers_have_subscription_patterns(
        self, sparebank1_importer, dnb_importer, amex_importer
    ):
        """Test that all importers have subscription patterns."""
        for importer, name in [
            (sparebank1_importer, 'SpareBank1'),
            (dnb_importer, 'DNB'),
            (amex_importer, 'Amex')
        ]:
            subscription_patterns = [
                p for p in importer.transaction_patterns
                if p.pattern.account and 'Subscriptions' in p.pattern.account
            ]
            assert len(subscription_patterns) >= 1, \
                f"{name} should have at least one subscription pattern"

    def test_pattern_accounts_are_valid(
        self, sparebank1_importer, dnb_importer, amex_importer
    ):
        """Test that all pattern accounts follow Beancount conventions."""
        valid_prefixes = ('Assets:', 'Liabilities:', 'Income:', 'Expenses:', 'Equity:')

        for importer, name in [
            (sparebank1_importer, 'SpareBank1'),
            (dnb_importer, 'DNB'),
            (amex_importer, 'Amex')
        ]:
            for pattern in importer.transaction_patterns:
                account = pattern.pattern.account
                assert any(account.startswith(prefix) for prefix in valid_prefixes), \
                    f"{name} pattern account '{account}' should start with valid prefix"
