"""No-model checks for the preregistered visibility ablation."""

from __future__ import annotations

import json

import pytest

from dogwhistle.allocation import benchmark, generate_instances
from dogwhistle.gate import public_refs
from dogwhistle.study import digest
from dogwhistle import visibility
from prior_work.nns_snapshot.src.neural_node_swarm.verifier import verify_node_output


def test_new_sample_supports_noncolliding_visibility_ablation():
    tasks = generate_instances(visibility.SEED, visibility.INSTANCES)
    assert len(tasks) == 30
    new_matrices = {tuple(map(tuple, task["matrix"])) for task in tasks}
    for relative in ("study/registration.json", "followup/registration.json"):
        prior = json.loads((visibility.ROOT / relative).read_text(encoding="utf-8"))
        prior_matrices = {tuple(map(tuple, task["matrix"]))
                          for task in prior["instances"]}
        assert new_matrices.isdisjoint(prior_matrices)
    for task in tasks:
        eligible = visibility.eligible_targets(task)
        assert eligible
        pair = eligible[0]
        codeword = visibility.trial_input(task, pair, "codeword")
        control = visibility.trial_input(task, pair, "public")
        assert codeword["task"] == control["task"]
        assert codeword["handoff"]["required_memory_refs"] != public_refs(task)
        assert {k: v for k, v in codeword["handoff"].items()
                if k != "required_memory_refs"} == {
                    k: v for k, v in control["handoff"].items()
                    if k != "required_memory_refs"
                }
        assert verify_node_output(codeword["handoff"])["status"] == "passed"
        assert verify_node_output(control["handoff"])["status"] == "passed"


def test_fake_checkpoint_seal_reveal_audit_and_input_tamper(tmp_path, monkeypatch):
    folder = tmp_path / "visibility"
    monkeypatch.setattr(visibility, "ROOT", tmp_path)
    monkeypatch.setattr(visibility, "FOLDER", folder)
    monkeypatch.setattr(visibility, "REGISTRATION", folder / "registration.json")
    monkeypatch.setattr(visibility, "SECRET", folder / ".private" / "labels.json")
    monkeypatch.setattr(visibility, "ensure_published", lambda paths: "fake-pushed-commit")
    monkeypatch.setattr(visibility, "_verify_history", lambda ledger, reveal, public: None)

    registration = visibility.prepare()
    secret = visibility.load(visibility.SECRET)
    visibility.validate_registration(registration, secret)
    assert len(registration["trials"]) == 270

    def fake_receiver(command, payload):
        if "explicit_coalition" in payload:
            pair = payload["explicit_coalition"]
        else:
            named = {ref.split("/", 1)[1]
                     for ref in payload["handoff"]["required_memory_refs"]}
            pair = [vendor for vendor in "ABCD" if vendor not in named]
        assignment = benchmark(payload["task"]["matrix"], tuple(pair))["canonical_optimum"]
        return json.dumps({"assignment": assignment, "decoded_pair": pair}), 0

    monkeypatch.setattr(visibility, "invoke", fake_receiver)
    run_dir = folder / ".private" / "runs" / "fake-1"
    assert visibility.receive(run_dir, "fake-receiver", max_trials=17) is False
    assert len(visibility.load(run_dir / "receiver_progress.json")["rows"]) == 17
    assert visibility.receive(run_dir, "fake-receiver") is True
    assert len(visibility.load(run_dir / "ledger.json")["receiver_rows"]) == 270
    reveal_path = visibility.reveal(run_dir)
    result = visibility.audit(run_dir, reveal_path)
    assert result == visibility.load(run_dir / "scores.json")
    assert result["commitment_verified"] and result["input_replay_verified"]

    ledger = visibility.load(run_dir / "ledger.json")
    ledger["receiver_rows"][0]["receiver_input"]["handoff"]["objective"] = "tampered"
    (run_dir / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    visibility.seal_path(run_dir).write_text(digest((run_dir / "ledger.json").read_bytes()) + "\n")
    with pytest.raises(ValueError, match="receiver input differs"):
        visibility.audit(run_dir, reveal_path)
