# Independent re-analysis (EVAL mode)

This folder re-scores every published answer in the series without using the study's own code or stored scores, then recomputes the statistics with a separately tested library. It backs the "independent statistical review" numbers in the slides and in [REPORT.md](REPORT.md).

Everything here reads only published files on `main`. It makes no model calls and needs no passphrase or private files.

## What is in it

| File | What it does |
| --- | --- |
| [`series_eval.py`](series_eval.py) | Re-scores PRs #1 to #4 with its own exhaustive solver and recomputes their confirmatory tests, equivalence and non-inferiority checks, Holm correction, repeats split and the exploratory label-free audit |
| [`pr6_eval.py`](pr6_eval.py) | Re-scores PR #6 from `listener/codex/ledger.json` and `listener/qwen/ledger.json` with its own parser, then computes the primary and S1 to S5 tests, resolution (MDE), the series-wide Holm correction (m = 17), AUC, per-wording effects, the repeats split and the Qwen validity check |
| [`REPORT.md`](REPORT.md) | The written review of PR #6, with every number traced to the outputs below |
| [`series_eval_output.txt`](series_eval_output.txt), [`pr6_eval_output.txt`](pr6_eval_output.txt) | Expected output of each script, byte for byte |
| [`evalstats.py`](evalstats.py) | Statistics library from the EVAL toolkit, vendored unmodified. Every function is tagged with its published source |
| [`test_evalstats.py`](test_evalstats.py) | The library's own checks against simulations and published values. It is a script, not a pytest file |
| [`requirements.txt`](requirements.txt) | Pinned `numpy` and `scipy` |
| [`requirements-crosscheck.txt`](requirements-crosscheck.txt) | Optional: also pins `statsmodels`, `scikit-learn`, `MLstatkit` and `ppi-python`, so the library check can compare its results against them |

## Replay

From the repository root, with Python 3.12:

```
python3.12 -m venv .venv
.venv/bin/pip install -r analysis/independent_eval/requirements.txt
.venv/bin/python analysis/independent_eval/test_evalstats.py
.venv/bin/python analysis/independent_eval/series_eval.py 2>/dev/null | diff - analysis/independent_eval/series_eval_output.txt
.venv/bin/python analysis/independent_eval/pr6_eval.py 2>/dev/null | diff - analysis/independent_eval/pr6_eval_output.txt
```

The library check should end with `45 passed, 0 failed, 7 skipped`. The 7 skips are cross-checks against other statistics packages; install `requirements-crosscheck.txt` instead and it ends with `58 passed, 0 failed, 0 skipped`. Each `diff` should print nothing. Both scripts take a few seconds. The Monte Carlo sign-flip tests use a fixed seed, so the output is deterministic, and every number is rounded to its printed precision with no sign on zero, so the diff doesn't depend on last-digit floating-point differences between machines. `series_eval.py` writes two numpy `RuntimeWarning`s to stderr, from a correlation on a constant vector; they don't affect any number.

## How to read the numbers

- **Registered decisions** use the study's exact one-sided tests in each `RESULTS.md`. This review's sign-flip test is two-sided and, at n = 30, Monte Carlo with a floor of about 1 × 10⁻⁵, so its p-values are larger by design.
- **Exploratory, added in this review:** the series-wide Holm correction across all 17 confirmatory tests, the per-wording split, and the resolution (MDE) check. They add no decision to any study.
- **Series-wide correction inputs:** the 11 earlier raw p-values in `pr6_eval.py` are exactly the values `series_eval.py` prints; check them against `series_eval_output.txt`.
