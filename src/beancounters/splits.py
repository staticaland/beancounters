"""Generate split adjustment transactions from inline split annotations."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Sequence

from beancount.core import data
from beancount.core.amount import Amount
from beancount.parser import parser, printer


SPLIT_PERSON_DIRECTIVE = "split-person"
SPLIT_META_KEY = "split"
SPLIT_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z0-9_-]+)\s*:\s*(?P<share>\d+(?:\.\d+)?)\s*%?\s*$"
)


class SplitGenerationError(Exception):
    """Raised when split generation cannot continue."""


@dataclass(frozen=True)
class SplitPerson:
    key: str
    account: str


@dataclass(frozen=True)
class SplitAnnotation:
    key: str
    share: Decimal


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser_ = argparse.ArgumentParser(
        prog="generate-splits",
        description="Generate Beancount split adjustment transactions.",
    )
    parser_.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Config ledger containing split-person directives and opened accounts.",
    )
    parser_.add_argument(
        "--year",
        required=True,
        type=int,
        help="Only generate adjustments for source transactions in this year.",
    )
    parser_.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Imported ledger files to scan for inline split annotations.",
    )
    return parser_.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        adjustments = generate_split_adjustments(args.config, args.inputs, args.year)
    except SplitGenerationError as exc:
        print(f"generate-splits: error: {exc}", file=sys.stderr)
        return 1

    printer.print_entries(adjustments, file=sys.stdout)
    return 0


def generate_split_adjustments(
    config_path: Path, input_paths: Iterable[Path], year: int
) -> list[data.Transaction]:
    people = load_split_people(config_path)
    entries = []
    for input_path in input_paths:
        entries.extend(parse_ledger(input_path))

    adjustments = []
    for entry in entries:
        if not isinstance(entry, data.Transaction) or entry.date.year != year:
            continue
        annotations = annotations_for_transaction(entry)
        if annotations:
            adjustments.append(build_adjustment(entry, annotations, people))

    return adjustments


def load_split_people(config_path: Path) -> dict[str, SplitPerson]:
    entries = parse_ledger(config_path)
    opened_accounts = {
        entry.account for entry in entries if isinstance(entry, data.Open)
    }
    people: dict[str, SplitPerson] = {}

    for entry in entries:
        if not isinstance(entry, data.Custom) or entry.type != SPLIT_PERSON_DIRECTIVE:
            continue
        if len(entry.values) != 2:
            raise SplitGenerationError(
                f"{location(entry)} split-person must be: "
                'custom "split-person" "key" Assets:Receivable:Name'
            )

        raw_key = entry.values[0].value
        account = entry.values[1].value
        if not isinstance(raw_key, str) or not isinstance(account, str):
            raise SplitGenerationError(
                f"{location(entry)} split-person requires a string key and account"
            )

        key = raw_key.lower()
        if account not in opened_accounts:
            raise SplitGenerationError(
                f"{location(entry)} split person '{key}' account {account} "
                "must be opened in the config ledger"
            )
        people[key] = SplitPerson(key=key, account=account)

    return people


def annotations_for_transaction(entry: data.Transaction) -> list[SplitAnnotation]:
    annotations = []
    if SPLIT_META_KEY in entry.meta:
        annotations.extend(
            parse_split_meta(entry.meta[SPLIT_META_KEY], location(entry))
        )

    for posting in entry.postings:
        if not posting.meta or SPLIT_META_KEY not in posting.meta:
            continue
        annotations.extend(
            parse_split_meta(posting.meta[SPLIT_META_KEY], posting_location(posting))
        )
    return annotations


def parse_split_meta(value: object, source_location: str) -> list[SplitAnnotation]:
    if not isinstance(value, str):
        raise SplitGenerationError(f"{source_location} split must be a string")

    annotations = []
    for raw_part in value.split(","):
        match = SPLIT_RE.match(raw_part)
        if not match:
            raise SplitGenerationError(
                f"{source_location} invalid split annotation {value!r}; "
                "expected key:percent"
            )
        try:
            share = Decimal(match.group("share"))
        except InvalidOperation as exc:
            raise SplitGenerationError(
                f"{source_location} invalid split percentage {value!r}"
            ) from exc
        annotations.append(
            SplitAnnotation(key=match.group("key").lower(), share=share)
        )

    return annotations


def build_adjustment(
    entry: data.Transaction,
    annotations: Sequence[SplitAnnotation],
    people: dict[str, SplitPerson],
) -> data.Transaction:
    expense_posting = find_single_positive_expense_posting(entry)
    if expense_posting.units is None:
        raise SplitGenerationError(f"{location(entry)} expense posting has no amount")

    postings: list[data.Posting] = []
    total_share = Decimal("0")
    for annotation in annotations:
        person = people.get(annotation.key)
        if person is None:
            raise SplitGenerationError(
                f"{location(entry)} unknown split person '{annotation.key}'"
            )
        total_share += annotation.share
        amount = split_amount(expense_posting.units.number, annotation.share)
        postings.append(
            new_posting(person.account, amount, expense_posting.units.currency)
        )

    if total_share > Decimal("100"):
        raise SplitGenerationError(
            f"{location(entry)} split shares total {total_share}% which exceeds 100%"
        )

    total_amount = sum(
        (posting.units.number for posting in postings if posting.units), Decimal("0")
    )
    postings.append(
        new_posting(
            expense_posting.account,
            -total_amount,
            expense_posting.units.currency,
        )
    )

    return data.Transaction(
        data.new_metadata(
            entry.meta.get("filename", "<generated>"), entry.meta.get("lineno", 0)
        ),
        entry.date,
        entry.flag,
        None,
        f"Split: {entry.narration}",
        frozenset(),
        frozenset(),
        postings,
    )


def find_single_positive_expense_posting(entry: data.Transaction) -> data.Posting:
    expense_postings = [
        posting
        for posting in entry.postings
        if posting.account.startswith("Expenses:")
        and posting.units is not None
        and posting.units.number > 0
    ]
    if len(expense_postings) != 1:
        raise SplitGenerationError(
            f"{location(entry)} split transaction must have exactly one positive "
            "Expenses:* posting"
        )
    return expense_postings[0]


def split_amount(amount: Decimal, share: Decimal) -> Decimal:
    return (amount * share / Decimal("100")).quantize(
        amount_quantum(amount), rounding=ROUND_HALF_UP
    )


def amount_quantum(amount: Decimal) -> Decimal:
    exponent = amount.as_tuple().exponent
    if exponent >= 0:
        return Decimal("1")
    return Decimal("1").scaleb(exponent)


def new_posting(account: str, number: Decimal, currency: str) -> data.Posting:
    return data.Posting(account, Amount(number, currency), None, None, None, None)


def parse_ledger(path: Path) -> list[data.Directive]:
    entries, errors, _ = parser.parse_file(str(path))
    if errors:
        first_error = errors[0]
        raise SplitGenerationError(f"{path}: {first_error.message}")
    return entries


def location(entry: data.Directive) -> str:
    return f"{entry.meta.get('filename', '<unknown>')}:{entry.meta.get('lineno', '?')}"


def posting_location(posting: data.Posting) -> str:
    if posting.meta is None:
        return "<unknown>:?"
    return f"{posting.meta.get('filename', '<unknown>')}:{posting.meta.get('lineno', '?')}"


if __name__ == "__main__":
    raise SystemExit(main())
