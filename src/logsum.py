from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, NamedTuple, TextIO

UNKNOWN = "unknown"
REQUIRED_COLUMNS = ("service", "level")
EMPTY_MESSAGE = "No events found."


class InputError(Exception):
    """Input cannot be processed; maps to exit status 1."""


class _Columns(NamedTuple):
    """Positions of the columns logsum needs, plus the expected row width."""

    service: int
    level: int
    width: int


def _read_columns(reader: Any) -> _Columns:
    """Consume the header row and locate the required columns."""
    try:
        header = next(reader, None)
    except csv.Error as exc:
        raise InputError(f"cannot parse header: {exc}") from exc
    if header is None:
        raise InputError("file is empty: no header row")

    names = [name.strip() for name in header]
    missing = [col for col in REQUIRED_COLUMNS if col not in names]
    if missing:
        raise InputError("missing required column(s): " + ", ".join(missing))

    return _Columns(names.index("service"), names.index("level"), len(names))


def _valid_rows(reader: Any, width: int, warn: TextIO) -> Iterator[list[str]]:
    """Yield data rows of the expected width.

    Blank lines are skipped silently. Unparseable and wrong-width rows are
    skipped with a warning on ``warn``.
    """
    while True:
        try:
            row = next(reader)
        except StopIteration:
            return
        except csv.Error as exc:
            print(
                f"warning: line {reader.line_num}: skipping unparseable row: {exc}",
                file=warn,
            )
            continue

        if not row:  # blank line
            continue
        if len(row) != width:
            print(
                f"warning: line {reader.line_num}: skipping malformed row "
                f"(expected {width} columns, got {len(row)})",
                file=warn,
            )
            continue
        yield row


def count_events(
    lines: Iterable[str], warn: TextIO | None = None
) -> Counter[tuple[str, str]]:
    """Count rows per (service, level) from CSV lines."""
    warn = warn if warn is not None else sys.stderr
    reader = csv.reader(lines)
    columns = _read_columns(reader)

    return Counter(
        (
            row[columns.service].strip() or UNKNOWN,
            row[columns.level].strip() or UNKNOWN,
        )
        for row in _valid_rows(reader, columns.width, warn)
    )


def format_summary(counts: Counter[tuple[str, str]]) -> list[str]:
    """Render sorted summary lines: service, level, count."""
    if not counts:
        return [EMPTY_MESSAGE]
    rows = sorted(counts.items())
    service_w = max(len(service) for (service, _), _ in rows)
    level_w = max(len(level) for (_, level), _ in rows)
    return [
        f"{service:<{service_w}}  {level:<{level_w}}  {count}"
        for (service, level), count in rows
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns the process exit status."""
    parser = argparse.ArgumentParser(
        prog="logsum",
        description="Summarize log events by service and level.",
    )
    parser.add_argument("csv_path", metavar="EVENTS_CSV", help="path to events CSV")
    args = parser.parse_args(argv)
    path: str = args.csv_path

    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            counts = count_events(handle)
    except FileNotFoundError:
        print(f"error: input file not found: {path}", file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return 1
    except InputError as exc:
        print(f"error: {path}: {exc}", file=sys.stderr)
        return 1

    print("\n".join(format_summary(counts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
