"""Command-level tests for split adjustment generation."""

import re
from pathlib import Path
from textwrap import dedent

from beancounters.splits import main


def write_ledger(path: Path, text: str) -> Path:
    path.write_text(dedent(text).strip() + "\n", encoding="utf-8")
    return path


def test_generate_splits_outputs_adjustment_for_annotated_expense(
    tmp_path: Path, capsys
):
    config = write_ledger(
        tmp_path / "config.beancount",
        """
        2025-01-01 open Assets:Receivable:Maria NOK
        2025-01-01 custom "split-person" "maria" Assets:Receivable:Maria
        """,
    )
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI" "Groceries"
          split: "maria:50%"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert '2025-02-03 * "Split: Groceries"' in captured.out
    assert re.search(r"Assets:Receivable:Maria\s+60\.00 NOK", captured.out)
    assert re.search(r"Expenses:Groceries\s+-60\.00 NOK", captured.out)
    assert "open Assets:Receivable:Maria" not in captured.out
    assert "balance" not in captured.out
    assert '"KIWI"' not in captured.out


def test_generate_splits_supports_full_expense_share(tmp_path: Path, capsys):
    config = write_ledger(
        tmp_path / "config.beancount",
        """
        2025-01-01 open Assets:Receivable:Maria NOK
        2025-01-01 custom "split-person" "maria" Assets:Receivable:Maria
        """,
    )
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Travel NOK

        2025-02-03 * "Train"
          split: "maria:100%"
          Expenses:Travel  300.00 NOK
          Assets:Bank:Checking  -300.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 0

    captured = capsys.readouterr()
    assert re.search(r"Assets:Receivable:Maria\s+300\.00 NOK", captured.out)
    assert re.search(r"Expenses:Travel\s+-300\.00 NOK", captured.out)


def test_generate_splits_filters_by_year(tmp_path: Path, capsys):
    config = write_ledger(
        tmp_path / "config.beancount",
        """
        2025-01-01 open Assets:Receivable:Maria NOK
        2025-01-01 custom "split-person" "maria" Assets:Receivable:Maria
        """,
    )
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2024-12-31 open Assets:Bank:Checking NOK
        2024-12-31 open Expenses:Groceries NOK

        2024-12-31 * "Old groceries"
          split: "maria:50%"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 0

    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_generate_splits_fails_for_unknown_split_person(tmp_path: Path, capsys):
    config = write_ledger(
        tmp_path / "config.beancount",
        """
        2025-01-01 open Assets:Receivable:Maria NOK
        2025-01-01 custom "split-person" "maria" Assets:Receivable:Maria
        """,
    )
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Groceries"
          split: "olav:50%"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 1

    captured = capsys.readouterr()
    assert "unknown split person 'olav'" in captured.err


def test_generate_splits_requires_open_receivable_account(tmp_path: Path, capsys):
    config = write_ledger(
        tmp_path / "config.beancount",
        """
        2025-01-01 custom "split-person" "maria" Assets:Receivable:Maria
        """,
    )
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Groceries"
          split: "maria:50%"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 1

    captured = capsys.readouterr()
    assert "account Assets:Receivable:Maria must be opened" in captured.err
