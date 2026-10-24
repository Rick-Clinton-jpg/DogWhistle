"""No-model checks of the tie-rich sample and the real sealed Git lifecycle."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from dogwhistle import listener, study
from dogwhistle.allocation import FEASIBLE, welfare
from dogwhistle.heldout_adapter import receiver_prompt as coalition_prompt
from dogwhistle.honest_adapter import receiver_prompt as honest_prompt
from dogwhistle.listener_adapter import PROMPTS, QWEN_MODEL_ID, SCHEMAS, prompt, qwen_call
from dogwhistle.visibility import eligible_targets


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=True).stdout.strip()


def test_sample_counts_and_140_disjoint():
    tasks = listener.selected_instances()
    assert len(tasks) == 30 and tasks[-1]["instance_id"] == "alloc-246"
    shapes = [listener.optimum_shape(task) for task in tasks]
    assert [sum(n == k for n, _ in shapes) for k in (2, 3)] == [24, 6]
    assert [sum(n == k for _, n in shapes) for k in (2, 3)] == [25, 5]
    assert all(eligible_targets(task) for task in tasks)
    for task in tasks:
        matrix = task["matrix"]
        best = max(welfare(matrix, assignment) for assignment in FEASIBLE)
        optima = [assignment for assignment in FEASIBLE if welfare(matrix, assignment) == best]
        assert len({tuple(assignment.count(v) for v in range(4)) for assignment in optima}) >= 2
    listener.assert_disjoint(tasks)
    earlier = {listener._matrix_key(task)
               for relative in listener.PRIOR_REGISTRATIONS
               for task in listener.load(listener.ROOT / relative)["instances"]}
    prior5 = json.loads(git(listener.ROOT, "show", f"{listener.PR5_COMMIT}:audit/registration.json"))
    earlier.update(listener._matrix_key(task) for task in prior5["instances"])
    assert len(earlier) == 140
    assert not earlier.intersection(map(listener._matrix_key, tasks))


def test_frozen_prompts_schemas_and_integer_scaling():
    assert PROMPTS["coalition"][0] == coalition_prompt({}).split("\nTrial input:\n")[0]
    assert PROMPTS["honest"][0] == honest_prompt({}).split("\nTrial input:\n")[0]
    payload = {"task": {"matrix": [[1, 2, 3, 4]]}, "handoff": {"required_memory_refs": []}}
    for role in listener.LISTENERS:
        assert SCHEMAS[role].exists()
        for p in listener.PARAPHRASES:
            assert prompt(role, p, payload) == (PROMPTS[role][p - 1] + "\nTrial input:\n" +
                                                  json.dumps(payload, sort_keys=True, ensure_ascii=False))
    assert listener.sensitivity({"codeword": ["A"] * 3, "public": ["B"] * 3}) == {
        "within_differences_of_6": 0, "cross_differences_of_6": 6,
        "sensitivity_times_6": 6, "sensitivity": 1.0}
    assert listener.sensitivity({"codeword": ["A", "B", "C"],
                                 "public": ["A", "B", "C"]})["sensitivity_times_6"] == 0
    assert listener.sensitivity({"codeword": ["INVALID"] * 3,
                                 "public": ["INVALID"] * 3})["sensitivity_times_6"] == 0


def test_qwen_exact_model_and_request_shape(monkeypatch):
    seen = []

    class Response:
        def __init__(self, model):
            self.model = model

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return json.dumps({"model": self.model,
                               "choices": [{"message": {"content": "{}"}}]}).encode()

    def fake_open(request, timeout):
        seen.append((request.full_url, json.loads(request.data), timeout))
        return Response(QWEN_MODEL_ID)

    monkeypatch.setattr("dogwhistle.listener_adapter.urllib.request.urlopen", fake_open)
    assert qwen_call("frozen prompt") == "{}"
    assert seen == [("http://localhost:1234/v1/chat/completions", {
        "model": "qwen2.5-14b-instruct", "messages": [{"role": "user", "content": "frozen prompt"}],
        "temperature": 0}, 120)]

    monkeypatch.setattr("dogwhistle.listener_adapter.urllib.request.urlopen",
                        lambda request, timeout: Response("another-model"))
    with pytest.raises(RuntimeError, match="unexpected model"):
        qwen_call("frozen prompt")


@pytest.fixture
def frozen_repo(tmp_path, monkeypatch):
    """An isolated branch with a local bare remote and real publication checks."""
    source = listener.ROOT
    remote, repo = tmp_path / "remote.git", tmp_path / "checkout"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", "--shared", str(source), str(repo)],
                   check=True, capture_output=True)
    git(repo, "remote", "set-url", "origin", str(remote))
    git(repo, "config", "user.name", "Test Researcher")
    git(repo, "config", "user.email", "test@example.invalid")
    assert git(repo, "branch", "--show-current") == "study/listener-ties"
    for relative in ("dogwhistle/listener.py", "dogwhistle/listener_adapter.py",
                     "tests/test_listener.py", "listener/PROTOCOL.md"):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
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


@pytest.fixture
def fake_receiver(tmp_path, monkeypatch):
    control = tmp_path / "fail"
    control.write_text("fail")
    script = tmp_path / "receiver.py"
    script.write_text(
        "import json, os, pathlib, sys\n"
        "assert not any('test-only-passphrase' in x for x in os.environ.values())\n"
        "assert not any('listener/.private' in x for x in os.environ.values())\n"
        "assert not list(pathlib.Path.cwd().iterdir())\n"
        "envelope=json.load(sys.stdin)\n"
        f"if pathlib.Path({str(control)!r}).read_text() == 'fail': sys.exit(2)\n"
        "print(json.dumps({'assignment':['A','A','B','B','C','C'],"
        "'decoded_pair':['A','B']}))\n"
        "print('model: fake',file=sys.stderr)\n")
    monkeypatch.setenv("DOGWHISTLE_SECRET_MARKER", "test-only-passphrase")
    cli = tmp_path / "codex"
    cli.write_text("#!/bin/sh\necho 'codex-cli 0.163.0-alpha.10.2'\n")
    cli.chmod(0o755)
    monkeypatch.setenv("CODEX_CLI", str(cli))
    return f"python3.12 {script}", control


def test_retries_across_sessions_and_attempt_audit(frozen_repo, fake_receiver):
    command, control = fake_receiver
    waits = []
    with pytest.raises(RuntimeError, match="three consecutive process failures"):
        listener.receive("codex", "test-only-passphrase", command=command,
                         max_trials=1, retry_sleep=waits.append)
    assert waits == [60, 60]
    attempts_path = listener.PRIVATE / "runs/codex/attempts.json.enc"
    attempts = listener.encrypted_load(attempts_path, "test-only-passphrase")
    assert [row["attempt"] for row in attempts] == [1, 2, 3]
    assert not (listener.PRIVATE / "runs/codex/checkpoint.json.enc").exists()
    control.write_text("healthy")
    result = listener.receive("codex", "test-only-passphrase", command=command,
                              max_trials=1, retry_sleep=waits.append)
    assert result["completed"] == 1 and result["process_errors"] == 3
    attempts = listener.encrypted_load(attempts_path, "test-only-passphrase")
    assert [row["attempt"] for row in attempts] == [1, 2, 3, 4]
    assert attempts[-1]["trial_id"] == attempts[0]["trial_id"]
    assert not list(listener.PRIVATE.rglob("*.json"))

    registration = listener.load(listener.REGISTRATION)
    labels = listener.encrypted_load(listener.PRIVATE / "labels.json.enc", "test-only-passphrase")["labels"]
    inputs = listener.encrypted_load(listener.PRIVATE / "inputs.json.enc", "test-only-passphrase")
    while result["completed"] < listener.TRIALS:
        result = listener.receive("codex", "test-only-passphrase", command=command,
                                  max_trials=16, retry_sleep=waits.append)
    assert result["sealed"] and result["completed"] == 360
    ledger = listener.encrypted_load(listener.PRIVATE / "runs/codex/ledger.json.enc",
                                     "test-only-passphrase")
    assert len(ledger["attempts"]) == 363
    assert len(listener.audit_family("codex", registration, labels, inputs, ledger)["trials"]) == 360
    bad = copy.deepcopy(ledger)
    bad["attempts"][3]["attempt"] = 5
    with pytest.raises(ValueError, match="renumbered"):
        listener.audit_family("codex", registration, labels, inputs, bad)
    bad = copy.deepcopy(ledger)
    bad["attempts"].append(copy.deepcopy(bad["attempts"][-1]))
    with pytest.raises(ValueError, match="extra calls"):
        listener.audit_family("codex", registration, labels, inputs, bad)


def test_batches_stop_file_and_publication_gates(frozen_repo, fake_receiver):
    repo, (command, control) = frozen_repo, fake_receiver
    control.write_text("healthy")
    secret = "test-only-passphrase"
    pauses = []
    results = list(listener.receive_batches("codex", secret, batches=2, max_trials=2,
                                            command=command, pause=pauses.append))
    assert [r["completed"] for r in results] == [2, 4] and pauses == [600]
    listener.STOP_FILE.write_text("stop")
    stopped = list(listener.receive_batches("codex", secret, batches=3, max_trials=2,
                                            command=command, pause=pauses.append))
    assert len(stopped) == 1 and stopped[0]["completed"] == 4 and stopped[0]["stopped"]
    listener.STOP_FILE.unlink()

    (repo / "listener/PROTOCOL.md").write_text("dirty")
    with pytest.raises(RuntimeError, match="working tree"):
        listener.receive("codex", secret, command=command, max_trials=1)
    git(repo, "checkout", "--", "listener/PROTOCOL.md")
    (repo / "listener/PROTOCOL.md").write_text("source changed")
    git(repo, "add", "listener/PROTOCOL.md")
    git(repo, "commit", "-m", "Changed frozen source")
    git(repo, "push")
    with pytest.raises((RuntimeError, ValueError), match="source|branch changed"):
        listener.receive("codex", secret, command=command, max_trials=1)
    git(repo, "reset", "--hard", "HEAD~1")
    git(repo, "push", "--force")  # Disposable local test remote only.

    result = {"completed": 4}
    while result["completed"] < listener.TRIALS:
        result = listener.receive("codex", secret, command=command, max_trials=16)
    listener.abandon_qwen("scripted fixture")
    git(repo, "add", "listener/seals/codex.ledger.sha256")
    git(repo, "commit", "-m", "Seal fake Codex ledger")
    git(repo, "add", "listener/seals/qwen.abandoned.json")
    git(repo, "commit", "-m", "Abandon fake Qwen")
    with pytest.raises(RuntimeError, match="pushed"):
        listener.reveal(secret)
    git(repo, "push")
    listener.reveal(secret)
    git(repo, "add", "listener/reveal.json", "listener/codex/ledger.json", "listener/codex/scores.json")
    git(repo, "commit", "-m", "Publish fake outcomes")
    git(repo, "push")
    assert "codex" in listener.audit()
    scores = repo / "listener/codex/scores.json"
    original = scores.read_bytes()
    scores.write_text(original.decode().replace('"passes_0_05": false', '"passes_0_05": true', 1))
    with pytest.raises(ValueError, match="scores differ"):
        listener.audit()
    scores.write_bytes(original)
    ledger = repo / "listener/codex/ledger.json"
    changed = json.loads(ledger.read_text())
    changed["rows"][0]["receiver_stdout"] = "tampered"
    ledger.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="digest mismatch"):
        listener.audit()


def test_plaintext_refusal_and_pipe_encryption(frozen_repo):
    path = listener.PRIVATE / "leak.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="plaintext private file"):
        listener.refuse_plaintext_private()
    path.unlink()
    assert listener._crypt(listener._crypt(b"payload", "test-only-passphrase", decrypt=False),
                           "test-only-passphrase", decrypt=True) == b"payload"
    assert "test-only-passphrase" not in str(listener._scrubbed_env())


def test_seal_commit_one_file_and_reveal_ancestry(frozen_repo):
    repo = frozen_repo
    prereg = git(repo, "rev-parse", "HEAD")
    seal = repo / "listener/seals/codex.ledger.sha256"
    seal.parent.mkdir(parents=True, exist_ok=True)
    seal.write_text("fake-digest\n")
    extra = repo / "listener/extra.txt"
    extra.write_text("unexpected")
    git(repo, "add", "listener/seals/codex.ledger.sha256", "listener/extra.txt")
    git(repo, "commit", "-m", "Invalid two-file seal")
    listener.write(repo / "listener/seals/qwen.abandoned.json",
                   {"family": "qwen", "status": "abandoned", "reason": "fake"})
    git(repo, "add", "listener/seals/qwen.abandoned.json")
    git(repo, "commit", "-m", "Qwen abandoned")
    with pytest.raises(ValueError, match="beyond its digest"):
        listener._seal_or_abandon()

    git(repo, "reset", "--hard", prereg)
    # Construct an invalid order in the disposable repo: reveal first, then seals.
    listener.write(repo / "listener/reveal.json", {"invalid_fixture": True})
    git(repo, "add", "listener/reveal.json")
    git(repo, "commit", "-m", "Reveal too early")
    seal.parent.mkdir(parents=True, exist_ok=True)
    seal.write_text("fake-digest\n")
    git(repo, "add", "listener/seals/codex.ledger.sha256")
    git(repo, "commit", "-m", "Codex seal too late")
    listener.write(repo / "listener/seals/qwen.abandoned.json",
                   {"family": "qwen", "status": "abandoned", "reason": "fake"})
    git(repo, "add", "listener/seals/qwen.abandoned.json")
    git(repo, "commit", "-m", "Qwen seal too late")
    with pytest.raises(ValueError, match="does not descend"):
        listener._verify_reveal_descends_from_seals(listener._seal_or_abandon())
