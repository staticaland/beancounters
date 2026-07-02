"""Safe one-command import/re-import pipeline."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from beancount.core import data
from beancount.parser import printer
from beangulp import extract, identify, utils

from beancounters.importers import get_importers
from beancounters.splits import (
    SPLIT_META_KEY,
    SplitGenerationError,
    generate_split_adjustments,
    parse_ledger,
    preserve_split_annotations,
)


class ReimportError(Exception):
    """Raised when the safe re-import pipeline cannot complete."""


@dataclass(frozen=True)
class ReimportSummary:
    transactions: int
    duplicates: int
    splits_preserved: int
    generated_splits: int
    import_path: Path
    generated_path: Path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reimport",
        description="Safely import, preserve split annotations, and regenerate splits.",
    )
    parser.add_argument(
        "--year",
        required=True,
        type=int,
        help="Year used for imports/{year}.beancount and generated/{year}-splits.beancount.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data"),
        help="Provider export file or directory to import.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("main.beancount"),
        help="Config ledger containing split-person directives.",
    )
    parser.add_argument(
        "--imports-dir",
        type=Path,
        default=Path("imports"),
        help="Directory containing year-scoped imported ledgers.",
    )
    parser.add_argument(
        "--generated-dir",
        type=Path,
        default=Path("generated"),
        help="Directory containing year-scoped generated split ledgers.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = reimport(
            year=args.year,
            data_path=args.data,
            config_path=args.config,
            imports_dir=args.imports_dir,
            generated_dir=args.generated_dir,
        )
    except (ReimportError, SplitGenerationError) as exc:
        print(f"reimport: error: {exc}", file=sys.stderr)
        return 1

    print(format_summary(summary))
    return 0


def reimport(
    *,
    year: int,
    data_path: Path,
    config_path: Path,
    imports_dir: Path,
    generated_dir: Path,
) -> ReimportSummary:
    imports_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    import_path = imports_dir / f"{year}.beancount"
    generated_path = generated_dir / f"{year}-splits.beancount"
    temp_paths: list[Path] = []

    try:
        fresh_path = make_temp_path(imports_dir, f".{year}.fresh.", ".beancount")
        temp_paths.append(fresh_path)
        transactions, duplicates = extract_imports(data_path, fresh_path)

        preserved_path = make_temp_path(imports_dir, f".{year}.preserved.", ".beancount")
        temp_paths.append(preserved_path)
        if import_path.exists():
            preserved_entries = preserve_split_annotations(import_path, fresh_path)
            write_entries(preserved_path, preserved_entries)
        else:
            preserved_path.write_text(
                fresh_path.read_text(encoding="utf-8"), encoding="utf-8"
            )

        parse_ledger(preserved_path)
        generated_temp_path = make_temp_path(
            generated_dir, f".{year}-splits.", ".beancount"
        )
        temp_paths.append(generated_temp_path)
        adjustments = generate_split_adjustments(config_path, [preserved_path], year)
        write_entries(generated_temp_path, adjustments)
        parse_ledger(generated_temp_path)

        splits_preserved = count_split_transactions(preserved_path) - count_split_transactions(
            fresh_path
        )

        os.replace(preserved_path, import_path)
        temp_paths.remove(preserved_path)
        os.replace(generated_temp_path, generated_path)
        temp_paths.remove(generated_temp_path)

        return ReimportSummary(
            transactions=transactions,
            duplicates=duplicates,
            splits_preserved=max(splits_preserved, 0),
            generated_splits=len(adjustments),
            import_path=import_path,
            generated_path=generated_path,
        )
    finally:
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)


def extract_imports(data_path: Path, output_path: Path) -> tuple[int, int]:
    if not data_path.exists():
        raise ReimportError(f"{data_path} does not exist")

    importers = get_importers()
    existing_entries: list[data.Directive] = []
    extracted = []
    transaction_count = 0
    duplicate_count = 0

    for filename in utils.walk([str(data_path)]):
        importer = identify.identify(importers, filename)
        if importer is None:
            continue

        entries = extract.extract_from_file(importer, filename, existing_entries)
        importer.deduplicate(entries, existing_entries)
        existing_entries.extend(entries)
        transaction_count += count_transactions(entries)
        duplicate_count += count_duplicate_entries(entries)
        extracted.append((filename, entries, importer.account(filename), importer))

    extract.sort_extracted_entries(extracted)
    with output_path.open("w", encoding="utf-8") as output:
        extract.print_extracted_entries(extracted, output)

    if not extracted:
        raise ReimportError(f"no importable files found under {data_path}")

    return transaction_count, duplicate_count


def make_temp_path(directory: Path, prefix: str, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=directory, prefix=prefix, suffix=suffix, delete=False
    ) as temp_file:
        return Path(temp_file.name)


def write_entries(path: Path, entries: Sequence[data.Directive]) -> None:
    with path.open("w", encoding="utf-8") as output:
        printer.print_entries(entries, file=output)


def count_transactions(entries: Sequence[data.Directive]) -> int:
    return sum(isinstance(entry, data.Transaction) for entry in entries)


def count_duplicate_entries(entries: Sequence[data.Directive]) -> int:
    return sum(bool(entry.meta.get(extract.DUPLICATE)) for entry in entries)


def count_split_transactions(path: Path) -> int:
    return sum(
        isinstance(entry, data.Transaction) and SPLIT_META_KEY in entry.meta
        for entry in parse_ledger(path)
    )


def format_summary(summary: ReimportSummary) -> str:
    return (
        f"reimport: {summary.transactions} transactions, "
        f"{summary.duplicates} duplicates marked, "
        f"{summary.splits_preserved} splits preserved, "
        f"{summary.generated_splits} split adjustments generated -> "
        f"{summary.import_path} and {summary.generated_path}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
