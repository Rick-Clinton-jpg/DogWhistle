# Test maintenance — 2026-10-25

Four fixture-based tests in `tests/test_listener.py` could not run on any committed version, including preregistration commit `3a6ed85`: their fixture calls `prepare` after `listener/registration.json` is present. They had passed only in the working copy before prepare. The “post-publication” description in `RESULTS.md` is corrected by this note.

`tests/test_listener_rerun.py` runs the unchanged tests from the pre-prepare parent of `3a6ed85`. `tests/conftest.py` skips only their original collection entries. No frozen file, sealed record, score, or result changed.
