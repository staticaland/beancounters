"""Generate and preserve split annotations for imported transactions."""

from __future__ import annotations

import argparse
import hashlib
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
SPLIT_NOTE_META_KEY = "split_note"
GENERATED_BY_META_KEY = "generated_by"
SOURCE_PROVIDER_ID_META_KEY = "source_provider_id"
SOURCE_IMPORT_FINGERPRINT_META_KEY = "source_import_fingerprint"
GENERATED_BY_VALUE = "beancounters.generate-splits"
GENERATED_NARRATION_PREFIX = "Split: "
SPLIT_LINK_PREFIX = "split"
PROVIDER_ID_META_KEYS = (
    "provider_transaction_id",
    "transaction_id",
    "fitid",
)
IMPORT_FINGERPRINT_META_KEYS = (
    "import_fingerprint",
    "fingerprint",
)
SPLIT_PERSON_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SPLIT_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z0-9_-]+)\s*:\s*(?P<share>\d+(?:\.\d+)?)\s*%?\s*$"
)
EXACT_AMOUNT_SPLIT_RE = re.compile(
    r"^\s*[A-Za-z0-9_-]+\s*:\s*\d+(?:\.\d+)?\s+[A-Z][A-Z0-9'.-]*\s*$"
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


@dataclass(frozen=True)
class SourceIdentity:
    kind: str
    value: str
    meta_key: str


@dataclass(frozen=True)
class PreservedSplitMetadata:
    split: str
    split_note: str | None


@dataclass(frozen=True)
class PreservedSplitRecord:
    identity: SourceIdentity
    metadata: PreservedSplitMetadata
    entry: data.Transaction


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
        "--check",
        action="store_true",
        help="Validate split annotations without writing Beancount output.",
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

    if not args.check:
        printer.print_entries(adjustments, file=sys.stdout)
    return 0


def parse_preserve_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser_ = argparse.ArgumentParser(
        prog="preserve-splits",
        description="Carry split annotations from old importer output to fresh output.",
    )
    parser_.add_argument(
        "--check",
        action="store_true",
        help="Validate split preservation without writing Beancount output.",
    )
    parser_.add_argument(
        "old_imported",
        type=Path,
        help="Previous imported ledger containing user-owned split annotations.",
    )
    parser_.add_argument(
        "fresh_imported",
        type=Path,
        help="Fresh imported ledger to receive preserved split annotations.",
    )
    return parser_.parse_args(argv)


def preserve_main(argv: Sequence[str] | None = None) -> int:
    args = parse_preserve_args(argv)
    try:
        entries = preserve_split_annotations(args.old_imported, args.fresh_imported)
    except SplitGenerationError as exc:
        print(f"preserve-splits: error: {exc}", file=sys.stderr)
        return 1

    if not args.check:
        printer.print_entries(entries, file=sys.stdout)
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
        validate_generated_input(entry)
        annotations = annotations_for_transaction(entry)
        if not annotations:
            validate_split_note_requires_split(entry)
            continue
        adjustments.append(build_adjustment(entry, annotations, people))

    return adjustments


def preserve_split_annotations(
    old_imported_path: Path, fresh_imported_path: Path
) -> list[data.Directive]:
    old_entries = parse_ledger(old_imported_path)
    fresh_entries = parse_ledger(fresh_imported_path)
    preserved_records = preserved_split_metadata_records(old_entries)
    fresh_by_identity = fresh_transactions_by_identity(fresh_entries)
    preserved_by_identity = validate_preservation_matches(
        preserved_records, fresh_by_identity
    )

    merged_entries: list[data.Directive] = []
    for entry in fresh_entries:
        if not isinstance(entry, data.Transaction):
            merged_entries.append(entry)
            continue

        source_identity = source_identity_for_transaction(entry)
        preserved = preserved_by_identity.get(source_identity)
        if preserved is None:
            merged_entries.append(entry)
            continue

        merged_entries.append(
            transaction_with_preserved_split_metadata(
                entry, preserved, source_identity
            )
        )

    return merged_entries


def preserved_split_metadata_records(
    old_entries: Iterable[data.Directive],
) -> list[PreservedSplitRecord]:
    preserved: list[PreservedSplitRecord] = []
    for entry in old_entries:
        if not isinstance(entry, data.Transaction):
            continue

        validate_generated_input(entry)
        annotations = annotations_for_transaction(entry)
        if not annotations:
            validate_split_note_requires_split(entry)
            continue

        preserved.append(
            PreservedSplitRecord(
                identity=source_identity_for_transaction(entry),
                metadata=PreservedSplitMetadata(
                    split=normalize_split_annotations(annotations),
                    split_note=normalized_split_note(entry),
                ),
                entry=entry,
            )
        )

    return preserved


def fresh_transactions_by_identity(
    fresh_entries: Iterable[data.Directive],
) -> dict[SourceIdentity, list[data.Transaction]]:
    fresh_by_identity: dict[SourceIdentity, list[data.Transaction]] = {}
    for entry in fresh_entries:
        if not isinstance(entry, data.Transaction):
            continue
        fresh_by_identity.setdefault(source_identity_for_transaction(entry), []).append(
            entry
        )
    return fresh_by_identity


def validate_preservation_matches(
    preserved_records: Sequence[PreservedSplitRecord],
    fresh_by_identity: dict[SourceIdentity, list[data.Transaction]],
) -> dict[SourceIdentity, PreservedSplitMetadata]:
    old_by_identity: dict[SourceIdentity, list[PreservedSplitRecord]] = {}
    for record in preserved_records:
        old_by_identity.setdefault(record.identity, []).append(record)

    preserved_by_identity: dict[SourceIdentity, PreservedSplitMetadata] = {}
    for identity, records in old_by_identity.items():
        fresh_matches = fresh_by_identity.get(identity, [])
        if not fresh_matches:
            for record in records:
                warn_orphaned_annotation(record.entry, identity)
            continue
        if len(records) > 1:
            raise SplitGenerationError(
                "fresh transaction matches multiple old annotated transactions by "
                f"{identity_label(identity)}: {entry_list_context(fresh_matches)}; "
                f"old matches: {entry_list_context(record.entry for record in records)}"
            )
        if len(fresh_matches) > 1:
            raise SplitGenerationError(
                "old annotated transaction matches multiple fresh transactions by "
                f"{identity_label(identity)}: {transaction_context(records[0].entry)}; "
                f"fresh matches: {entry_list_context(fresh_matches)}"
            )
        preserved_by_identity[identity] = records[0].metadata

    return preserved_by_identity


def warn_orphaned_annotation(entry: data.Transaction, identity: SourceIdentity) -> None:
    print(
        "preserve-splits: warning: old annotated transaction was not found in fresh "
        f"import by {identity_label(identity)}: {transaction_context(entry)}",
        file=sys.stderr,
    )


def transaction_with_preserved_split_metadata(
    entry: data.Transaction,
    preserved: PreservedSplitMetadata,
    source_identity: SourceIdentity,
) -> data.Transaction:
    meta = dict(entry.meta)
    meta[SPLIT_META_KEY] = preserved.split
    if preserved.split_note is None:
        meta.pop(SPLIT_NOTE_META_KEY, None)
    else:
        meta[SPLIT_NOTE_META_KEY] = preserved.split_note

    links = frozenset(
        link for link in entry.links if not link.startswith(f"{SPLIT_LINK_PREFIX}-")
    )
    links = links | frozenset({split_link(source_identity)})
    return entry._replace(meta=meta, links=links)


def identity_label(identity: SourceIdentity) -> str:
    return f"{identity.kind} {identity.value!r}"


def entry_list_context(entries: Iterable[data.Transaction]) -> str:
    return "; ".join(transaction_context(entry) for entry in entries)


def transaction_context(entry: data.Transaction) -> str:
    payee = f"{entry.payee} " if entry.payee else ""
    return f"{location(entry)} {entry.date} {payee}{entry.narration!r}"


def normalize_split_annotations(annotations: Sequence[SplitAnnotation]) -> str:
    return ", ".join(
        f"{annotation.key}:{format_share(annotation.share)}%"
        for annotation in annotations
    )


def normalized_split_note(entry: data.Transaction) -> str | None:
    if SPLIT_NOTE_META_KEY not in entry.meta:
        return None
    split_note = entry.meta[SPLIT_NOTE_META_KEY]
    if not isinstance(split_note, str):
        raise SplitGenerationError(f"{location(entry)} split_note must be a string")
    return split_note.strip()


def format_share(share: Decimal) -> str:
    normalized = share.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


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

        key = normalize_split_key(raw_key, location(entry))
        if key in people:
            raise SplitGenerationError(
                f"{location(entry)} duplicate split person '{key}'"
            )
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
            if EXACT_AMOUNT_SPLIT_RE.match(raw_part):
                raise SplitGenerationError(
                    f"{source_location} exact amount split annotation {value!r} "
                    "is not supported in v1"
                )
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
            SplitAnnotation(
                key=normalize_split_key(match.group("key"), source_location),
                share=share,
            )
        )

    return annotations


def normalize_split_key(value: str, source_location: str) -> str:
    if not SPLIT_PERSON_KEY_RE.match(value):
        raise SplitGenerationError(
            f"{source_location} split person key {value!r} must be a simple slug"
        )
    return value.lower()


def build_adjustment(
    entry: data.Transaction,
    annotations: Sequence[SplitAnnotation],
    people: dict[str, SplitPerson],
) -> data.Transaction:
    expense_posting = validate_splittable_expense_transaction(entry)
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

    meta = data.new_metadata(
        entry.meta.get("filename", "<generated>"), entry.meta.get("lineno", 0)
    )
    if SPLIT_NOTE_META_KEY in entry.meta:
        split_note = entry.meta[SPLIT_NOTE_META_KEY]
        if not isinstance(split_note, str):
            raise SplitGenerationError(f"{location(entry)} split_note must be a string")
        meta[SPLIT_NOTE_META_KEY] = split_note
    source_identity = source_identity_for_transaction(entry)
    meta[GENERATED_BY_META_KEY] = GENERATED_BY_VALUE
    meta[source_identity.meta_key] = source_identity.value

    return data.Transaction(
        meta,
        entry.date,
        entry.flag,
        None,
        f"Split: {entry.narration}",
        frozenset(),
        frozenset({split_link(source_identity)}),
        postings,
    )


def source_identity_for_transaction(entry: data.Transaction) -> SourceIdentity:
    provider_id = first_string_meta(entry, PROVIDER_ID_META_KEYS)
    if provider_id is not None:
        return SourceIdentity(
            kind="provider",
            value=provider_id,
            meta_key=SOURCE_PROVIDER_ID_META_KEY,
        )

    import_fingerprint = first_string_meta(entry, IMPORT_FINGERPRINT_META_KEYS)
    if import_fingerprint is None:
        import_fingerprint = transaction_fingerprint(entry)
    return SourceIdentity(
        kind="fingerprint",
        value=import_fingerprint,
        meta_key=SOURCE_IMPORT_FINGERPRINT_META_KEY,
    )


def first_string_meta(entry: data.Transaction, keys: Sequence[str]) -> str | None:
    for key in keys:
        value = entry.meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def transaction_fingerprint(entry: data.Transaction) -> str:
    parts = [
        str(entry.date),
        entry.payee or "",
        entry.narration,
    ]
    for posting in entry.postings:
        units = posting.units
        parts.append(posting.account)
        if units is None:
            parts.extend(("", ""))
        else:
            parts.extend((str(units.number), units.currency))
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:24]


def split_link(source_identity: SourceIdentity) -> str:
    digest = hashlib.sha256(source_identity.value.encode("utf-8")).hexdigest()[:24]
    return f"{SPLIT_LINK_PREFIX}-{source_identity.kind}-{digest}"


def validate_generated_input(entry: data.Transaction) -> None:
    if entry.narration.startswith(GENERATED_NARRATION_PREFIX):
        raise SplitGenerationError(
            f"{location(entry)} generated split adjustment input is not supported"
        )


def validate_split_note_requires_split(entry: data.Transaction) -> None:
    if SPLIT_NOTE_META_KEY in entry.meta:
        raise SplitGenerationError(
            f"{location(entry)} split_note requires at least one split annotation"
        )


def validate_splittable_expense_transaction(
    entry: data.Transaction,
) -> data.Posting:
    expense_postings = [
        posting
        for posting in entry.postings
        if posting.account.startswith("Expenses:")
    ]
    if len(expense_postings) != 1:
        raise SplitGenerationError(
            f"{location(entry)} split transaction must have exactly one Expenses:* "
            "posting"
        )
    expense_posting = expense_postings[0]
    if expense_posting.units is None:
        raise SplitGenerationError(f"{location(entry)} expense posting has no amount")
    if expense_posting.units.number <= 0:
        raise SplitGenerationError(
            f"{location(entry)} split transaction expense posting must be positive"
        )
    return expense_posting


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
