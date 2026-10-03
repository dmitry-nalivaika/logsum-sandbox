## Removed by AI in the refactor

Scope: the proposed split of `count_events` in `src/logsum.py` into `_Columns`, `_read_columns`, `_valid_rows` and a short `count_events`. The diff was written up before it was applied and has since been applied to `src/logsum.py` exactly as shown (`git diff --stat`: 36 insertions, 17 deletions).

Method: every `-` line of the diff was listed and checked against the new source. The four areas flagged for scrutiny (width check, `or UNKNOWN` fallbacks, the three `except` branches in `main()`, blank-line skip) were also removed one at a time from the new code in memory, to confirm the old-vs-new comparison would notice each loss (results at the end).

Decisions: all nine were recorded in one step on the instruction "accept all after review each line", each as "accepted from AI recommendation". That means the AI's recommendation was adopted as given. It is not nine separate judgments, and it does not mean each entry was weighed individually.

### Areas flagged for scrutiny: none of these was removed

- `len(row) != width` guard (malformed-row skip with stderr warning). **Not removed; moved verbatim** into `_valid_rows`. Only the `width = len(names)` local disappeared, and the same value now arrives as `columns.width = len(names)`. Same header-derived width, same message text, same `reader.line_num`. AI reason: the guard belongs with the other row filters.
  My decision: accepted from AI recommendation (keep removed; nothing to restore).
- `... .strip() or UNKNOWN` fallbacks for `service` and `level`. **Not removed; moved verbatim** into the generator expression in `count_events`. The named locals `service` and `level` are gone, but the strip-then-fallback expression is character for character the same. AI reason: feeds `Counter(...)` directly.
  My decision: accepted from AI recommendation (keep removed; nothing to restore).
- The three `except` branches in `main()` (`FileNotFoundError`, `(OSError, UnicodeDecodeError)`, `InputError`). **Not touched; `main()` is byte-identical** and does not appear in the diff. Branch order is unchanged, which matters because `FileNotFoundError` is a subclass of `OSError`.
  One thing to keep in mind: these branches only work because `count_events` still builds its result eagerly, inside the `with open(...)` block, and `Counter(...)` consumes the generator before returning. If a later edit made `count_events` return a lazy iterator, read errors would escape the `try` in `main()`.
  Update: this is now written into the `count_events` docstring and exercised by `TestInvalidUtf8` (bad byte early, late and in the header; exit 1, no traceback). A throwaway mutant that returned a lazy iterator made 46 tests fail across the whole suite. Run against only the 6 `TestInvalidUtf8` tests, that mutant failed exactly one: `test_exits_one_with_clean_error[late]`. The `early` and `in_header` cases still passed, because for a short file the decode error occurs before the file closes (the header is read eagerly in `_read_columns`, and the first buffered read already contains the bad byte). So within `TestInvalidUtf8`, only the `late` case detects a lazy return; the three `test_prints_no_partial_summary` cases pass either way, since stdout is empty whether the program fails cleanly or crashes. The 46 failures across the full suite come mostly from the mutant also breaking valid inputs (the file is closed by the time the iterator is consumed), not from the decode-error path. A lazy variant that keeps the file open would fail far fewer tests, and `late` would matter more there; that variant has not been run.
  My decision: accepted from AI recommendation (document; done in the docstring, and the `late` test backs it). A more prominent location than the docstring was offered and not requested.
- Blank-line skip (`if not row: continue`). **Not removed; moved verbatim** into `_valid_rows`, before the width check. The order matters: without the skip, a blank line reaches the width check and produces a spurious `expected 4 columns, got 0` warning.
  My decision: accepted from AI recommendation (keep removed; nothing to restore).

### Lines that are removed

- `service_idx = names.index("service")`, `level_idx = names.index("level")`, `width = len(names)`. AI reason: the three values are returned together as a `_Columns` tuple from `_read_columns`, so the row loop can live in another function. `names.index` still returns the first match when a column name is duplicated, as before.
  My decision: accepted from AI recommendation (keep removed).
- `counts: Counter[tuple[str, str]] = Counter()`, `counts[(service, level)] += 1`, `return counts`. AI reason: replaced by `return Counter(<generator>)`. The result is built eagerly and inserted in the same first-seen order. The explicit annotation is dropped, and the type should be inferred from the generator's `tuple[str, str]` items (not checked with a type checker).
  My decision: accepted from AI recommendation (keep removed).
- `break` on `StopIteration`. AI reason: inside a generator the equivalent is `return`. The `except StopIteration` is kept, so PEP 479 does not turn it into a `RuntimeError`.
  My decision: accepted from AI recommendation (keep removed).
- Imports `Iterable, Sequence` and `TextIO`, replaced by supersets that add `Iterator`, `Any` and `NamedTuple`. Nothing is dropped.
  My decision: accepted from AI recommendation (keep removed).
- **Type precision on `reader` (a real loss).** Before, `reader = csv.reader(lines)` was inferred as the csv reader type. The helpers now take `reader: Any`. AI reason: the precise type is the private `_csv._reader`, and the AI did not want to import a private name. A small `Protocol` with `__next__` and `line_num` would restore precision at the cost of more code.
  My decision: accepted from AI recommendation (document now; restore via a `Protocol` if type checking is added later). The loss stays in place, and nothing checks it today.

### What was and was not verified

- Old and new `count_events` and `format_summary` were compared in memory on 20,000 random inputs plus edge cases, covering counts, formatted output, stderr text and exceptions. No differences.
- Guard-removal check (3,000 inputs plus five targeted cases): removing the width check, either `or UNKNOWN` fallback, or the blank-line skip from the new code each produced many differences (1,828 / 1,029 / 1,014 / 1,066 of 3,000). So the comparison would have noticed if the refactor had dropped any of them.
- **After applying** (local, Python 3.14 in `.venv`): `ruff check .` passed, 72 tests passed, and the applied file matched the committed version on 10,000 further random inputs with 0 differences. The CLI printed the same six summary rows for `data/sample_events.csv` (exit 0) and still exited 1 with an error for a missing file.
- **Verified since the first write-up:**
  - Python 3.11 (CI): the refactor commit `edd2926` passed on both the push and pull_request runs, each executing **72 tests**. That commit predates `TestInvalidUtf8`, so those runs do not cover the new tests. The first CI runs that execute all **78 tests** are on `e942808`, and `bb6c9dc` (which includes the docstring change) also passed with 78. `cad9367` and `acb5564` were pushed together with later commits, so neither has a CI run of its own.
  - `ruff check .` and 78 passing tests, run locally on the current HEAD `bb6c9dc`, after the docstring edit.
  - `UnicodeDecodeError` partway through a real file: run through the actual CLI on three files with a bad byte (row 2, after about 38 KB and 1,000 valid rows, and inside a header name). All exited 1 with a clean error message and nothing on stdout, identical to the pre-refactor version. Now covered by `TestInvalidUtf8`.
  - The lazy-iterator mutant, run against only the 6 `TestInvalidUtf8` tests, fails the `late` case and nothing else. So `TestInvalidUtf8` does catch that regression, through one of its six cases.
- **Not verified:**
  - Any type checker (`mypy` and `pyright` are not installed). The "type inferred from the generator" claim and the `reader: Any` loss are unchecked. Installing one is gated by `CLAUDE.md` and has not been done.
  - Only these four guards were mutation-checked.
  - The lazy mutant used here consumes the iterator right after the `with` block closes. Other lazy variants were not tried.
