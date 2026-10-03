# Test notes

## Result

`python -m pytest -v` (in `.venv`, 2026-10-03): 72 passed, 0 failed. There were no failures to classify as implementation bug, test bug, or spec ambiguity. (An earlier `pytest -v` exit 127 was `pytest` not on PATH outside the venv, not a test failure.)

## Isolation: not confirmed

`tests/test_logsum.py` claims to be "written from spec.md only", and it does test only the CLI as a subprocess (argv, stdout, stderr, exit code). The workspace does not show that the test author never saw `src/logsum.py`:

- No record of a subagent, fresh session, or restricted file access was found.
- File timestamps: `src/logsum.py` 18:14, `spec.md` last modified 18:21, `tests/test_logsum.py` 18:25. The code existed before the tests were written.
- The "Implementation notes" in `spec.md` were added after the code and describe its behaviour. Tests derived from them are not independent of the implementation.

Treat the suite as spec-plus-implementation-notes tests, not as an independent check of the code.

Update: the file header no longer claims "written from spec.md only". It now says most tests derive from the spec and its "Implementation notes", and that `TestInvalidUtf8` (added later) was written from knowledge of the implementation. That class is not independent spec coverage. The suite now has 78 tests (72 originally, plus 6 in `TestInvalidUtf8`).

## Decision: zero-byte file is a spec ambiguity

The spec covers only "header present, no data rows" (print `No events found.`, exit 0). A zero-byte file (no header) is not named. Classified as a genuine spec ambiguity, not an implementation or test bug.

The implementation exits 1 with `file is empty: no header row`, and `TestZeroByteFile` pins that behaviour. Those tests only confirm the code matches its own implementation note. They do not show it is the right behaviour. The spec owner should decide, then move the rule from "Implementation notes" into "Edge Cases".
