from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GENERATED = ROOT / "generated"


def test_demo_data_has_full_year_and_single_overlap_export() -> None:
    expected = sorted([f"2025-{month:02d}" for month in range(1, 13)] + ["2025-02-15_to_2025-04-15"])

    assert sorted(path.stem for path in (DATA / "sparebank1").glob("*.csv")) == expected
    assert sorted(path.stem for path in (DATA / "dnb").glob("*.xlsx")) == expected
    assert sorted(path.stem for path in (DATA / "amex").glob("*.qbo")) == expected


def test_demo_data_provider_files_are_structurally_valid() -> None:
    with (DATA / "sparebank1" / "2025-01.csv").open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter=";")
        assert next(reader) == ["Dato", "Beskrivelse", "Rentedato", "Inn", "Ut", "Til konto", "Fra konto", ""]
        assert sum(1 for _ in reader) >= 12

    workbook = load_workbook(DATA / "dnb" / "2025-01.xlsx", read_only=True)
    worksheet = workbook.active
    assert [cell.value for cell in next(worksheet.iter_rows(max_row=1))] == ["Dato", "Beløpet gjelder", "Valuta", "Kurs", "Inn", "Ut"]
    assert worksheet.max_row >= 9

    qbo = (DATA / "amex" / "2025-01.qbo").read_text(encoding="utf-8")
    root = ET.fromstring(qbo.split("?>", maxsplit=2)[-1])
    assert len(root.findall(".//STMTTRN")) >= 6


def test_demo_data_includes_generated_mortgage_accounting() -> None:
    mortgage = (GENERATED / "2025-mortgage.beancount").read_text(encoding="utf-8")

    assert "Liabilities:Loan:Mortgage" in mortgage
    assert "Expenses:Interest:Mortgage" in mortgage
    assert "Extra Mortgage Payment - Vacation bonus" in mortgage
    assert "Extra Mortgage Payment - Year-end savings" in mortgage


def test_generated_demo_data_imports_with_configured_importers() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "beancounters.importers", "extract", str(DATA)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Assets:Bank:SpareBank1:Checking" in result.stdout
    assert "Liabilities:CreditCard:DNB" in result.stdout
    assert "Liabilities:CreditCard:Amex" in result.stdout


def test_demo_query_script_reports_loan_insights(tmp_path: Path) -> None:
    output = tmp_path / "queries.md"
    result = subprocess.run(
        ["bash", "scripts/run-demo-queries.sh", "main.beancount", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = output.read_text(encoding="utf-8")
    assert "## Loan Insights" in report
    assert "How Much Do I Save by Repaying Loan?" in report
    assert "Extra Mortgage Payment - Vacation bonus" in report
    assert "Loan Principal Paid by Month" in report
    assert "Liabilities:Loan:Mortgage" in report
