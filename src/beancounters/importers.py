"""Importer configuration demonstrating all Norwegian bank importers."""

from beangulp import Ingest

# SpareBank 1 importer
from beancount_no_sparebank1 import (
    DepositAccountImporter,
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
                transaction_patterns=[
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
                    match("GET/TELIA") >> "Expenses:Subscriptions:Internet",
                    # Shopping
                    match("POWER") >> "Expenses:Shopping:Electronics",
                    match("XXL") >> "Expenses:Shopping:Sports",
                    # Other
                    match("VINMONOPOLET") >> "Expenses:Alcohol",
                    match("FINN.NO") >> "Expenses:Services",
                    match("HUSLEIE") >> "Expenses:Housing:Rent",
                    match("SAS") >> "Expenses:Travel:Flights",
                    # Income
                    match("SKATTEETATEN") >> "Income:TaxRefund",
                    # Field-based: savings account transfers
                    field(to_account="11112222333") >> "Assets:Bank:SpareBank1:Savings",
                ],
                default_expense_account="Expenses:Uncategorized",
                default_income_account="Income:Other",
            )
        ),
        # DNB Mastercard
        DnbImporter(
            DnbMastercardConfig(
                account_name="Liabilities:CreditCard:DNB",
                currency="NOK",
                transaction_patterns=[
                    # Groceries
                    match("KIWI") >> "Expenses:Groceries",
                    match("MENY") >> "Expenses:Groceries",
                    match("COOP") >> "Expenses:Groceries",
                    match(r"REMA\s*1000").regex >> "Expenses:Groceries",
                    # Subscriptions
                    match("SPOTIFY") >> "Expenses:Subscriptions:Music",
                    match("NETFLIX") >> "Expenses:Subscriptions:Streaming",
                    match("GITHUB") >> "Expenses:Subscriptions:Dev",
                    # Coffee
                    match("STARBUCKS").ignorecase >> "Expenses:Coffee",
                    # Shopping
                    match("POWER") >> "Expenses:Shopping:Electronics",
                    match("XXL") >> "Expenses:Shopping:Sports",
                    # Other
                    match("VINMONOPOLET") >> "Expenses:Alcohol",
                    match("SAS") >> "Expenses:Travel:Flights",
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
                transaction_patterns=[
                    # Groceries
                    match("KIWI") >> "Expenses:Groceries",
                    match("MENY") >> "Expenses:Groceries",
                    match(r"REMA\s*1000").regex >> "Expenses:Groceries",
                    # Subscriptions
                    match("SPOTIFY") >> "Expenses:Subscriptions:Music",
                    match("NETFLIX") >> "Expenses:Subscriptions:Streaming",
                    match("GITHUB") >> "Expenses:Subscriptions:Dev",
                    # Coffee
                    match("STARBUCKS").ignorecase >> "Expenses:Coffee",
                    # Shopping
                    match("ELKJOP") >> "Expenses:Shopping:Electronics",
                    match("H&M") >> "Expenses:Shopping:Clothing",
                    # Other
                    match("VINMONOPOLET") >> "Expenses:Alcohol",
                    match("SAS") >> "Expenses:Travel:Flights",
                ],
                default_account="Expenses:Uncategorized",
            )
        ),
    ]


def main():
    """Entry point for the import-transactions command."""
    ingest = Ingest(get_importers())
    ingest.cli()


if __name__ == "__main__":
    main()
