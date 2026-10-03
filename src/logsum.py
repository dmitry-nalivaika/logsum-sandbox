from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import TextIO

UNKNOWN = "unknown"
REQUIRED_COLUMNS = ("service", "level")
EMPTY_MESSAGE = "No events found."


class InputError(Exception):
    """Input cannot be processed; maps to exit status 1."""


def count_events(
    lines: Iterable[str], warn: TextIO | None = None
) -> Counter[tuple[str, str]]:
    """Count rows per (service, level) from CSV lines."""
    warn = warn if warn is not None else sys.stderr
    reader = csv.reader(lines)

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

    service_idx = names.index("service")
    level_idx = names.index("level")
    width = len(names)
    counts: Counter[tuple[str, str]] = Counter()

    while True:
        try:
            row = next(reader)
        except StopIteration:
            break
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

        service = row[service_idx].strip() or UNKNOWN
        level = row[level_idx].strip() or UNKNOWN
        counts[(service, level)] += 1

    return counts


def format_summary(counts: Counter[tuple[str, str]]) -> list[str]:
    """Render sorted summary lines: service, level, count."""
    if not counts:
        return [EMPTY_MESSAGE]
    rows = sorted(counts.items(), reverse=True)
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
