"""Black-box tests for the logsum CLI, written from spec.md only.

The CLI is exercised as a subprocess (``python src/logsum.py <csv>``), so the
tests depend only on the observable contract: argv, stdout, stderr, exit code.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "src" / "logsum.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

HEADER = "timestamp,level,service,message\n"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def parse_rows(stdout: str) -> list[tuple[str, str, int]]:
    """Parse summary output into (service, level, count) tuples.

    Splits on whitespace so the test does not depend on exact column padding.
    """
    rows = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        service, level, count = line.split()
        rows.append((service, level, int(count)))
    return rows


def summary(path: Path) -> dict[tuple[str, str], int]:
    result = run_cli(path)
    assert result.returncode == 0, result.stderr
    return {(s, lvl): n for s, lvl, n in parse_rows(result.stdout)}


def write_csv(tmp_path: Path, body: str, name: str = "events.csv") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# AC1: CLI invocation / positional argument
# --------------------------------------------------------------------------


class TestCliInvocation:
    def test_script_exists(self) -> None:
        assert SCRIPT.is_file()

    def test_path_is_required(self) -> None:
        result = run_cli()
        assert result.returncode != 0
        assert result.stderr.strip() != ""
        assert result.stdout == ""

    def test_accepts_positional_path(self) -> None:
        result = run_cli(FIXTURES / "basic.csv")
        assert result.returncode == 0

    def test_accepts_relative_path(self, tmp_path: Path) -> None:
        write_csv(tmp_path, HEADER + "t,INFO,cart-api,m\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "events.csv"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0
        assert parse_rows(result.stdout) == [("cart-api", "INFO", 1)]


# --------------------------------------------------------------------------
# AC3, AC4, AC5: grouping and counting
# --------------------------------------------------------------------------


class TestGrouping:
    def test_one_row_per_unique_service_level_pair(self) -> None:
        rows = parse_rows(run_cli(FIXTURES / "basic.csv").stdout)
        pairs = [(s, lvl) for s, lvl, _ in rows]
        assert len(pairs) == len(set(pairs))
        assert set(pairs) == {
            ("cart-api", "DEBUG"),
            ("cart-api", "INFO"),
            ("checkout-service", "ERROR"),
            ("checkout-service", "INFO"),
            ("identity-service", "INFO"),
            ("identity-service", "WARN"),
        }

    def test_counts_match_number_of_data_rows(self) -> None:
        assert summary(FIXTURES / "basic.csv") == {
            ("cart-api", "DEBUG"): 1,
            ("cart-api", "INFO"): 2,
            ("checkout-service", "ERROR"): 2,
            ("checkout-service", "INFO"): 2,
            ("identity-service", "INFO"): 1,
            ("identity-service", "WARN"): 1,
        }

    def test_total_count_equals_data_row_count(self) -> None:
        assert sum(summary(FIXTURES / "basic.csv").values()) == 9

    def test_each_row_has_service_level_and_count(self) -> None:
        result = run_cli(FIXTURES / "basic.csv")
        for line in result.stdout.splitlines():
            fields = line.split()
            assert len(fields) == 3
            assert fields[2].isdigit()

    def test_same_level_different_service_are_separate(self, tmp_path: Path) -> None:
        path = write_csv(
            tmp_path,
            HEADER + "t,INFO,cart-api,a\nt,INFO,checkout-service,b\n",
        )
        assert summary(path) == {
            ("cart-api", "INFO"): 1,
            ("checkout-service", "INFO"): 1,
        }

    def test_same_service_different_level_are_separate(self, tmp_path: Path) -> None:
        path = write_csv(
            tmp_path,
            HEADER + "t,INFO,cart-api,a\nt,ERROR,cart-api,b\n",
        )
        assert summary(path) == {
            ("cart-api", "INFO"): 1,
            ("cart-api", "ERROR"): 1,
        }

    def test_level_match_is_exact_case_sensitive(self, tmp_path: Path) -> None:
        # Spec: "exact (service, level) combination"; levels counted as provided.
        path = write_csv(
            tmp_path,
            HEADER + "t,INFO,cart-api,a\nt,info,cart-api,b\n",
        )
        assert summary(path) == {
            ("cart-api", "INFO"): 1,
            ("cart-api", "info"): 1,
        }

    def test_nonstandard_levels_are_counted_as_provided(self, tmp_path: Path) -> None:
        # Out of scope: validation of allowed log levels.
        path = write_csv(tmp_path, HEADER + "t,BANANA,cart-api,a\n")
        assert summary(path) == {("cart-api", "BANANA"): 1}

    def test_column_order_in_header_does_not_matter(self, tmp_path: Path) -> None:
        path = write_csv(
            tmp_path,
            "message,service,level,timestamp\nm,cart-api,INFO,t\nm,cart-api,INFO,t\n",
        )
        assert summary(path) == {("cart-api", "INFO"): 2}

    def test_quoted_fields_with_commas_in_message(self, tmp_path: Path) -> None:
        path = write_csv(
            tmp_path,
            HEADER + 't,INFO,cart-api,"item added, qty=2"\n',
        )
        assert summary(path) == {("cart-api", "INFO"): 1}

    def test_crlf_line_endings(self, tmp_path: Path) -> None:
        path = tmp_path / "crlf.csv"
        path.write_bytes(
            b"timestamp,level,service,message\r\nt,INFO,cart-api,a\r\nt,INFO,cart-api,b\r\n"
        )
        assert summary(path) == {("cart-api", "INFO"): 2}


# --------------------------------------------------------------------------
# AC6: sort order
# --------------------------------------------------------------------------


class TestSorting:
    def test_sorted_by_service_then_level(self) -> None:
        rows = parse_rows(run_cli(FIXTURES / "unsorted.csv").stdout)
        assert [(s, lvl) for s, lvl, _ in rows] == [
            ("cart-api", "ERROR"),
            ("cart-api", "INFO"),
            ("checkout-service", "DEBUG"),
            ("checkout-service", "ERROR"),
            ("checkout-service", "INFO"),
            ("identity-service", "INFO"),
            ("identity-service", "WARN"),
        ]

    def test_output_order_is_independent_of_input_order(self, tmp_path: Path) -> None:
        forward = HEADER + "t,A,s1,m\nt,B,s1,m\nt,A,s2,m\nt,B,s2,m\n"
        backward = HEADER + "t,B,s2,m\nt,A,s2,m\nt,B,s1,m\nt,A,s1,m\n"
        out1 = run_cli(write_csv(tmp_path, forward, "a.csv")).stdout
        out2 = run_cli(write_csv(tmp_path, backward, "b.csv")).stdout
        assert out1 == out2
        assert [(s, lvl) for s, lvl, _ in parse_rows(out1)] == [
            ("s1", "A"),
            ("s1", "B"),
            ("s2", "A"),
            ("s2", "B"),
        ]

    def test_service_takes_priority_over_level(self, tmp_path: Path) -> None:
        # service "a" / level "Z" must come before service "b" / level "A"
        path = write_csv(tmp_path, HEADER + "t,A,b,m\nt,Z,a,m\n")
        rows = parse_rows(run_cli(path).stdout)
        assert [(s, lvl) for s, lvl, _ in rows] == [("a", "Z"), ("b", "A")]

    def test_unknown_sorts_alphabetically_with_others(self, tmp_path: Path) -> None:
        path = write_csv(
            tmp_path,
            HEADER + "t,INFO,,m\nt,INFO,cart-api,m\nt,INFO,zeta,m\n",
        )
        rows = parse_rows(run_cli(path).stdout)
        assert [s for s, _, _ in rows] == ["cart-api", "unknown", "zeta"]


# --------------------------------------------------------------------------
# AC7, AC8, AC9: exit code, stdout, input not modified
# --------------------------------------------------------------------------


class TestOutputChannelsAndExitCode:
    def test_success_exits_zero(self) -> None:
        assert run_cli(FIXTURES / "basic.csv").returncode == 0

    def test_summary_goes_to_stdout(self) -> None:
        result = run_cli(FIXTURES / "basic.csv")
        assert "checkout-service" in result.stdout
        assert "cart-api" in result.stdout
        assert "identity-service" in result.stdout

    def test_summary_not_written_to_stderr_on_clean_input(self) -> None:
        result = run_cli(FIXTURES / "basic.csv")
        assert result.stderr == ""

    def test_input_file_is_not_modified(self, tmp_path: Path) -> None:
        path = write_csv(tmp_path, (FIXTURES / "basic.csv").read_text())
        before_bytes = path.read_bytes()
        before_stat = path.stat()
        run_cli(path)
        after_stat = path.stat()
        assert path.read_bytes() == before_bytes
        assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
        assert after_stat.st_size == before_stat.st_size

    def test_input_file_not_modified_on_malformed_input(self, tmp_path: Path) -> None:
        path = write_csv(tmp_path, (FIXTURES / "malformed_rows.csv").read_text())
        before = path.read_bytes()
        run_cli(path)
        assert path.read_bytes() == before

    def test_no_extra_files_created_next_to_input(self, tmp_path: Path) -> None:
        path = write_csv(tmp_path, (FIXTURES / "basic.csv").read_text())
        run_cli(path)
        assert [p.name for p in tmp_path.iterdir()] == [path.name]


# --------------------------------------------------------------------------
# Edge case: empty input (header present, no data rows)
# --------------------------------------------------------------------------


class TestEmptyInput:
    def test_header_only_prints_no_events_found(self) -> None:
        result = run_cli(FIXTURES / "header_only.csv")
        assert result.stdout.strip() == "No events found."

    def test_header_only_exits_zero(self) -> None:
        assert run_cli(FIXTURES / "header_only.csv").returncode == 0

    def test_header_only_message_goes_to_stdout_not_stderr(self) -> None:
        result = run_cli(FIXTURES / "header_only.csv")
        assert "No events found." in result.stdout
        assert "No events found." not in result.stderr

    def test_header_only_without_trailing_newline(self, tmp_path: Path) -> None:
        path = write_csv(tmp_path, HEADER.rstrip("\n"))
        result = run_cli(path)
        assert result.returncode == 0
        assert result.stdout.strip() == "No events found."

    def test_no_events_found_not_printed_when_events_exist(self) -> None:
        assert "No events found." not in run_cli(FIXTURES / "basic.csv").stdout


# --------------------------------------------------------------------------
# Edge cases: missing service / level values
# --------------------------------------------------------------------------


class TestMissingValues:
    def test_missing_service_counted_as_unknown(self) -> None:
        assert summary(FIXTURES / "missing_service_value.csv") == {
            ("unknown", "INFO"): 2,
            ("cart-api", "INFO"): 1,
        }

    def test_missing_service_continues_processing(self) -> None:
        result = run_cli(FIXTURES / "missing_service_value.csv")
        assert result.returncode == 0
        assert any(s == "cart-api" for s, _, _ in parse_rows(result.stdout))

    def test_missing_level_counted_as_unknown(self) -> None:
        assert summary(FIXTURES / "missing_level_value.csv") == {
            ("cart-api", "unknown"): 2,
            ("cart-api", "INFO"): 1,
        }

    def test_missing_level_continues_processing(self) -> None:
        result = run_cli(FIXTURES / "missing_level_value.csv")
        assert result.returncode == 0
        assert any(lvl == "INFO" for _, lvl, _ in parse_rows(result.stdout))

    def test_missing_both_counted_as_unknown_unknown(self, tmp_path: Path) -> None:
        path = write_csv(tmp_path, HEADER + "t,,,m\nt,,,m\n")
        assert summary(path) == {("unknown", "unknown"): 2}

    def test_missing_values_are_not_treated_as_malformed(self) -> None:
        # Empty value is a well-formed row: no warning expected.
        result = run_cli(FIXTURES / "missing_service_value.csv")
        assert result.stderr == ""

    def test_missing_values_sum_matches_row_count(self) -> None:
        assert sum(summary(FIXTURES / "missing_service_value.csv").values()) == 3


# --------------------------------------------------------------------------
# Edge case: malformed / short rows
# --------------------------------------------------------------------------


class TestMalformedRows:
    def test_malformed_rows_are_skipped(self) -> None:
        assert summary(FIXTURES / "malformed_rows.csv") == {
            ("cart-api", "INFO"): 2,
            ("cart-api", "ERROR"): 1,
        }

    def test_malformed_rows_warn_on_stderr(self) -> None:
        result = run_cli(FIXTURES / "malformed_rows.csv")
        assert result.stderr.strip() != ""

    def test_one_warning_per_malformed_row(self) -> None:
        result = run_cli(FIXTURES / "malformed_rows.csv")
        warnings = [ln for ln in result.stderr.splitlines() if ln.strip()]
        assert len(warnings) >= 2  # two malformed rows in the fixture

    def test_malformed_rows_do_not_change_exit_code(self) -> None:
        assert run_cli(FIXTURES / "malformed_rows.csv").returncode == 0

    def test_warnings_do_not_pollute_stdout(self) -> None:
        result = run_cli(FIXTURES / "malformed_rows.csv")
        # Every stdout line must still be a valid summary row.
        rows = parse_rows(result.stdout)
        assert len(rows) == 2
        assert "warn" not in result.stdout.lower()

    def test_processing_continues_after_malformed_row(self) -> None:
        # The fixture has good rows both before and after the bad ones.
        counts = summary(FIXTURES / "malformed_rows.csv")
        assert counts[("cart-api", "INFO")] == 2

    def test_row_with_extra_columns_is_skipped(self) -> None:
        # Implementation note: mismatch in either direction is malformed.
        result = run_cli(FIXTURES / "extra_columns.csv")
        assert result.returncode == 0
        assert {(s, lvl): n for s, lvl, n in parse_rows(result.stdout)} == {
            ("cart-api", "INFO"): 2
        }
        assert result.stderr.strip() != ""

    def test_only_malformed_rows_prints_no_events_found(self, tmp_path: Path) -> None:
        # Implementation note: nothing counted -> "No events found.", exit 0.
        path = write_csv(tmp_path, HEADER + "short\nalso,short\n")
        result = run_cli(path)
        assert result.returncode == 0
        assert result.stdout.strip() == "No events found."
        assert result.stderr.strip() != ""

    def test_blank_lines_skipped_silently(self) -> None:
        # Implementation note: no warning, no count.
        result = run_cli(FIXTURES / "blank_lines.csv")
        assert result.returncode == 0
        assert result.stderr == ""
        assert parse_rows(result.stdout) == [("cart-api", "INFO", 2)]


# --------------------------------------------------------------------------
# Normalisation (implementation notes): whitespace, BOM
# --------------------------------------------------------------------------


class TestNormalisation:
    def test_surrounding_whitespace_is_stripped_before_grouping(self) -> None:
        counts = summary(FIXTURES / "whitespace.csv")
        assert counts[("checkout-service", "INFO")] == 3

    def test_whitespace_only_level_is_unknown(self) -> None:
        counts = summary(FIXTURES / "whitespace.csv")
        assert counts[("checkout-service", "unknown")] == 1

    def test_whitespace_only_service_is_unknown(self) -> None:
        counts = summary(FIXTURES / "whitespace.csv")
        assert counts[("unknown", "INFO")] == 1

    def test_whitespace_fixture_full_result(self) -> None:
        assert summary(FIXTURES / "whitespace.csv") == {
            ("checkout-service", "INFO"): 3,
            ("checkout-service", "unknown"): 1,
            ("unknown", "INFO"): 1,
        }

    def test_header_names_are_stripped(self, tmp_path: Path) -> None:
        path = write_csv(
            tmp_path,
            "timestamp, level , service ,message\nt,INFO,cart-api,m\n",
        )
        assert summary(path) == {("cart-api", "INFO"): 1}

    def test_utf8_bom_does_not_corrupt_first_header(self, tmp_path: Path) -> None:
        # Put a required column first so a BOM would break its name.
        path = tmp_path / "bom.csv"
        path.write_bytes(
            b"\xef\xbb\xbfservice,level,message\ncart-api,INFO,hello\n"
        )
        result = run_cli(path)
        assert result.returncode == 0, result.stderr
        assert parse_rows(result.stdout) == [("cart-api", "INFO", 1)]

    def test_case_is_not_normalised(self, tmp_path: Path) -> None:
        path = write_csv(
            tmp_path,
            HEADER + "t,INFO,Cart-API,m\nt,INFO,cart-api,m\n",
        )
        assert summary(path) == {
            ("Cart-API", "INFO"): 1,
            ("cart-api", "INFO"): 1,
        }


# --------------------------------------------------------------------------
# Edge case: required column missing from header
# --------------------------------------------------------------------------


class TestMissingRequiredColumn:
    @pytest.mark.parametrize(
        ("fixture", "column"),
        [
            ("missing_service_column.csv", "service"),
            ("missing_level_column.csv", "level"),
        ],
    )
    def test_exits_one(self, fixture: str, column: str) -> None:
        assert run_cli(FIXTURES / fixture).returncode == 1

    @pytest.mark.parametrize(
        ("fixture", "column"),
        [
            ("missing_service_column.csv", "service"),
            ("missing_level_column.csv", "level"),
        ],
    )
    def test_error_on_stderr_names_the_column(self, fixture: str, column: str) -> None:
        result = run_cli(FIXTURES / fixture)
        assert column in result.stderr.lower()

    @pytest.mark.parametrize(
        "fixture",
        ["missing_service_column.csv", "missing_level_column.csv"],
    )
    def test_nothing_on_stdout(self, fixture: str) -> None:
        assert run_cli(FIXTURES / fixture).stdout == ""

    def test_header_with_neither_required_column(self, tmp_path: Path) -> None:
        path = write_csv(tmp_path, "timestamp,message\nt,m\n")
        result = run_cli(path)
        assert result.returncode == 1
        assert result.stderr.strip() != ""

    def test_missing_column_with_header_only_file_still_errors(
        self, tmp_path: Path
    ) -> None:
        path = write_csv(tmp_path, "timestamp,message\n")
        assert run_cli(path).returncode == 1

    def test_error_is_not_a_traceback(self) -> None:
        result = run_cli(FIXTURES / "missing_service_column.csv")
        assert "Traceback" not in result.stderr


# --------------------------------------------------------------------------
# Edge case: file not found
# --------------------------------------------------------------------------


class TestFileNotFound:
    def test_exits_one(self, tmp_path: Path) -> None:
        assert run_cli(tmp_path / "nope.csv").returncode == 1

    def test_error_message_on_stderr(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.csv"
        result = run_cli(missing)
        assert result.stderr.strip() != ""
        assert "nope.csv" in result.stderr

    def test_nothing_on_stdout(self, tmp_path: Path) -> None:
        assert run_cli(tmp_path / "nope.csv").stdout == ""

    def test_error_is_not_a_traceback(self, tmp_path: Path) -> None:
        assert "Traceback" not in run_cli(tmp_path / "nope.csv").stderr

    def test_does_not_create_the_missing_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.csv"
        run_cli(missing)
        assert not missing.exists()


# --------------------------------------------------------------------------
# Edge case: unreadable file / I/O error
# --------------------------------------------------------------------------


class TestUnreadableFile:
    @pytest.mark.skipif(
        os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
        reason="permission bits are not enforced on Windows or for root",
    )
    def test_permission_denied_exits_one(self, tmp_path: Path) -> None:
        path = write_csv(tmp_path, HEADER + "t,INFO,cart-api,m\n")
        path.chmod(0o000)
        try:
            result = run_cli(path)
        finally:
            path.chmod(0o644)
        assert result.returncode == 1
        assert result.stderr.strip() != ""
        assert "Traceback" not in result.stderr
        assert result.stdout == ""

    def test_directory_as_input_exits_one(self, tmp_path: Path) -> None:
        result = run_cli(tmp_path)
        assert result.returncode == 1
        assert result.stderr.strip() != ""
        assert "Traceback" not in result.stderr
        assert result.stdout == ""


# --------------------------------------------------------------------------
# Implementation note: zero-byte file (no header at all)
# --------------------------------------------------------------------------


class TestZeroByteFile:
    def test_exits_one(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.csv"
        path.write_bytes(b"")
        assert run_cli(path).returncode == 1

    def test_reports_no_header_on_stderr(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.csv"
        path.write_bytes(b"")
        result = run_cli(path)
        assert "empty" in result.stderr.lower()
        assert result.stdout == ""

    def test_differs_from_header_only_case(self, tmp_path: Path) -> None:
        zero = tmp_path / "zero.csv"
        zero.write_bytes(b"")
        assert run_cli(zero).returncode != run_cli(FIXTURES / "header_only.csv").returncode
