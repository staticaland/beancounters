"""Command-level tests for split adjustment generation."""

import re
from pathlib import Path
from textwrap import dedent

import pytest

from beancounters.splits import main, preserve_main


def write_ledger(path: Path, text: str) -> Path:
    path.write_text(dedent(text).strip() + "\n", encoding="utf-8")
    return path


def write_split_config(tmp_path: Path) -> Path:
    return write_ledger(
        tmp_path / "config.beancount",
        """
        2025-01-01 open Assets:Receivable:Maria NOK
        2025-01-01 open Assets:Receivable:Olav NOK
        2025-01-01 custom "split-person" "Maria" Assets:Receivable:Maria
        2025-01-01 custom "split-person" "olav" Assets:Receivable:Olav
        """,
    )


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
    assert re.search(r"generated_by:\s+\"beancounters.generate-splits\"", captured.out)
    assert "open Assets:Receivable:Maria" not in captured.out
    assert "balance" not in captured.out
    assert '"KIWI"' not in captured.out


def test_generate_splits_uses_provider_id_for_link_and_source_metadata(
    tmp_path: Path, capsys
):
    config = write_split_config(tmp_path)
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI" "Groceries"
          provider_transaction_id: "txn/2025/02/03/kiwi"
          import_fingerprint: "fallback-fingerprint"
          split: "maria:50%"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert re.search(
        r'2025-02-03 \* "Split: Groceries" \^split-provider-[a-f0-9]{24}',
        captured.out,
    )
    assert re.search(r"generated_by:\s+\"beancounters.generate-splits\"", captured.out)
    assert re.search(
        r"source_provider_id:\s+\"txn/2025/02/03/kiwi\"",
        captured.out,
    )
    assert "source_import_fingerprint" not in captured.out
    assert "fallback-fingerprint" not in captured.out
    assert "source_narration" not in captured.out
    assert "source_date" not in captured.out
    assert "source_amount" not in captured.out


def test_generate_splits_uses_import_fingerprint_when_provider_id_is_absent(
    tmp_path: Path, capsys
):
    config = write_split_config(tmp_path)
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Dining NOK

        2025-02-03 * "Restaurant"
          import_fingerprint: "restaurant-2025-02-03-100"
          split: "maria:25%"
          Expenses:Dining  100.00 NOK
          Assets:Bank:Checking  -100.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert re.search(
        r'2025-02-03 \* "Split: Restaurant" \^split-fingerprint-[a-f0-9]{24}',
        captured.out,
    )
    assert re.search(
        r"source_import_fingerprint:\s+\"restaurant-2025-02-03-100\"",
        captured.out,
    )
    assert "source_provider_id" not in captured.out


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


def test_generate_splits_combines_multiple_annotations_with_note_and_rounding(
    tmp_path: Path, capsys
):
    config = write_split_config(tmp_path)
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Dining NOK

        2025-02-03 * "Restaurant"
          split: " MARIA : 33.333 , olav:33.333% "
          split_note: "Dinner before movie"
          Expenses:Dining  100.00 NOK
          Assets:Bank:Checking  -100.00 NOK
        """,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.count('2025-02-03 * "Split: Restaurant"') == 1
    assert len(re.findall(r"\^split-fingerprint-[a-f0-9]{24}", captured.out)) == 1
    assert re.search(r"split_note:\s+\"Dinner before movie\"", captured.out)
    assert re.search(r"Assets:Receivable:Maria\s+33\.33 NOK", captured.out)
    assert re.search(r"Assets:Receivable:Olav\s+33\.33 NOK", captured.out)
    assert re.search(r"Expenses:Dining\s+-66\.66 NOK", captured.out)


def test_generate_splits_check_mode_validates_without_output(tmp_path: Path, capsys):
    config = write_split_config(tmp_path)
    imported = write_ledger(
        tmp_path / "imports.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Groceries"
          split: "maria:50"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert (
        main(["--config", str(config), "--year", "2025", "--check", str(imported)])
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    ("transaction", "expected_error"),
    [
        (
            """
            2025-02-03 * "Too much"
              split: "maria:75, olav:30"
              Expenses:Groceries  120.00 NOK
              Assets:Bank:Checking  -120.00 NOK
            """,
            "exceeds 100%",
        ),
        (
            """
            2025-02-03 * "Note without split"
              split_note: "Shared later"
              Expenses:Groceries  120.00 NOK
              Assets:Bank:Checking  -120.00 NOK
            """,
            "split_note requires at least one split annotation",
        ),
        (
            """
            2025-02-03 * "Exact amount"
              split: "maria:60.00 NOK"
              Expenses:Groceries  120.00 NOK
              Assets:Bank:Checking  -120.00 NOK
            """,
            "exact amount split annotation",
        ),
        (
            """
            2025-02-03 * "Transfer"
              split: "maria:50"
              Assets:Savings  120.00 NOK
              Assets:Bank:Checking  -120.00 NOK
            """,
            "exactly one Expenses:* posting",
        ),
        (
            """
            2025-02-03 * "Two categories"
              split: "maria:50"
              Expenses:Groceries  80.00 NOK
              Expenses:Dining  40.00 NOK
              Assets:Bank:Checking  -120.00 NOK
            """,
            "exactly one Expenses:* posting",
        ),
        (
            """
            2025-02-03 * "Refund"
              split: "maria:50"
              Expenses:Groceries  -120.00 NOK
              Assets:Bank:Checking  120.00 NOK
            """,
            "expense posting must be positive",
        ),
        (
            """
            2025-02-03 * "Split: Groceries"
              Expenses:Groceries  -60.00 NOK
              Assets:Receivable:Maria  60.00 NOK
            """,
            "generated split adjustment input is not supported",
        ),
    ],
)
def test_generate_splits_validation_failures(
    tmp_path: Path, capsys, transaction: str, expected_error: str
):
    config = write_split_config(tmp_path)
    header = dedent(
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Assets:Savings NOK
        2025-02-03 open Expenses:Dining NOK
        2025-02-03 open Expenses:Groceries NOK
        2025-02-03 open Assets:Receivable:Maria NOK
        """
    ).strip()
    transaction = dedent(transaction).strip()
    imported = write_ledger(
        tmp_path / "imports.beancount",
        header + "\n\n" + transaction,
    )

    assert main(["--config", str(config), "--year", "2025", str(imported)]) == 1

    captured = capsys.readouterr()
    assert expected_error in captured.err


def test_preserve_splits_carries_user_metadata_by_provider_id(
    tmp_path: Path, capsys
):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Old KIWI" "Old groceries"
          provider_transaction_id: "txn-kiwi-001"
          external_note: "not user owned"
          split: " MARIA : 50.0% "
          split_note: "  snacks, apples, and milk  "
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Fresh KIWI" "Fresh groceries"
          provider_transaction_id: "txn-kiwi-001"
          import_fingerprint: "fresh-fingerprint"
          Expenses:Groceries  121.00 NOK
          Assets:Bank:Checking  -121.00 NOK
        """,
    )

    assert preserve_main([str(old_imported), str(fresh_imported)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert '2025-02-03 * "Fresh KIWI" "Fresh groceries"' in captured.out
    assert re.search(r'provider_transaction_id:\s+"txn-kiwi-001"', captured.out)
    assert re.search(r'import_fingerprint:\s+"fresh-fingerprint"', captured.out)
    assert re.search(r'split:\s+"maria:50%"', captured.out)
    assert re.search(r'split_note:\s+"snacks, apples, and milk"', captured.out)
    assert re.search(r"\^split-provider-[a-f0-9]{24}", captured.out)
    assert "Old KIWI" not in captured.out
    assert "Old groceries" not in captured.out
    assert "external_note" not in captured.out
    assert "121.00 NOK" in captured.out


def test_preserve_splits_normalizes_posting_split_metadata(
    tmp_path: Path, capsys
):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Dining NOK

        2025-02-03 * "Restaurant"
          provider_transaction_id: "txn-restaurant-001"
          split_note: "  before  movie  "
          Expenses:Dining  100.00 NOK
            split: " MARIA : 33.3300 , olav:16.670% "
          Assets:Bank:Checking  -100.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Dining NOK

        2025-02-03 * "Restaurant"
          provider_transaction_id: "txn-restaurant-001"
          Expenses:Dining  100.00 NOK
          Assets:Bank:Checking  -100.00 NOK
        """,
    )

    assert preserve_main([str(old_imported), str(fresh_imported)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert re.search(r'split:\s+"maria:33.33%, olav:16.67%"', captured.out)
    assert re.search(r'split_note:\s+"before  movie"', captured.out)


def test_preserve_splits_replaces_stale_split_metadata_and_link(
    tmp_path: Path, capsys
):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI"
          provider_transaction_id: "txn-kiwi-001"
          split: "maria:25"
          Expenses:Groceries  80.00 NOK
          Assets:Bank:Checking  -80.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI" ^split-provider-stale
          provider_transaction_id: "txn-kiwi-001"
          split: "stale:99"
          split_note: "stale note"
          Expenses:Groceries  80.00 NOK
          Assets:Bank:Checking  -80.00 NOK
        """,
    )

    assert preserve_main([str(old_imported), str(fresh_imported)]) == 0

    captured = capsys.readouterr()
    assert re.search(r'split:\s+"maria:25%"', captured.out)
    assert "split_note" not in captured.out
    assert "split-provider-stale" not in captured.out
    assert len(re.findall(r"\^split-provider-[a-f0-9]{24}", captured.out)) == 1


def test_preserve_splits_check_mode_validates_without_output(tmp_path: Path, capsys):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI"
          provider_transaction_id: "txn-kiwi-001"
          split: "maria:50"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI"
          provider_transaction_id: "txn-kiwi-001"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert preserve_main(["--check", str(old_imported), str(fresh_imported)]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_preserve_splits_carries_user_metadata_by_computed_fingerprint(
    tmp_path: Path, capsys
):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI" "Groceries"
          split: " MARIA : 50.0% "
          split_note: "  weekly shop  "
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "KIWI" "Groceries"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert preserve_main([str(old_imported), str(fresh_imported)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert re.search(r'split:\s+"maria:50%"', captured.out)
    assert re.search(r'split_note:\s+"weekly shop"', captured.out)
    assert re.search(r"\^split-fingerprint-[a-f0-9]{24}", captured.out)


def test_preserve_splits_warns_for_orphaned_old_annotation(
    tmp_path: Path, capsys
):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Missing shop"
          import_fingerprint: "missing-shop"
          split: "maria:50"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Dining NOK

        2025-02-03 * "Restaurant"
          import_fingerprint: "restaurant"
          Expenses:Dining  80.00 NOK
          Assets:Bank:Checking  -80.00 NOK
        """,
    )

    assert preserve_main([str(old_imported), str(fresh_imported)]) == 0

    captured = capsys.readouterr()
    assert "preserve-splits: warning:" in captured.err
    assert "Missing shop" in captured.err
    assert "fingerprint 'missing-shop'" in captured.err
    assert '2025-02-03 * "Restaurant"' in captured.out
    assert "split:" not in captured.out


def test_preserve_splits_fails_when_fresh_matches_multiple_old_annotations(
    tmp_path: Path, capsys
):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Old groceries A"
          import_fingerprint: "shared-fingerprint"
          split: "maria:50"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK

        2025-02-04 * "Old groceries B"
          import_fingerprint: "shared-fingerprint"
          split: "olav:25"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Fresh groceries"
          import_fingerprint: "shared-fingerprint"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert preserve_main(["--check", str(old_imported), str(fresh_imported)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "fresh transaction matches multiple old annotated transactions" in captured.err
    assert "Old groceries A" in captured.err
    assert "Old groceries B" in captured.err
    assert "Fresh groceries" in captured.err


def test_preserve_splits_fails_when_old_annotation_matches_multiple_fresh(
    tmp_path: Path, capsys
):
    old_imported = write_ledger(
        tmp_path / "old.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Old groceries"
          import_fingerprint: "shared-fingerprint"
          split: "maria:50"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    fresh_imported = write_ledger(
        tmp_path / "fresh.beancount",
        """
        2025-02-03 open Assets:Bank:Checking NOK
        2025-02-03 open Expenses:Groceries NOK

        2025-02-03 * "Fresh groceries A"
          import_fingerprint: "shared-fingerprint"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK

        2025-02-04 * "Fresh groceries B"
          import_fingerprint: "shared-fingerprint"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )

    assert preserve_main([str(old_imported), str(fresh_imported)]) == 1

    captured = capsys.readouterr()
    assert "old annotated transaction matches multiple fresh transactions" in captured.err
    assert "Old groceries" in captured.err
    assert "Fresh groceries A" in captured.err
    assert "Fresh groceries B" in captured.err
