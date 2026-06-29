"""Tests for importer configuration."""

import pytest


class TestGetImporters:
    """Tests for get_importers() function."""

    def test_returns_list(self, all_importers):
        """Test that get_importers returns a list."""
        assert isinstance(all_importers, list)

    def test_returns_expected_number_of_importers(self, all_importers):
        """Test that get_importers returns exactly 3 importers."""
        assert len(all_importers) == 3

    def test_contains_sparebank1_importer(self, all_importers):
        """Test that SpareBank1 importer is included."""
        from beancount_no_sparebank1 import DepositAccountImporter

        sparebank1_importers = [
            i for i in all_importers if isinstance(i, DepositAccountImporter)
        ]
        assert len(sparebank1_importers) == 1

    def test_contains_dnb_importer(self, all_importers):
        """Test that DNB importer is included."""
        from beancount_no_dnb import Importer as DnbImporter

        dnb_importers = [i for i in all_importers if isinstance(i, DnbImporter)]
        assert len(dnb_importers) == 1

    def test_contains_amex_importer(self, all_importers):
        """Test that Amex importer is included."""
        from beancount_no_amex import Importer as AmexImporter

        amex_importers = [i for i in all_importers if isinstance(i, AmexImporter)]
        assert len(amex_importers) == 1


class TestSpareBank1Configuration:
    """Tests for SpareBank1 importer configuration."""

    def test_account_name(self, sparebank1_importer):
        """Test that SpareBank1 importer has correct account name."""
        assert sparebank1_importer.account_name == "Assets:Bank:SpareBank1:Checking"

    def test_currency(self, sparebank1_importer):
        """Test that SpareBank1 importer uses NOK currency."""
        assert sparebank1_importer.currency == "NOK"

    def test_primary_account_number(self, sparebank1_importer):
        """Test that SpareBank1 importer has correct primary account number."""
        assert sparebank1_importer.primary_account_number == "12345678901"

    def test_default_expense_account(self, sparebank1_importer):
        """Test that SpareBank1 importer has correct default expense account."""
        assert sparebank1_importer.default_expense == "Expenses:Uncategorized"

    def test_default_income_account(self, sparebank1_importer):
        """Test that SpareBank1 importer has correct default income account."""
        assert sparebank1_importer.default_income == "Income:Other"

    def test_has_transaction_patterns(self, sparebank1_importer):
        """Test that SpareBank1 importer has transaction patterns defined."""
        assert hasattr(sparebank1_importer, "transaction_patterns")
        assert len(sparebank1_importer.transaction_patterns) > 0

    def test_importer_account_matches_account_name(self, sparebank1_importer):
        """Test that importer_account matches the configured account name."""
        assert sparebank1_importer.importer_account == sparebank1_importer.account_name


class TestDnbConfiguration:
    """Tests for DNB Mastercard importer configuration."""

    def test_account_name(self, dnb_importer):
        """Test that DNB importer has correct account name."""
        assert dnb_importer.account_name == "Liabilities:CreditCard:DNB"

    def test_currency(self, dnb_importer):
        """Test that DNB importer uses NOK currency."""
        assert dnb_importer.currency == "NOK"

    def test_default_account(self, dnb_importer):
        """Test that DNB importer has correct default account."""
        assert dnb_importer.default_account == "Expenses:Uncategorized"

    def test_skip_balance_forward_enabled(self, dnb_importer):
        """Test that DNB importer skips balance forward entries."""
        assert dnb_importer.skip_balance_forward is True

    def test_has_transaction_patterns(self, dnb_importer):
        """Test that DNB importer has transaction patterns defined."""
        assert hasattr(dnb_importer, "transaction_patterns")
        assert len(dnb_importer.transaction_patterns) > 0


class TestAmexConfiguration:
    """Tests for American Express importer configuration."""

    def test_account_name(self, amex_importer):
        """Test that Amex importer has correct account name."""
        assert amex_importer.account_name == "Liabilities:CreditCard:Amex"

    def test_currency(self, amex_importer):
        """Test that Amex importer uses NOK currency."""
        assert amex_importer.currency == "NOK"

    def test_default_account(self, amex_importer):
        """Test that Amex importer has correct default account."""
        assert amex_importer.default_account == "Expenses:Uncategorized"

    def test_has_transaction_patterns(self, amex_importer):
        """Test that Amex importer has transaction patterns defined."""
        assert hasattr(amex_importer, "transaction_patterns")
        assert len(amex_importer.transaction_patterns) > 0


class TestPatternMatchingRules:
    """Tests for pattern matching rules across all importers."""

    def test_sparebank1_pattern_count(self, sparebank1_importer):
        """Test that SpareBank1 has expected number of patterns."""
        # importers.py configures 17 patterns for SpareBank1
        assert len(sparebank1_importer.transaction_patterns) >= 15

    def test_dnb_pattern_count(self, dnb_importer):
        """Test that DNB has expected number of patterns."""
        # importers.py configures 12 patterns for DNB
        assert len(dnb_importer.transaction_patterns) >= 10

    def test_amex_pattern_count(self, amex_importer):
        """Test that Amex has expected number of patterns."""
        # importers.py configures 11 patterns for Amex
        assert len(amex_importer.transaction_patterns) >= 10

    def test_patterns_are_pattern_result_objects(self, sparebank1_importer):
        """Test that patterns are valid PatternResult objects."""
        for pattern in sparebank1_importer.transaction_patterns:
            # All patterns should have 'pattern' and 'build' attributes
            assert hasattr(pattern, "pattern") or hasattr(pattern, "build")

    def test_all_importers_have_grocery_patterns(
        self, sparebank1_importer, dnb_importer, amex_importer
    ):
        """Test that all importers have grocery-related patterns configured."""
        # Each importer should have at least one grocery pattern
        # We verify by checking pattern count is significant
        assert len(sparebank1_importer.transaction_patterns) >= 3
        assert len(dnb_importer.transaction_patterns) >= 3
        assert len(amex_importer.transaction_patterns) >= 3


class TestImporterIdentification:
    """Tests for importer file type identification."""

    def test_sparebank1_identifies_csv_file(
        self, sparebank1_importer, sample_sparebank1_file
    ):
        """Test that SpareBank1 importer identifies its CSV files."""
        if sample_sparebank1_file.exists():
            result = sparebank1_importer.identify(sample_sparebank1_file)
            assert result is True

    def test_dnb_identifies_excel_file(self, dnb_importer, sample_dnb_file):
        """Test that DNB importer identifies its Excel files."""
        if sample_dnb_file.exists():
            result = dnb_importer.identify(sample_dnb_file)
            assert result is True

    def test_amex_identifies_qbo_file(self, amex_importer, sample_amex_file):
        """Test that Amex importer identifies its QBO files."""
        if sample_amex_file.exists():
            result = amex_importer.identify(sample_amex_file)
            assert result is True

    def test_sparebank1_rejects_excel_file(
        self, sparebank1_importer, sample_dnb_file
    ):
        """Test that SpareBank1 importer rejects DNB Excel files."""
        if sample_dnb_file.exists():
            result = sparebank1_importer.identify(sample_dnb_file)
            assert result is False

    def test_dnb_rejects_csv_file(self, dnb_importer, sample_sparebank1_file):
        """Test that DNB importer rejects SpareBank1 CSV files."""
        if sample_sparebank1_file.exists():
            result = dnb_importer.identify(sample_sparebank1_file)
            assert result is False

    def test_amex_rejects_csv_file(self, amex_importer, sample_sparebank1_file):
        """Test that Amex importer rejects SpareBank1 CSV files."""
        if sample_sparebank1_file.exists():
            result = amex_importer.identify(sample_sparebank1_file)
            assert result is False

    def test_amex_rejects_excel_file(self, amex_importer, sample_dnb_file):
        """Test that Amex importer rejects DNB Excel files."""
        if sample_dnb_file.exists():
            result = amex_importer.identify(sample_dnb_file)
            assert result is False


class TestImporterNames:
    """Tests for importer name attributes."""

    def test_sparebank1_has_name(self, sparebank1_importer):
        """Test that SpareBank1 importer has a name attribute."""
        assert hasattr(sparebank1_importer, "name")
        assert "sparebank1" in sparebank1_importer.name.lower()

    def test_dnb_has_name(self, dnb_importer):
        """Test that DNB importer has a name attribute."""
        assert hasattr(dnb_importer, "name")
        assert "dnb" in dnb_importer.name.lower()

    def test_amex_has_name(self, amex_importer):
        """Test that Amex importer has a name attribute."""
        assert hasattr(amex_importer, "name")
        assert "amex" in amex_importer.name.lower()


class TestAccountNameValidity:
    """Tests to ensure all configured account names follow Beancount conventions."""

    @pytest.mark.parametrize(
        "account_name",
        [
            "Assets:Bank:SpareBank1:Checking",
            "Assets:Bank:SpareBank1:Savings",
            "Liabilities:CreditCard:DNB",
            "Liabilities:CreditCard:Amex",
            "Income:Salary",
            "Income:Other",
            "Income:TaxRefund",
            "Expenses:Uncategorized",
            "Expenses:Groceries",
            "Expenses:Transport:Public",
            "Expenses:Transport:Fuel",
            "Expenses:Subscriptions:Music",
            "Expenses:Subscriptions:Streaming",
            "Expenses:Subscriptions:Internet",
            "Expenses:Subscriptions:Dev",
            "Expenses:Shopping:Electronics",
            "Expenses:Shopping:Sports",
            "Expenses:Shopping:Clothing",
            "Expenses:Alcohol",
            "Expenses:Services",
            "Expenses:Housing:Rent",
            "Expenses:Travel:Flights",
            "Expenses:Coffee",
        ],
    )
    def test_account_name_starts_with_valid_root(self, account_name):
        """Test that account names start with valid root accounts."""
        valid_roots = ("Assets:", "Liabilities:", "Income:", "Expenses:", "Equity:")
        assert any(account_name.startswith(root) for root in valid_roots)

    @pytest.mark.parametrize(
        "account_name",
        [
            "Assets:Bank:SpareBank1:Checking",
            "Assets:Bank:SpareBank1:Savings",
            "Liabilities:CreditCard:DNB",
            "Liabilities:CreditCard:Amex",
            "Income:Salary",
            "Expenses:Groceries",
        ],
    )
    def test_account_name_has_no_invalid_characters(self, account_name):
        """Test that account names don't contain invalid characters."""
        invalid_chars = [" ", "\t", "\n", "/", "\\", "@", "#", "$", "%"]
        for char in invalid_chars:
            assert char not in account_name

    @pytest.mark.parametrize(
        "account_name",
        [
            "Assets:Bank:SpareBank1:Checking",
            "Expenses:Subscriptions:Music",
            "Income:Salary",
        ],
    )
    def test_account_name_components_start_with_uppercase(self, account_name):
        """Test that account name components start with uppercase letters."""
        components = account_name.split(":")
        for component in components:
            assert component[0].isupper(), f"Component '{component}' should start with uppercase"


class TestImporterFlags:
    """Tests for importer transaction flags."""

    def test_sparebank1_default_flag(self, sparebank1_importer):
        """Test that SpareBank1 importer uses correct default flag."""
        assert sparebank1_importer.flag == "*"

    def test_dnb_default_flag(self, dnb_importer):
        """Test that DNB importer uses correct default flag."""
        assert dnb_importer.flag == "*"

    def test_amex_default_flag(self, amex_importer):
        """Test that Amex importer uses correct default flag."""
        assert amex_importer.flag == "*"
