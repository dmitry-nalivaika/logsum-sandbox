# CI notes

## Workflow

`.github/workflows/ci.yml`, triggered on `push` and `pull_request`. One job, `test`, on `ubuntu-latest` with Python 3.11:

1. Install `ruff` and `pytest`
2. `ruff check .`
3. `pytest -v`

## Result on PR #1 (`add-tests` into `main`)

Checked with `gh pr checks 1` after pushing the workflow commit (7f6ad1e). Two `test` runs, both passed in 10s:

- https://github.com/dmitry-nalivaika/logsum-sandbox/actions/runs/37137874964
- https://github.com/dmitry-nalivaika/logsum-sandbox/actions/runs/37137875604

The workflow triggers on both `push` and `pull_request`, which accounts for the two runs. I did not confirm which run is which.

## Red run (deliberate failure)

Commit `b879d8b` ("TEMP: reverse sort order to demonstrate CI failure") changed `sorted(counts.items())` to `sorted(counts.items(), reverse=True)` in `format_summary`. Local result before pushing: 4 failed, 68 passed; `ruff check .` still passed.

Both CI runs on that commit failed (checked with `gh run view`):

| Run | Event | Lint | Test |
| --- | --- | --- | --- |
| [37138142811](https://github.com/dmitry-nalivaika/logsum-sandbox/actions/runs/37138142811) | push | success | failure |
| [37138145450](https://github.com/dmitry-nalivaika/logsum-sandbox/actions/runs/37138145450) | pull_request | success | failure |

Failing tests (4 failed, 68 passed, same as local), all in `TestSorting`:

- `test_sorted_by_service_then_level`
- `test_output_order_is_independent_of_input_order`
- `test_service_takes_priority_over_level`
- `test_unknown_sorts_alphabetically_with_others`

The other 68 tests passed, so CI caught the bug through the sort tests, not through lint. The commit was reverted afterwards (see below).

## Green run after the revert

Commit `ad761e7` (`git revert` of `b879d8b`) restores `sorted(counts.items())`. Before pushing, locally: `ruff check .` clean, 72 passed. Pushed to `add-tests` as a normal fast-forward (`b879d8b..ad761e7`), with no force push and no history rewrite. The `TEMP` commit stays in the branch history, followed by its revert.

Both CI runs on `ad761e7` passed (checked with `gh run view`). Every step, including Lint and Test, succeeded:

| Run | Event | Lint | Test |
| --- | --- | --- | --- |
| [37138294445](https://github.com/dmitry-nalivaika/logsum-sandbox/actions/runs/37138294445) | push | success | success |
| [37138297059](https://github.com/dmitry-nalivaika/logsum-sandbox/actions/runs/37138297059) | pull_request | success | success |

`gh pr checks 1` reported both `test` jobs as `pass` (10s and 8s).

Timeline on PR #1:

| Commit | Change | CI |
| --- | --- | --- |
| `7f6ad1e` | Add CI workflow | green |
| `b879d8b` | TEMP: reverse sort order | red (4 sort tests) |
| `ad761e7` | Revert of `b879d8b` | green |

The red-then-green sequence shows the sort tests detect the regression and the suite recovers once it is reverted.

## Caveats

- `main` has no workflow yet. CI will only run there after PR #1 is merged.
- The green runs (on 7f6ad1e and on ad761e7) show the tests also pass on Python 3.11. Local runs used a different Python.
- `ci-notes.md` was committed to `add-tests` after the revert runs above. It does not record the later runs on the refactor commit `edd2926` (both passed) or on the invalid-UTF-8 tests commit.
- CI checks the code, not test isolation. See `test-notes.md`.
