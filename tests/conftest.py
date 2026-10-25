"""Redirect only the four frozen lifecycle tests to their pre-prepare reruns."""

from pathlib import Path

import pytest


FROZEN_LIFECYCLE_TESTS = {
    "test_retries_across_sessions_and_attempt_audit",
    "test_batches_stop_file_and_publication_gates",
    "test_plaintext_refusal_and_pipe_encryption",
    "test_seal_commit_one_file_and_reveal_ancestry",
}
REASON = (
    "frozen fixture needs a pre-prepare checkout; rerun from the "
    "preregistration state by tests/test_listener_rerun.py"
)


def pytest_collection_modifyitems(items):
    frozen_file = Path(__file__).with_name("test_listener.py").resolve()
    for item in items:
        if item.path.resolve() == frozen_file and item.name in FROZEN_LIFECYCLE_TESTS:
            item.add_marker(pytest.mark.skip(reason=REASON))
