## What both produced

Comparison basis: the original run on `min-count-flag` (supervised, per the `*-notes.md` files) against the replay on `replay/logsum`. The repo holds no hand-written build, so "by hand" here means the original supervised run. Replace this with your own by-hand attempt if you made one.

- Same behaviour from the same `spec.md`: the original 100 tests pass against the replay code, and the replay's 106 tests pass against the original code.
- `src/logsum.py` is identical in executable code. Only comments and docstrings differ.
- Same refactor (`count_events` split into `_read_columns` and `_valid_rows`), same `ci.yml`, a provenance note, and `ruff` clean.

## Where the agent saved time

- Writing 106 black-box tests and 11 fixtures from the spec in one delegated pass.
- Mechanical verification that would be tedious by hand: a 20,000-input differential check of the refactor, and 14 mutants run against the suite.
- Keeping `provenance-notes.md` and the evidence behind it in step with the work.

## Where the agent went wrong or shorter

- 14 of the 106 tests passed with no implementation (Python's own exit 2 for a missing script matched the `--min-count` checks). They were vacuous until they were tightened.
- One test had its columns in the wrong order and only failed once the code ran.
- The new code is not an independent derivation: the agent had read the old code and tests while planning. Only the subagent's tests are independent.
- No lazy-iterator mutant was run, `ci.yml` was not parsed mechanically, and CI was not run on Python 3.11.
- One mutant survived: removing the `FileNotFoundError` branch. The spec does not pin the error wording, so the suite does not either.

## What the agent did better

- The cross-run of old tests against new code, and new tests against old code, was cheap and gave real evidence of equivalence.
- Systematic coverage of every acceptance criterion, edge case and implementation note, including the unreadable-file, invalid-UTF-8 and bad `--min-count` cases.
- Honest bookkeeping: what was verified, what was not, and who wrote each artifact.

## What I learned about supervised vs async

- A subagent with only `spec.md` gave independence that a single session cannot, but it needed a prompt that spelled out exactly which files it could read.
- Delegated test writing needs a red-run check. Without it, the 14 vacuous tests would have looked like passing coverage.
- The human gates mattered: the approval to write outside `src/` and `tests/`, and the choice of branch, scope and refactor, kept the replay inside what the project allows.

## What I would do differently next time

- Write the implementation in a session that has not seen the old code, or hand it to a second subagent, so both sides are independent.
- Add a "no implementation present" red run to the test-writing step, and require every test to fail for the right reason.
- Run CI on the real workflow (Python 3.11) before calling the replay done, and add a YAML parse step.
- Decide the zero-byte-file rule with the spec owner instead of carrying it as an implementation note.
