"""Run the four frozen lifecycle tests from a checkout before prepare."""

from pathlib import Path
import subprocess

import pytest

from dogwhistle import listener, study
from test_listener import (
    fake_receiver,
    git,
    test_batches_stop_file_and_publication_gates,
    test_plaintext_refusal_and_pipe_encryption,
    test_retries_across_sessions_and_attempt_audit,
    test_seal_commit_one_file_and_reveal_ancestry,
)


PREREG = "3a6ed854ea577cd933592acabb79cf81b61315f9"
PREPARE_SOURCES = (
    "dogwhistle/listener.py",
    "dogwhistle/listener_adapter.py",
    "tests/test_listener.py",
    "listener/PROTOCOL.md",
)


def frozen_bytes(repo: Path, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{PREREG}:{relative}"], cwd=repo,
        capture_output=True, check=True,
    ).stdout


def test_frozen_sources_match_preregistration():
    source = Path(__file__).resolve().parents[1]
    for relative in PREPARE_SOURCES:
        assert (source / relative).read_bytes() == frozen_bytes(source, relative)


@pytest.fixture
def frozen_repo(tmp_path, monkeypatch):
    """Recreate the pre-prepare branch, then use the frozen test lifecycle."""
    source = Path(__file__).resolve().parents[1]
    remote, repo = tmp_path / "remote.git", tmp_path / "checkout"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", "--shared", str(source), str(repo)],
                   check=True, capture_output=True)
    git(repo, "remote", "set-url", "origin", str(remote))
    git(repo, "config", "user.name", "Test Researcher")
    git(repo, "config", "user.email", "test@example.invalid")
    parent = git(repo, "rev-parse", f"{PREREG}^")
    git(repo, "switch", "-C", "study/listener-ties", parent)
    assert git(repo, "branch", "--show-current") == "study/listener-ties"
    for relative in PREPARE_SOURCES:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(frozen_bytes(repo, relative))
    monkeypatch.setattr(listener, "ROOT", repo)
    monkeypatch.setattr(listener, "FOLDER", repo / "listener")
    monkeypatch.setattr(listener, "PRIVATE", repo / "listener" / ".private")
    monkeypatch.setattr(listener, "REGISTRATION", repo / "listener" / "registration.json")
    monkeypatch.setattr(listener, "STOP_FILE", tmp_path / "stop")
    monkeypatch.setattr(study, "ROOT", repo)
    registration = listener.prepare("test-only-passphrase")
    assert len(registration["trials"]) == listener.TRIALS
    git(repo, "add", *listener.SOURCE_FILES[:5])
    git(repo, "commit", "-m", "Freeze fake listener study")
    git(repo, "push", "-u", "origin", "study/listener-ties")
    return repo
