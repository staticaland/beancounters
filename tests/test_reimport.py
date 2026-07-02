"""Tests for the safe one-command re-import pipeline."""

from pathlib import Path
from textwrap import dedent

from beancounters import reimport as reimport_module
from beancounters.reimport import main, reimport


def write_ledger(path: Path, text: str) -> Path:
    path.write_text(dedent(text).strip() + "\n", encoding="utf-8")
    return path


def write_config(tmp_path: Path) -> Path:
    return write_ledger(
        tmp_path / "main.beancount",
        """
        2025-01-01 open Assets:Receivable:Maria NOK
        2025-01-01 custom "split-person" "maria" Assets:Receivable:Maria
        """,
    )


def test_reimport_preserves_annotations_regenerates_splits_and_replaces_atomically(
    tmp_path: Path, monkeypatch
):
    data_dir = tmp_path / "data"
    imports_dir = tmp_path / "imports"
    generated_dir = tmp_path / "generated"
    data_dir.mkdir()
    imports_dir.mkdir()
    generated_dir.mkdir()
    config = write_config(tmp_path)
    old_import = write_ledger(
        imports_dir / "2025.beancount",
        """
        2025-02-03 * "Old KIWI"
          import_fingerprint: "kiwi-001"
          split: "maria:50%"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    generated_path = write_ledger(
        generated_dir / "2025-splits.beancount",
        """
        2025-01-01 note Assets:Receivable:Maria "stale"
        """,
    )

    def fake_extract(_data_path: Path, output_path: Path) -> tuple[int, int]:
        write_ledger(
            output_path,
            """
            2025-02-03 * "Fresh KIWI"
              import_fingerprint: "kiwi-001"
              Expenses:Groceries  122.00 NOK
              Assets:Bank:Checking  -122.00 NOK
            """,
        )
        return (1, 0)

    monkeypatch.setattr(reimport_module, "extract_imports", fake_extract)

    summary = reimport(
        year=2025,
        data_path=data_dir,
        config_path=config,
        imports_dir=imports_dir,
        generated_dir=generated_dir,
    )

    assert summary.transactions == 1
    assert summary.duplicates == 0
    assert summary.splits_preserved == 1
    assert summary.generated_splits == 1
    assert '2025-02-03 * "Fresh KIWI"' in old_import.read_text(encoding="utf-8")
    assert 'split: "maria:50%"' in old_import.read_text(encoding="utf-8")
    assert "122.00 NOK" in old_import.read_text(encoding="utf-8")
    assert '2025-02-03 * "Split: Fresh KIWI"' in generated_path.read_text(
        encoding="utf-8"
    )


def test_reimport_leaves_existing_import_untouched_when_validation_fails(
    tmp_path: Path, monkeypatch
):
    data_dir = tmp_path / "data"
    imports_dir = tmp_path / "imports"
    generated_dir = tmp_path / "generated"
    data_dir.mkdir()
    imports_dir.mkdir()
    generated_dir.mkdir()
    config = write_config(tmp_path)
    existing = write_ledger(
        imports_dir / "2025.beancount",
        """
        2025-02-03 * "Old KIWI"
          import_fingerprint: "kiwi-001"
          split: "unknown:50%"
          Expenses:Groceries  120.00 NOK
          Assets:Bank:Checking  -120.00 NOK
        """,
    )
    original_import = existing.read_text(encoding="utf-8")

    def fake_extract(_data_path: Path, output_path: Path) -> tuple[int, int]:
        write_ledger(
            output_path,
            """
            2025-02-03 * "Fresh KIWI"
              import_fingerprint: "kiwi-001"
              Expenses:Groceries  122.00 NOK
              Assets:Bank:Checking  -122.00 NOK
            """,
        )
        return (1, 0)

    monkeypatch.setattr(reimport_module, "extract_imports", fake_extract)

    exit_code = main(
        [
            "--year",
            "2025",
            "--data",
            str(data_dir),
            "--config",
            str(config),
            "--imports-dir",
            str(imports_dir),
            "--generated-dir",
            str(generated_dir),
        ]
    )

    assert exit_code == 1
    assert existing.read_text(encoding="utf-8") == original_import
    assert not (generated_dir / "2025-splits.beancount").exists()


def test_reimport_creates_first_import_without_preservation(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    imports_dir = tmp_path / "imports"
    generated_dir = tmp_path / "generated"
    data_dir.mkdir()
    config = write_config(tmp_path)

    def fake_extract(_data_path: Path, output_path: Path) -> tuple[int, int]:
        write_ledger(
            output_path,
            """
            2025-02-03 * "Fresh KIWI"
              import_fingerprint: "kiwi-001"
              Expenses:Groceries  122.00 NOK
              Assets:Bank:Checking  -122.00 NOK
            """,
        )
        return (1, 0)

    monkeypatch.setattr(reimport_module, "extract_imports", fake_extract)

    summary = reimport(
        year=2025,
        data_path=data_dir,
        config_path=config,
        imports_dir=imports_dir,
        generated_dir=generated_dir,
    )

    assert summary.splits_preserved == 0
    assert (imports_dir / "2025.beancount").exists()
    assert (generated_dir / "2025-splits.beancount").exists()
