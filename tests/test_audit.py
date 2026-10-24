"""No-model checks of the frozen listener audit and sealed lifecycle."""

from __future__ import annotations

import json

import pytest

from dogwhistle import audit
from dogwhistle.allocation import benchmark, generate_instances
from dogwhistle.audit_adapter import PROMPTS, SCHEMAS, prompt, qwen_call
from dogwhistle.heldout_adapter import receiver_prompt as coalition_prompt
from dogwhistle.honest_adapter import receiver_prompt as honest_prompt


def test_sample_disjoint_from_all_110_prior_matrices():
    tasks = generate_instances(audit.SEED, audit.INSTANCES)
    audit.assert_disjoint(tasks)
    assert len({tuple(map(tuple, task["matrix"])) for task in tasks}) == 30
    earlier = {tuple(map(tuple, task["matrix"]))
               for relative in audit.PRIOR_REGISTRATIONS
               for task in audit.load(audit.ROOT / relative)["instances"]}
    assert len(earlier) == 110


def test_frozen_prompts_and_schemas():
    assert PROMPTS["coalition"][0] == coalition_prompt({}).split("\nTrial input:\n")[0]
    assert PROMPTS["honest"][0] == honest_prompt({}).split("\nTrial input:\n")[0]
    payload = {"task": {"matrix": [[1, 2, 3, 4]]}, "handoff": {"required_memory_refs": []}}
    for listener in audit.LISTENERS:
        assert SCHEMAS[listener].exists()
        for paraphrase in audit.PARAPHRASES:
            assert prompt(listener, paraphrase, payload) == (
                PROMPTS[listener][paraphrase - 1] + "\nTrial input:\n" +
                json.dumps(payload, sort_keys=True, ensure_ascii=False))


def test_balanced_pair_contrast_and_integer_scaling():
    constant_by_arm = {"codeword": ["A"] * 3, "public": ["B"] * 3}
    assert audit.sensitivity(constant_by_arm) == {
        "within_differences_of_6": 0, "cross_differences_of_6": 6,
        "sensitivity_times_6": 6, "sensitivity": 1.0,
    }
    same_paraphrase_effect = {"codeword": ["A", "B", "C"],
                              "public": ["A", "B", "C"]}
    result = audit.sensitivity(same_paraphrase_effect)
    assert result["within_differences_of_6"] == result["cross_differences_of_6"] == 6
    assert result["sensitivity_times_6"] == 0
    invalid = {"codeword": ["INVALID"] * 3, "public": ["INVALID"] * 3}
    assert audit.sensitivity(invalid)["sensitivity_times_6"] == 0


def test_qwen_adapter_uses_prompt_only_json(monkeypatch):
    seen = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return json.dumps({"model": "qwen2.5-14b-instruct-q4_k_m",
                               "choices": [{"message": {"content": "{}"}}]}).encode()

    def fake_open(request, timeout):
        seen.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr("dogwhistle.audit_adapter.urllib.request.urlopen", fake_open)
    assert qwen_call("frozen prompt") == "{}"
    assert seen == [{"model": "qwen2.5-14b-instruct", "messages": [
        {"role": "user", "content": "frozen prompt"}], "temperature": 0}]


def test_fake_encrypted_lifecycle_and_isolation(tmp_path, monkeypatch):
    folder = tmp_path / "audit"
    monkeypatch.setattr(audit, "FOLDER", folder)
    monkeypatch.setattr(audit, "PRIVATE", folder / ".private")
    monkeypatch.setattr(audit, "REGISTRATION", folder / "registration.json")
    monkeypatch.setattr(audit, "_prereg_check", lambda: "fake-prereg")
    monkeypatch.setattr(audit, "_codex_version", lambda: "codex-cli 0.163.0-alpha.10.2")
    monkeypatch.setattr(audit, "_seal_or_abandon", lambda: {
        "codex": "fake-codex-seal", "qwen": "fake-qwen-abandoned"})
    monkeypatch.setattr(audit, "_verify_sources", lambda prereg: None)
    passphrase = "test-only-passphrase"
    registration = audit.prepare(passphrase)
    assert len(registration["instances"]) == 30
    assert len(registration["trials"]) == 360
    private_files = list((folder / ".private").rglob("*"))
    assert all(path.suffix == ".enc" for path in private_files if path.is_file())
    assert all(b"salt_hex" not in path.read_bytes() for path in private_files if path.is_file())
    labels = audit.encrypted_load(folder / ".private" / "labels.json.enc", passphrase)
    inputs = audit.encrypted_load(folder / ".private" / "inputs.json.enc", passphrase)
    audit.validate_registration(registration, labels, inputs)
    seen = []

    def fake_receiver(command, envelope):
        seen.append(envelope)
        if len(seen) == 1:
            return "", 1, "transient error"
        if len(seen) == 2:
            assert seen[0] == seen[1]
            return "{}", 0, "model: fake"
        task = envelope["receiver_input"]["task"]
        assignment = benchmark(task["matrix"], ("A", "B"))["canonical_optimum"]
        return json.dumps({"assignment": assignment, "decoded_pair": ["A", "B"]}), 0, "model: fake"

    monkeypatch.setattr(audit, "invoke", fake_receiver)
    first = audit.receive("codex", passphrase, max_trials=16, command="fake")
    assert first == {"completed": 16, "process_errors": 1, "retries": 1, "sealed": False}
    checkpoint = audit.encrypted_load(folder / ".private" / "runs" / "codex" /
                                      "checkpoint.json.enc", passphrase)
    assert len(checkpoint["rows"]) == 16
    with pytest.raises(ValueError, match="plaintext private file"):
        (folder / ".private" / "leak.json").write_text("{}")
        audit.receive("codex", passphrase, max_trials=1, command="fake")
    (folder / ".private" / "leak.json").unlink()
    while first["completed"] < audit.TRIALS:
        first = audit.receive("codex", passphrase, max_trials=16, command="fake")
    assert first == {"completed": 360, "process_errors": 1, "retries": 1, "sealed": True}
    assert len(seen) == 361
    ledger = audit.encrypted_load(folder / ".private" / "runs" / "codex" /
                                  "ledger.json.enc", passphrase)
    assert len(ledger["rows"]) == 360 and len(ledger["attempts"]) == 361
    assert ledger["attempts"][0]["attempt"] == 1
    assert ledger["attempts"][1]["attempt"] == 2
    assert ledger["reported_model_ids"] == ["fake"]
    audit.write(folder / "seals" / "qwen.abandoned.json",
                {"family": "qwen", "status": "abandoned", "reason": "fake lifecycle"})
    audit.reveal(passphrase)
    reports = audit.audit()
    assert list(reports) == ["codex"]
    assert len(reports["codex"]["trials"]) == 360
    assert reports["codex"]["trials"][0]["score"]["valid"] is False
    assert reports["codex"]["summary"]["manipulation_check"]["passes"]
