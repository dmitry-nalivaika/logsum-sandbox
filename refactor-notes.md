## Removed by AI in the refactor

Scope: the proposed split of `count_events` in `src/logsum.py` into `_Columns`, `_read_columns`, `_valid_rows` and a short `count_events`. The diff was written up before it was applied and has since been applied to `src/logsum.py` exactly as shown (`git diff --stat`: 36 insertions, 17 deletions).

Method: every `-` line of the diff was listed and checked against the new source. The four areas flagged for scrutiny (width check, `or UNKNOWN` fallbacks, the three `except` branches in `main()`, blank-line skip) were also removed one at a time from the new code in memory, to confirm the old-vs-new comparison would notice each loss (results at the end).

"My decision" is left open on every entry. The recommendation is the AI's and is not a decision.

### Areas flagged for scrutiny: none of these was removed

- `len(row) != width` guard (malformed-row skip with stderr warning). **Not removed; moved verbatim** into `_valid_rows`. Only the `width = len(names)` local disappeared, and the same value now arrives as `columns.width = len(names)`. Same header-derived width, same message text, same `reader.line_num`. AI reason: the guard belongs with the other row filters.
  My decision: _open_. AI recommends: keep removed (nothing to restore).
- `... .strip() or UNKNOWN` fallbacks for `service` and `level`. **Not removed; moved verbatim** into the generator expression in `count_events`. The named locals `service` and `level` are gone, but the strip-then-fallback expression is character for character the same. AI reason: feeds `Counter(...)` directly.
  My decision: _open_. AI recommends: keep removed (nothing to restore).
- The three `except` branches in `main()` (`FileNotFoundError`, `(OSError, UnicodeDecodeError)`, `InputError`). **Not touched; `main()` is byte-identical** and does not appear in the diff. Branch order is unchanged, which matters because `FileNotFoundError` is a subclass of `OSError`.
  One thing to keep in mind: these branches only work because `count_events` still builds its result eagerly, inside the `with open(...)` block, and `Counter(...)` consumes the generator before returning. If a later edit made `count_events` return a lazy iterator, read errors would escape the `try` in `main()`.
  My decision: _open_. AI recommends: document (the eager-return requirement is now implicit).
- Blank-line skip (`if not row: continue`). **Not removed; moved verbatim** into `_valid_rows`, before the width check. The order matters: without the skip, a blank line reaches the width check and produces a spurious `expected 4 columns, got 0` warning.
  My decision: _open_. AI recommends: keep removed (nothing to restore).

### Lines that are removed

- `service_idx = names.index("service")`, `level_idx = names.index("level")`, `width = len(names)`. AI reason: the three values are returned together as a `_Columns` tuple from `_read_columns`, so the row loop can live in another function. `names.index` still returns the first match when a column name is duplicated, as before.
  My decision: _open_. AI recommends: keep removed.
- `counts: Counter[tuple[str, str]] = Counter()`, `counts[(service, level)] += 1`, `return counts`. AI reason: replaced by `return Counter(<generator>)`. The result is built eagerly and inserted in the same first-seen order. The explicit annotation is dropped, and the type should be inferred from the generator's `tuple[str, str]` items (not checked with a type checker).
  My decision: _open_. AI recommends: keep removed.
- `break` on `StopIteration`. AI reason: inside a generator the equivalent is `return`. The `except StopIteration` is kept, so PEP 479 does not turn it into a `RuntimeError`.
  My decision: _open_. AI recommends: keep removed.
- Imports `Iterable, Sequence` and `TextIO`, replaced by supersets that add `Iterator`, `Any` and `NamedTuple`. Nothing is dropped.
  My decision: _open_. AI recommends: keep removed.
- **Type precision on `reader` (a real loss).** Before, `reader = csv.reader(lines)` was inferred as the csv reader type. The helpers now take `reader: Any`. AI reason: the precise type is the private `_csv._reader`, and the AI did not want to import a private name. A small `Protocol` with `__next__` and `line_num` would restore precision at the cost of more code.
  My decision: _open_. AI recommends: document now, restore via a `Protocol` if type checking is added later.

### What was and was not verified

- Old and new `count_events` and `format_summary` were compared in memory on 20,000 random inputs plus edge cases, covering counts, formatted output, stderr text and exceptions. No differences.
- Guard-removal check (3,000 inputs plus five targeted cases): removing the width check, either `or UNKNOWN` fallback, or the blank-line skip from the new code each produced many differences (1,828 / 1,029 / 1,014 / 1,066 of 3,000). So the comparison would have noticed if the refactor had dropped any of them.
- **After applying** (local, Python 3.14 in `.venv`): `ruff check .` passed, 72 tests passed, and the applied file matched the committed version on 10,000 further random inputs with 0 differences. The CLI printed the same six summary rows for `data/sample_events.csv` (exit 0) and still exited 1 with an error for a missing file.
- **Not verified:**
  - Python 3.11 (what CI uses) and any type checker (`mypy` and `pyright` are not installed).
  - A `UnicodeDecodeError` partway through a real file was not exercised. The in-memory inputs are `StringIO` and cannot raise it. The exception still propagates out of the generator and `Counter(...)` to the same `except` in `main()`, but that is reasoning, not a test.
  - Only these four guards were mutation-checked.
