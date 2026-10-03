# Repo questions

Branch at time of writing: `min-count-flag` (HEAD `8982b71`).

## 1. Where is the grouping rule?

**Files read:** `src/logsum.py`, `spec.md`, `tests/test_logsum.py`, `CLAUDE.md`

**Answer.** The rule is in `count_events` in `src/logsum.py`. Each data row becomes a key made of its service and its level. A `Counter` counts how many rows share each key. So every distinct (service, level) pair gets one count. Both values are trimmed of surrounding whitespace first. An empty value becomes `unknown`.

- The key is `(row[service].strip() or UNKNOWN, row[level].strip() or UNKNOWN)`, fed straight into `Counter(...)`: `src/logsum.py:91-97`.
- The two column positions come from the header. `service` and `level` are the required columns (`src/logsum.py:11`). Their positions are found by name, so column order does not matter (`src/logsum.py:38-43`; test at `tests/test_logsum.py:178-183`).
- Only rows of the right width are counted. Blank lines and wrong-width rows are dropped first (`src/logsum.py:65-74`).
- The match is exact and case-sensitive: `INFO` and `info` are separate groups (`tests/test_logsum.py:162-171`). Case is not normalised (`tests/test_logsum.py:459-467`).
- Output is sorted by service, then level, in `format_summary`: `src/logsum.py:104`. This is spec criterion 6 (`spec.md:13`).
- `--min-count` is applied after grouping. It only drops groups whose count is below N, and it does not change the counts: `src/logsum.py:113-117`, `src/logsum.py:162`. The spec says the same (`spec.md:17`).
- The spec states the intent: "one output row for every unique `(service, level)` combination" (`spec.md:10`), and counts reflect the "exact `(service, level)` combination" (`spec.md:12`).
- The trimming is an implementation decision, not in the original spec text: `spec.md:63-66`.

**Could not verify:** nothing material. I confirmed the behaviour by running the test suite (see question 3), not just by reading the code.

## 2. How is a missing level handled?

**Files read:** `src/logsum.py`, `spec.md`, `tests/test_logsum.py`, `tests/fixtures/missing_level_value.csv`, `tests/fixtures/missing_level_column.csv`

**Answer.** It depends on what "missing" means.

**a) The level cell is empty or only spaces.**
- The row is counted under the level name `unknown`, and processing continues. The `or UNKNOWN` fallback at `src/logsum.py:94` does this, using the constant `UNKNOWN = "unknown"` (`src/logsum.py:10`).
- Whitespace-only counts as empty because the value is stripped first (`src/logsum.py:94`; `spec.md:65-66`).
- No warning is printed. An empty value is a well-formed row. The only test of this (`tests/test_logsum.py:347-350`) uses `missing_service_value.csv`, so it covers an empty service. No test checks stderr for an empty level; for level this rests on the code (`src/logsum.py:67-73` only warns on width mismatch).
- Spec: `spec.md:26-27`.
- Fixture: two rows with an empty level and one `INFO` (`tests/fixtures/missing_level_value.csv:2-4`). The expected result is `("cart-api","unknown"): 2` and `("cart-api","INFO"): 1` (`tests/test_logsum.py:332-336`).
- If both service and level are empty, the row is counted as `unknown / unknown` (`tests/test_logsum.py:343-345`).
- `--min-count` treats `unknown` groups like any other (`tests/test_logsum.py:698-703`).

**b) The `level` column is absent from the header.**
- This is an error. `_read_columns` raises `InputError("missing required column(s): ...")` (`src/logsum.py:39-41`).
- `main()` prints `error: <path>: ...` to stderr and returns exit status 1 (`src/logsum.py:158-160`). Nothing goes to stdout (`tests/test_logsum.py:497-502`).
- Spec: `spec.md:30-31`.
- Fixture: `tests/fixtures/missing_level_column.csv:1` has no `level` header.

**c) The row is too short, so the level field does not exist.**
- This is not treated as "missing level". The row has the wrong width, so it is skipped with a warning on stderr and is not counted (`src/logsum.py:67-73`).
- Spec: `spec.md:28-29`.
- Tests: skipped and not counted at `tests/test_logsum.py:362-366`; warning on stderr at `tests/test_logsum.py:368-370`.

**Could not verify:** nothing material.

## 3. How do I run tests and CI locally?

**Files read:** `.github/workflows/ci.yml`, `ci-notes.md`, `test-notes.md`, `refactor-notes.md`, `tests/test_logsum.py`, `.gitignore`, `CLAUDE.md`. I also listed the tracked files with `git ls-files` and looked for config files.

**Answer.**

Tests and lint can be run locally. CI as a GitHub Actions run cannot be reproduced locally with anything in this repo.

What CI does (one job, `test`, on `ubuntu-latest`, Python 3.11, on every push and pull request):
1. `python -m pip install ruff pytest` (`.github/workflows/ci.yml:20-21`)
2. `ruff check .` (`.github/workflows/ci.yml:23-24`)
3. `pytest -v` (`.github/workflows/ci.yml:26-27`)
4. Triggers: `.github/workflows/ci.yml:3-5`. Python version: `.github/workflows/ci.yml:16-18`. Runner: `.github/workflows/ci.yml:12`.

To reproduce it locally, run the same two commands from the repo root:

```
source .venv/bin/activate     # .venv is git-ignored (.gitignore:1); ruff and pytest are already in it
ruff check .
pytest -v
```

- The tests run the CLI as a subprocess, `python src/logsum.py <csv>` (`tests/test_logsum.py:9-10`, `tests/test_logsum.py:34-41`). They need no network and no extra setup. The paths are built from the test file's location (`tests/test_logsum.py:22-24`).
- If `pytest` is not found outside the venv, that is a PATH problem, not a test failure (`test-notes.md:5`).
- `CLAUDE.md` says not to install packages without asking. Use the existing `.venv` rather than installing anything new.

**What I ran** (using `.venv/bin/python -m ...`, Python 3.14.6):
- `ruff check .` printed "All checks passed!".
- `pytest -q` gave 100 passed in 4.76s.
- `pytest --collect-only -q` showed 100 tests collected.

**Could not verify / caveats:**
- **Workflow itself not run locally.** I did not run the `ci.yml` workflow. `act` is not installed, and the repo documents no way to run it. The commands above are the same steps, not the workflow.
- **Python version differs from CI.** Local is 3.14.6, CI is 3.11. I did not run on 3.11. `ci-notes.md:66` says the same.
- **Tool versions not checked.** CI installs unpinned `ruff` and `pytest` (`.github/workflows/ci.yml:21`). I did not compare them with the `.venv` versions.
- **No config files found.** I looked for `pyproject.toml`, `ruff.toml`, `.ruff.toml`, `pytest.ini`, `tox.ini`, `setup.cfg`, `conftest.py`, `Makefile` and `requirements.txt`. None exist (`ls`). Both tools therefore run on defaults, in CI and locally.
- **No README.** The tracked file list (`git ls-files`) has no README, so there is no documented run procedure beyond `ci.yml`.
- **Test counts in the notes are out of date.**
  - `test-notes.md:17` says 78 tests, and `refactor-notes.md:42` says 78. The current count is 100.
  - The extra tests are presumably the `--min-count` classes (`tests/test_logsum.py:638-780`), added in commits `2e23e56` and `8982b71`. I did not count them to confirm the arithmetic.
- **CI results after the `--min-count` commits not checked.** `ci-notes.md` records runs only up to the earlier commits (`ci-notes.md:67`). I did not query GitHub (that needs the network, which `CLAUDE.md` forbids).
- **`main` and the workflow not checked.** `ci-notes.md:65` says `main` has no workflow yet. The git log shows PR #1 merged (`633f24c`). I did not check whether `main` now contains `ci.yml`, so that note may be stale.

## Verification

Every file-line citation above was opened and compared with the claim it supports. Verdicts: **correct**, **off-by-N**, **wrong rule**, **unverifiable**. Checked on branch `min-count-flag`, HEAD `8982b71`.

**Summary:** 50 citations checked. 48 correct, 1 off-by-N, 1 wrong rule, 0 unverifiable. The first pass marked all 50 correct; a second pass opening the test bodies found the two below. Both are fixed in the answers above.

### Question 1

| Citation | Verdict | Note |
| --- | --- | --- |
| `src/logsum.py:91-97` | correct | `Counter(...)` over stripped `service`/`level` with `or UNKNOWN` |
| `src/logsum.py:11` | correct | `REQUIRED_COLUMNS` |
| `src/logsum.py:38-43` | correct | header names stripped, `.index()` by name |
| `tests/test_logsum.py:178-183` | correct | `test_column_order_in_header_does_not_matter` |
| `src/logsum.py:65-74` | correct | blank-line skip and width check |
| `tests/test_logsum.py:162-171` | correct | `INFO` vs `info` |
| `tests/test_logsum.py:459-467` | correct | `Cart-API` vs `cart-api` |
| `src/logsum.py:104` | correct | `sorted(counts.items())` |
| `spec.md:13` | correct | criterion 6 |
| `src/logsum.py:113-117` | correct | `filter_counts` |
| `src/logsum.py:162` | correct | `filter_counts(counts, min_count)` after `count_events` |
| `spec.md:17` | correct | criterion 10 |
| `spec.md:10` | correct | "one output row for every unique `(service, level)` combination" |
| `spec.md:12` | correct | "exact `(service, level)` combination" |
| `spec.md:63-66` | correct | whitespace bullets under Implementation notes |

### Question 2

| Citation | Verdict | Note |
| --- | --- | --- |
| `src/logsum.py:94` | correct | `or UNKNOWN` on the level value |
| `src/logsum.py:10` | correct | `UNKNOWN = "unknown"` |
| `spec.md:65-66` | correct | whitespace-only value reported as `unknown` |
| `tests/test_logsum.py:347-350` | wrong rule | the test runs `missing_service_value.csv`, so it shows no warning for an empty service, not an empty level. Claim reworded |
| `spec.md:26-27` | correct | missing `level` value |
| `tests/fixtures/missing_level_value.csv:2-4` | correct | two empty levels, one `INFO` |
| `tests/test_logsum.py:332-336` | correct | expected `unknown: 2`, `INFO: 1` |
| `tests/test_logsum.py:343-345` | correct | `unknown / unknown: 2` |
| `tests/test_logsum.py:698-703` | correct | `unknown` filtered like any other group |
| `src/logsum.py:39-41` | correct | `missing` check and `InputError` |
| `src/logsum.py:158-160` | correct | `except InputError`, prints `error: <path>: ...`, returns 1 |
| `tests/test_logsum.py:497-502` | correct | `test_nothing_on_stdout` |
| `spec.md:30-31` | correct | missing required column |
| `tests/fixtures/missing_level_column.csv:1` | correct | header is `timestamp,service,message` |
| `src/logsum.py:67-73` | correct | width mismatch warns and skips |
| `spec.md:28-29` | correct | fewer columns / unparseable |
| `tests/test_logsum.py:362-366` | off-by-N | asserts counts only (`malformed_rows.csv` gives INFO 2, ERROR 1). The stderr warning is asserted in a separate test at `:368-370` (`stderr.strip() != ""`). Claim now cites both ranges |

### Question 3

| Citation | Verdict | Note |
| --- | --- | --- |
| `.github/workflows/ci.yml:20-21` | correct | install `ruff pytest` |
| `.github/workflows/ci.yml:23-24` | correct | `ruff check .` |
| `.github/workflows/ci.yml:26-27` | correct | `pytest -v` |
| `.github/workflows/ci.yml:3-5` | correct | `push` and `pull_request` triggers |
| `.github/workflows/ci.yml:16-18` | correct | Python `3.11` |
| `.github/workflows/ci.yml:12` | correct | `ubuntu-latest` |
| `.github/workflows/ci.yml:21` | correct | unpinned install |
| `.gitignore:1` | correct | `.venv/` |
| `tests/test_logsum.py:9-10` | correct | docstring: subprocess `python src/logsum.py <csv>` |
| `tests/test_logsum.py:34-41` | correct | `run_cli` |
| `tests/test_logsum.py:22-24` | correct | `ROOT`, `SCRIPT`, `FIXTURES` from `__file__` |
| `test-notes.md:5` | correct | exit 127 was `pytest` not on PATH |
| `test-notes.md:17` | correct | "78 tests" |
| `refactor-notes.md:42` | correct | "78 passing tests" |
| `tests/test_logsum.py:638-780` | correct | AC10 section to end of file (780 lines) |
| `ci-notes.md:66` | correct | green runs on 3.11; local used a different Python |
| `ci-notes.md:67` | correct | later runs not recorded |
| `ci-notes.md:65` | correct | "`main` has no workflow yet" |

### Other checks

- Header: branch `min-count-flag` and HEAD `8982b71` match `git`.
- `pytest --collect-only -q` reports 100 tests, matching the answer.
- Commit `2e23e56` is the one that added `TestMinCount`; `8982b71` was not checked for test additions, so "added in `2e23e56` and `8982b71`" is only partly confirmed.
- Not re-run in this pass: `ruff check .` result, the 100-pass count and timing, and the Python 3.14.6 version string. These are run results, not file-line citations.
- Bare file references without line numbers (e.g. `CLAUDE.md`, `.github/workflows/ci.yml` as a whole) were not counted.
