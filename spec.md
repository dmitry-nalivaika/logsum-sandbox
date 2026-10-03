# Spec: logsum — summarize log events by service and level

Requirement
The `logsum` CLI shall read a CSV file containing log events and produce a summary showing how many events occurred for each unique combination of `service` and `level`. This allows engineers to quickly identify which services are generating the most activity at different log severities.

## Acceptance Criteria

1. The CLI accepts a CSV file path as a required positional argument.
2. The CSV input must contain `service` and `level` columns.
3. For a valid input file, the tool prints one output row for every unique `(service, level)` combination present in the data.
4. Each output row includes the service name, the level name, and the corresponding event count.
5. Counts reflect the number of data rows matching that exact `(service, level)` combination.
6. Output rows are sorted alphabetically by `service`, then alphabetically by `level`.
7. When processing completes successfully, the program exits with status code `0`.
8. The tool writes the summary to standard output.
9. The tool does not modify the input file.


## Edge Cases

* Empty file (header present, no data rows)
Print `No events found.` to standard output and exit with status code `0`.
* Missing `service` value in a row
Count the row under service name `unknown` and continue processing.
* Missing `level` value in a row
Count the row under level name `unknown` and continue processing.
* Row has fewer columns than expected or cannot be parsed correctly
Skip the malformed row, print a warning to standard error, and continue processing remaining rows.
* Required column (`service` or `level`) is missing from the header
Print a clear error message to standard error and exit with status code `1`.
* Input file does not exist
Print a clear error message to standard error and exit with status code `1`.
* Input file is unreadable (permissions or I/O error)
Print a clear error message to standard error and exit with status code `1`.


## Out of Scope

* Filtering by date, timestamp, service, or log level.
* Custom sorting options.
* Support for output formats other than plain text.
* Reading from standard input.
* Real-time or streaming log processing.
* Aggregations beyond counts grouped by `service` and `level`.
* Validation of allowed log levels (all non-empty level values are counted as provided).


## Implementation notes

Decisions made in `src/logsum.py` to fill gaps this spec leaves open. None of them contradict the spec text.

* Zero-byte file (no header row at all)
The spec covers only "header present, no data rows". A file with no header is treated as an input error: print `file is empty: no header row` to standard error and exit with status code `1`.
* Rows with more columns than the header
The spec says "fewer columns than expected". Any mismatch with the header width, fewer or more, is treated as malformed: the row is skipped, a warning goes to standard error, and processing continues.
* Whitespace in values
`service` and `level` values are stripped of leading and trailing whitespace before counting, so `" checkout-service "` and `"checkout-service"` share one bucket. Header names are stripped the same way.
* Whitespace-only values
A value that is empty after stripping counts as missing and is reported as `unknown`.
* Output layout
Each output row is `service`, `level`, `count`, separated by two spaces, with the service and level columns padded to the widest value. The spec requires the three fields but no layout.
* Blank lines
Blank lines in the data are skipped silently, with no warning and no count.
* Byte order mark
The file is read as `utf-8-sig`, so a leading BOM is removed and does not corrupt the first header name.
* Only malformed rows
If every data row is skipped as malformed, nothing is counted, so the tool prints `No events found.` and exits with status code `0`. Warnings for the skipped rows still go to standard error.
* A zero-byte input file (no header row at all) is treated as an error (exit 1),
  distinct from the spec's "header present, no data rows" case (which exits 0
  with "No events found."). The spec didn't name this case explicitly; this is
  the decision made during implementation.
* Rows with *more* columns than the header, not just fewer, are also treated as
  malformed and skipped with a warning — the spec only named "fewer columns"
  explicitly, this extends the same handling symmetrically.
* `service` and `level` values are trimmed of surrounding whitespace before
  being counted or compared against "unknown" / the header names. Not specified
  either way; chosen for robustness against trailing spaces in CSV exports.