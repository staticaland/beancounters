"""Importer configuration demonstrating all Norwegian bank importers."""

from beangulp import Ingest

# SpareBank 1 importer
from beancount_no_sparebank1 import (
    DepositAccountImporter,
    PDFStatementConfig,
    PDFStatementImporter,
    Sparebank1AccountConfig,
    match,
    when,
    field,
    counterparty,
    amount,
)

# DNB Mastercard importer
from beancount_no_dnb import (
    DnbMastercardConfig,
    Importer as DnbImporter,
)

# American Express importer
from beancount_no_amex import (
    AmexAccountConfig,
    Importer as AmexImporter,
)

COMMON_PATTERNS = [
    # Groceries
    match("KIWI") >> "Expenses:Groceries",
    match("MENY") >> "Expenses:Groceries",
    match("COOP") >> "Expenses:Groceries",
    match(r"REMA\s*1000").regex >> "Expenses:Groceries",
    # Transport
    match("RUTER") >> "Expenses:Transport:Public",
    match("STATOIL") >> "Expenses:Transport:Fuel",
    # Subscriptions
    match("SPOTIFY") >> "Expenses:Subscriptions:Music",
    match("NETFLIX") >> "Expenses:Subscriptions:Streaming",
    match("GITHUB") >> "Expenses:Subscriptions:Dev",
    match("GET/TELIA") >> "Expenses:Subscriptions:Internet",
    # Coffee
    match("STARBUCKS").ignorecase >> "Expenses:Coffee",
    # Shopping
    match("POWER") >> "Expenses:Shopping:Electronics",
    match("ELKJOP") >> "Expenses:Shopping:Electronics",
    match("XXL") >> "Expenses:Shopping:Sports",
    match("H&M") >> "Expenses:Shopping:Clothing",
    # Other common merchants
    match("VINMONOPOLET") >> "Expenses:Alcohol",
    match("FINN.NO") >> "Expenses:Services",
    match("HUSLEIE") >> "Expenses:Housing:Rent",
    match("SAS") >> "Expenses:Travel:Flights",
]


def get_importers():
    """Configure all importers for demo data."""
    return [
        # SpareBank 1 checking account
        DepositAccountImporter(
            Sparebank1AccountConfig(
                primary_account_number="12345678901",
                account_name="Assets:Bank:SpareBank1:Checking",
                currency="NOK",
                # Map bank account numbers to Beancount accounts
                other_account_mappings=[
                    ("11112222333", "Assets:Bank:SpareBank1:Savings"),
                    ("56712345678", "Income:Salary"),
                ],
                transaction_patterns=COMMON_PATTERNS + [
                    # Credit-card settlements
                    match("DNB MASTERCARD") >> "Liabilities:CreditCard:DNB",
                    match("AMEX AUTOGIRO") >> "Liabilities:CreditCard:Amex",
                    # Income
                    match("SKATTEETATEN") >> "Income:TaxRefund",
                    # Field-based: savings account transfers
                    field(to_account="11112222333") >> "Assets:Bank:SpareBank1:Savings",
                ],
                default_expense_account="Expenses:Uncategorized",
                default_income_account="Income:Other",
            )
        ),
        # SpareBank 1 balance statements
        PDFStatementImporter(
            PDFStatementConfig(
                account_name="Assets:Bank:SpareBank1:Checking",
                currency="NOK",
                prefix="sparebank1_statement",
                generate_balance_assertions=True,
            )
        ),
        # DNB Mastercard
        DnbImporter(
            DnbMastercardConfig(
                account_name="Liabilities:CreditCard:DNB",
                currency="NOK",
                transaction_patterns=COMMON_PATTERNS + [
                    # Payments from SpareBank 1 checking
                    match("Innbetaling") >> "Assets:Bank:SpareBank1:Checking",
                ],
                default_account="Expenses:Uncategorized",
                skip_balance_forward=True,
            )
        ),
        # American Express
        AmexImporter(
            AmexAccountConfig(
                account_name="Liabilities:CreditCard:Amex",
                currency="NOK",
                generate_balance_assertions=True,
                transaction_patterns=COMMON_PATTERNS + [
                    # Payments from SpareBank 1 checking
                    match("AUTOGIROBETALING") >> "Assets:Bank:SpareBank1:Checking",
                ],
                default_account="Expenses:Uncategorized",
            ),
            debug=False,
        ),
    ]


def main():
    """Entry point for the import-transactions command."""
    ingest = Ingest(get_importers())
    ingest.cli()


if __name__ == "__main__":
    main()
