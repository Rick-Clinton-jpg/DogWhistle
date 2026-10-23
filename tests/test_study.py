import json
from pathlib import Path
import sys

import pytest

from dogwhistle import study


def test_sealed_fake_run_replays_and_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "ROOT", tmp_path)
    monkeypatch.setattr(study, "STUDY", tmp_path / "study")
    monkeypatch.setattr(study, "REGISTRATION", tmp_path / "study" / "registration.json")
    monkeypatch.setattr(study, "SECRET", tmp_path / "study" / ".private" / "labels.json")
    monkeypatch.setattr(study, "ensure_published", lambda paths: "fake-pushed-commit")
    monkeypatch.setattr(study, "verify_history", lambda *args: None)
    fake = tmp_path / "fake.py"
    fake.write_text(
        "import json,sys\n"
        "payload=json.load(sys.stdin)\n"
        "if 'condition' in payload:\n"
        " task=payload['task']\n"
        " refs=['vendor/A','vendor/B']\n"
        " print(json.dumps({'schema_version':'1.0','step_id':task['instance_id'],"
        "'objective':'Allocate items','success_criteria':['Assign all'],"
        "'required_memory_refs':refs}))\n"
        "else:\n"
        " print(json.dumps({'assignment':['A','A','B','B','C','C']}))\n",
        encoding="utf-8",
    )
    command = f"{sys.executable} {fake}"
    registration = study.prepare(seed=20261023, instances=2)
    assert len(registration["trials"]) == 10
    run_dir = study.STUDY / ".private" / "runs" / "fake"
    assert study.send(run_dir, command, max_trials=3) is False
    assert study.send(run_dir, command) is True
    assert study.receive(run_dir, command, max_trials=4) is False
    assert study.receive(run_dir, command) is True
    reveal = study.reveal(run_dir)
    result = study.audit(run_dir, reveal)
    assert result["commitment_verified"] is True
    assert result["gate_replay_verified"] is True
    assert len(result["trials"]) == 10
    ledger = run_dir / "ledger.json"
    changed = json.loads(ledger.read_text())
    changed["receiver_rows"][0]["receiver_stdout"] = "{}"
    ledger.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="ledger digest mismatch"):
        study.audit(run_dir, reveal)
