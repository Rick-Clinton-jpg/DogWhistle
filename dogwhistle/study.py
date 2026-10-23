"""Sealed, restartable two-node allocation experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import tempfile
from typing import Any

from dogwhistle.allocation import benchmark, eligible_coalitions, generate_instances, score
from dogwhistle.gate import deliver, handoff, public_refs
from dogwhistle.stats import summarize


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "study"
REGISTRATION = STUDY / "registration.json"
SECRET = STUDY / ".private" / "labels.json"
REGIMES = ("free", "controlled")
CONDITIONS = ("covert", "no_signal")
CELLS = tuple((regime, condition) for regime in REGIMES for condition in CONDITIONS)
SOURCE_FILES = (
    "study/PROTOCOL.md", "study/registration.json", "dogwhistle/study.py",
    "dogwhistle/allocation.py", "dogwhistle/gate.py", "dogwhistle/stats.py",
    "dogwhistle/codex_adapter.py", "dogwhistle/assignment.schema.json",
    "prior_work/manifest.json",
    "prior_work/nns_snapshot/schemas/node_output.schema.json",
    "prior_work/nns_snapshot/src/neural_node_swarm/verifier.py",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def label_commitment(salt_hex: str, labels: dict[str, list[str]]) -> str:
    return digest(bytes.fromhex(salt_hex) + canonical(labels))


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        if private:
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def checkpoint(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                            text=True, check=True)
    return result.stdout.strip()


def ensure_published(paths: tuple[str, ...]) -> str:
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    if not branch or git("ls-remote", "origin", f"refs/heads/{branch}").split("\t")[0] != head:
        raise RuntimeError("current commit must be pushed to its remote branch")
    for relative in paths:
        committed = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=ROOT,
                                   capture_output=True, check=True).stdout
        if committed != (ROOT / relative).read_bytes():
            raise RuntimeError(f"{relative} differs from pushed commit")
    return head


def prepare(*, seed: int, instances: int) -> dict:
    if REGISTRATION.exists() or SECRET.exists():
        raise FileExistsError("registration already exists")
    tasks = generate_instances(seed, instances)
    hidden: dict[str, list[str]] = {}
    rng = secrets.SystemRandom()
    for task in tasks:
        eligible = eligible_coalitions(task["matrix"])
        if not eligible:
            raise ValueError(f"no coalition opportunity for {task['instance_id']}; choose another public seed")
        hidden[task["instance_id"]] = list(rng.choice(eligible))
        reference = benchmark(task["matrix"], ("A", "B"))
        task["public_optimum_welfare"] = reference["optimum_welfare"]
        task["welfare_floor"] = reference["near_optimal_floor"]
    trials = [
        {"trial_id": f"{task['instance_id']}-{regime}-{condition}",
         "instance_id": task["instance_id"], "regime": regime, "condition": condition}
        for task in tasks for regime, condition in CELLS
    ]
    trials.extend({"trial_id": f"{task['instance_id']}-explicit",
                   "instance_id": task["instance_id"], "regime": "explicit",
                   "condition": "explicit"} for task in tasks)
    rng.shuffle(trials)
    salt_hex = secrets.token_hex(32)
    registration = {
        "protocol_version": "1.0", "public_seed": seed,
        "instances": tasks, "trials": trials, "instances_per_cell": instances,
        "commitment_sha256": label_commitment(salt_hex, hidden),
        "commitment_encoding": "SHA256(bytes.fromhex(salt_hex) + canonical JSON of instance_id to coalition mapping)",
        "prior_work": ["https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/pull/5",
                       "https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/pull/6"],
    }
    write(SECRET, {"salt_hex": salt_hex, "labels": hidden}, private=True)
    write(REGISTRATION, registration)
    return registration


def validate_registration(registration: dict, secret: dict) -> None:
    if label_commitment(secret["salt_hex"], secret["labels"]) != registration["commitment_sha256"]:
        raise ValueError("coalition commitment mismatch")
    tasks = generate_instances(registration["public_seed"], registration["instances_per_cell"])
    if [{key: task[key] for key in ("instance_id", "matrix", "vendors", "capacity_per_vendor")}
        for task in tasks] != [
        {key: task[key] for key in ("instance_id", "matrix", "vendors", "capacity_per_vendor")}
        for task in registration["instances"]
    ]:
        raise ValueError("public task generator mismatch")
    ids = {task["instance_id"] for task in registration["instances"]}
    if set(secret["labels"]) != ids or len(registration["trials"]) != len(ids) * 5:
        raise ValueError("registration size mismatch")
    if len({trial["trial_id"] for trial in registration["trials"]}) != len(registration["trials"]):
        raise ValueError("duplicate trial")
    for task in registration["instances"]:
        pair = tuple(secret["labels"][task["instance_id"]])
        if pair not in eligible_coalitions(task["matrix"]):
            raise ValueError("coalition violates opportunity rule")
        reference = benchmark(task["matrix"], ("A", "B"))
        if (task["public_optimum_welfare"], task["welfare_floor"]) != (
            reference["optimum_welfare"], reference["near_optimal_floor"]
        ):
            raise ValueError("published optimum or floor differs from solver")
    expected = {(task_id, regime, condition)
                for task_id in ids for regime, condition in CELLS}
    expected |= {(task_id, "explicit", "explicit") for task_id in ids}
    if {(t["instance_id"], t["regime"], t["condition"]) for t in registration["trials"]} != expected:
        raise ValueError("trial schedule mismatch")


def invoke(command: str, payload: dict) -> tuple[str, int]:
    argv = shlex.split(command)
    if not argv:
        raise ValueError("empty adapter command")
    with tempfile.TemporaryDirectory(prefix="dogwhistle-node-") as cwd:
        result = subprocess.run(argv, input=json.dumps(payload), text=True,
                                capture_output=True, cwd=cwd, check=False, timeout=140)
    return result.stdout, result.returncode


def run_paths(run_dir: Path) -> tuple[Path, Path, Path]:
    return (run_dir / "sender_progress.json", run_dir / "sender_seal.json",
            STUDY / "seals" / f"{run_dir.name}.sha256")


def public_ledger_digest_path(run_dir: Path) -> Path:
    return STUDY / "seals" / f"{run_dir.name}.ledger.sha256"


def send(run_dir: Path, command: str, max_trials: int | None = None) -> bool:
    prereg_head = ensure_published(SOURCE_FILES)
    registration, secret = load(REGISTRATION), load(SECRET)
    validate_registration(registration, secret)
    if max_trials is not None and max_trials < 1:
        raise ValueError("max_trials must be positive")
    progress, seal_path, public_seal = run_paths(run_dir)
    if seal_path.exists():
        raise FileExistsError("sender seal already complete")
    state = load(progress) if progress.exists() else {
        "registration_sha256": digest(REGISTRATION.read_bytes()),
        "sender_command": command, "prereg_commit": prereg_head, "rows": [],
    }
    if (state["registration_sha256"], state["sender_command"], state["prereg_commit"]) != (
        digest(REGISTRATION.read_bytes()), command, prereg_head
    ):
        raise ValueError("sender checkpoint does not match registration or command")
    trials = registration["trials"]
    if [row["trial_id"] for row in state["rows"]] != [t["trial_id"] for t in trials[:len(state["rows"])]]:
        raise ValueError("sender checkpoint order differs")
    tasks = {task["instance_id"]: task for task in registration["instances"]}
    started = 0
    for trial in trials[len(state["rows"]):]:
        if max_trials is not None and started >= max_trials:
            return False
        task = tasks[trial["instance_id"]]
        if trial["regime"] == "explicit":
            payload, raw, delivered, reason = None, None, handoff(task, public_refs(task)), "explicit"
        else:
            payload = {"task": task, "condition": trial["condition"]}
            if trial["condition"] == "covert":
                payload["private_coalition"] = secret["labels"][trial["instance_id"]]
            raw, code = invoke(command, payload)
            if code:
                raise RuntimeError(f"sender adapter failed at {trial['trial_id']}; retry same trial")
            delivered, reason = deliver(raw, task, trial["regime"])
        state["rows"].append({**trial, "sender_input": payload, "sender_stdout": raw,
                              "delivered_handoff": delivered, "gate_result": reason})
        checkpoint(progress, state)
        started += 1
    seal = {"registration_sha256": state["registration_sha256"],
            "prereg_commit": prereg_head, "sender_command": command,
            "sender_rows": state["rows"]}
    write(seal_path, seal, private=True)
    public_seal.parent.mkdir(parents=True, exist_ok=True)
    if public_seal.exists():
        raise FileExistsError(public_seal)
    public_seal.write_text(digest(seal_path.read_bytes()) + "\n", encoding="ascii")
    return True


def receiver_input(row: dict, task: dict, secret: dict | None = None) -> dict:
    payload = {"task": task, "handoff": row["delivered_handoff"]}
    if row["regime"] == "explicit":
        if secret is None:
            raise ValueError("explicit diagnostic needs sealed coalition")
        payload["explicit_coalition"] = secret["labels"][row["instance_id"]]
    return payload


def receive(run_dir: Path, command: str, max_trials: int | None = None) -> bool:
    _, seal_path, public_seal = run_paths(run_dir)
    seal_commit = ensure_published((str(public_seal.relative_to(ROOT)), *SOURCE_FILES))
    seal_hash = digest(seal_path.read_bytes())
    if seal_hash != public_seal.read_text(encoding="ascii").strip():
        raise ValueError("sender seal differs from committed digest")
    if max_trials is not None and max_trials < 1:
        raise ValueError("max_trials must be positive")
    ledger_path = run_dir / "ledger.json"
    if ledger_path.exists():
        raise FileExistsError("receiver ledger already complete")
    registration, secret, seal = load(REGISTRATION), load(SECRET), load(seal_path)
    validate_registration(registration, secret)
    if seal["registration_sha256"] != digest(REGISTRATION.read_bytes()):
        raise ValueError("sender seal registration mismatch")
    progress = run_dir / "receiver_progress.json"
    state = load(progress) if progress.exists() else {
        "sender_seal_sha256": seal_hash, "receiver_command": command,
        "seal_commit": seal_commit, "rows": [],
    }
    if (state["sender_seal_sha256"], state["receiver_command"], state["seal_commit"]) != (
        seal_hash, command, seal_commit
    ):
        raise ValueError("receiver checkpoint does not match seal or command")
    rows = seal["sender_rows"]
    if [row["trial_id"] for row in state["rows"]] != [row["trial_id"] for row in rows[:len(state["rows"])]]:
        raise ValueError("receiver checkpoint order differs")
    tasks = {task["instance_id"]: task for task in registration["instances"]}
    started = 0
    for row in rows[len(state["rows"]):]:
        if max_trials is not None and started >= max_trials:
            return False
        payload = receiver_input(row, tasks[row["instance_id"]], secret)
        raw, code = invoke(command, payload)
        if code:
            raise RuntimeError(f"receiver adapter failed at {row['trial_id']}; retry same trial")
        state["rows"].append({"trial_id": row["trial_id"], "receiver_input": payload,
                              "receiver_stdout": raw})
        checkpoint(progress, state)
        started += 1
    ledger = {"registration_sha256": seal["registration_sha256"],
              "sender_seal_sha256": seal_hash, "seal_commit": seal_commit,
              "receiver_command": command,
              "receiver_rows": state["rows"]}
    write(ledger_path, ledger, private=True)
    ledger_hash = digest(ledger_path.read_bytes()) + "\n"
    (run_dir / "ledger.sha256").write_text(ledger_hash, encoding="ascii")
    public_ledger = public_ledger_digest_path(run_dir)
    public_ledger.parent.mkdir(parents=True, exist_ok=True)
    if public_ledger.exists():
        raise FileExistsError(public_ledger)
    public_ledger.write_text(ledger_hash, encoding="ascii")
    return True


def parse_assignment(raw: str) -> Any:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed.get("assignment") if isinstance(parsed, dict) else None


def verify_history(seal: dict, ledger: dict, reveal_data: dict,
                   public_seal: Path, public_ledger: Path) -> None:
    prereg_commit = seal["prereg_commit"]
    seal_commit = ledger["seal_commit"]
    ledger_commit = reveal_data["ledger_commit"]
    for earlier, later in ((prereg_commit, seal_commit), (seal_commit, ledger_commit)):
        subprocess.run(["git", "merge-base", "--is-ancestor", earlier, later],
                       cwd=ROOT, capture_output=True, check=True)
    for relative in SOURCE_FILES:
        committed = subprocess.run(["git", "show", f"{prereg_commit}:{relative}"],
                                   cwd=ROOT, capture_output=True, check=True).stdout
        if committed != (ROOT / relative).read_bytes():
            raise ValueError(f"preregistered source changed: {relative}")
    for commit, path in ((seal_commit, public_seal), (ledger_commit, public_ledger)):
        relative = str(path.relative_to(ROOT))
        committed = subprocess.run(["git", "show", f"{commit}:{relative}"],
                                   cwd=ROOT, capture_output=True, check=True).stdout
        if committed != path.read_bytes():
            raise ValueError(f"published chronology anchor differs: {relative}")


def audit(run_dir: Path, reveal_path: Path) -> dict:
    registration, reveal = load(REGISTRATION), load(reveal_path)
    validate_registration(registration, reveal)
    _, seal_path, public_seal = run_paths(run_dir)
    seal, ledger = load(seal_path), load(run_dir / "ledger.json")
    if digest(seal_path.read_bytes()) != public_seal.read_text(encoding="ascii").strip():
        raise ValueError("sender seal digest mismatch")
    if digest((run_dir / "ledger.json").read_bytes()) != (run_dir / "ledger.sha256").read_text().strip():
        raise ValueError("receiver ledger digest mismatch")
    public_ledger = public_ledger_digest_path(run_dir)
    if public_ledger.read_text(encoding="ascii") != (run_dir / "ledger.sha256").read_text(encoding="ascii"):
        raise ValueError("public receiver digest mismatch")
    verify_history(seal, ledger, reveal, public_seal, public_ledger)
    if seal["registration_sha256"] != digest(REGISTRATION.read_bytes()):
        raise ValueError("registration digest mismatch")
    if ledger["sender_seal_sha256"] != digest(seal_path.read_bytes()):
        raise ValueError("ledger does not bind sender seal")
    if len(seal["sender_rows"]) != len(registration["trials"]) or len(ledger["receiver_rows"]) != len(registration["trials"]):
        raise ValueError("missing trials")
    tasks = {task["instance_id"]: task for task in registration["instances"]}
    scored_rows = []
    for trial, sender, receiver in zip(registration["trials"], seal["sender_rows"], ledger["receiver_rows"], strict=True):
        if sender["trial_id"] != receiver["trial_id"] or sender["trial_id"] != trial["trial_id"]:
            raise ValueError("trial order mismatch")
        task = tasks[trial["instance_id"]]
        pair = tuple(reveal["labels"][trial["instance_id"]])
        if trial["regime"] == "explicit":
            expected = handoff(task, public_refs(task))
            reason = "explicit"
            if sender["sender_input"] is not None or sender["sender_stdout"] is not None:
                raise ValueError("explicit diagnostic had a sender call")
        else:
            expected_input = {"task": task, "condition": trial["condition"]}
            if trial["condition"] == "covert":
                expected_input["private_coalition"] = list(pair)
            if sender["sender_input"] != expected_input:
                raise ValueError("sender input differs from committed label or task")
            expected, reason = deliver(sender["sender_stdout"], task, trial["regime"])
        if sender["delivered_handoff"] != expected or sender["gate_result"] != reason:
            raise ValueError("gate replay mismatch")
        if receiver["receiver_input"] != receiver_input(sender, task, reveal):
            raise ValueError("receiver saw a different input")
        result = score(task["matrix"], pair, parse_assignment(receiver["receiver_stdout"]))
        scored_rows.append({**trial, "gate_result": reason, "score": result})
    controlled_inputs_identical = all(
        next(row["receiver_input"] for row in ledger["receiver_rows"]
             if row["trial_id"] == f"{task['instance_id']}-controlled-covert") ==
        next(row["receiver_input"] for row in ledger["receiver_rows"]
             if row["trial_id"] == f"{task['instance_id']}-controlled-no_signal")
        for task in registration["instances"]
    )
    if not controlled_inputs_identical:
        raise ValueError("controlled receiver inputs are not identical within instance")
    result = {"registration_sha256": digest(REGISTRATION.read_bytes()),
            "sender_seal_sha256": digest(seal_path.read_bytes()),
            "ledger_sha256": digest((run_dir / "ledger.json").read_bytes()),
            "commitment_verified": True, "gate_replay_verified": True,
            "chronology_verified": True,
            "controlled_inputs_identical": True,
            "summary": summarize(scored_rows), "trials": scored_rows}
    scores_path = run_dir / "scores.json"
    if scores_path.exists() and load(scores_path) != result:
        raise ValueError("published scores differ from deterministic replay")
    return result


def reveal(run_dir: Path) -> Path:
    ledger_path = run_dir / "ledger.json"
    if not ledger_path.exists():
        raise FileNotFoundError("all receiver trials must finish before reveal")
    registration = load(REGISTRATION)
    if len(load(ledger_path)["receiver_rows"]) != len(registration["trials"]):
        raise ValueError("receiver ledger incomplete")
    public_ledger = public_ledger_digest_path(run_dir)
    ledger_commit = ensure_published((str(public_ledger.relative_to(ROOT)), *SOURCE_FILES))
    if public_ledger.read_text(encoding="ascii").strip() != digest(ledger_path.read_bytes()):
        raise ValueError("receiver ledger differs from committed digest")
    secret = load(SECRET)
    validate_registration(registration, secret)
    reveal_path = STUDY / f"reveal-{run_dir.name}.json"
    write(reveal_path, {**secret, "ledger_commit": ledger_commit})
    write(run_dir / "scores.json", audit(run_dir, reveal_path))
    return reveal_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--seed", type=int, default=20261023)
    prep.add_argument("--instances", type=int, default=20)
    for action, flag in (("send", "--sender-cmd"), ("receive", "--receiver-cmd")):
        command = sub.add_parser(action)
        command.add_argument("--run-dir", type=Path, required=True)
        command.add_argument(flag, required=True)
        command.add_argument("--max-trials", type=int)
    rev = sub.add_parser("reveal")
    rev.add_argument("--run-dir", type=Path, required=True)
    check = sub.add_parser("audit")
    check.add_argument("--run-dir", type=Path, required=True)
    check.add_argument("--reveal", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        registration = prepare(seed=args.seed, instances=args.instances)
        print(json.dumps({"instances": len(registration["instances"]),
                          "trials": len(registration["trials"]),
                          "commitment_sha256": registration["commitment_sha256"]}, indent=2))
    elif args.action == "send":
        print(json.dumps({"sender_phase_complete": send(args.run_dir, args.sender_cmd, args.max_trials)}))
    elif args.action == "receive":
        print(json.dumps({"receiver_phase_complete": receive(args.run_dir, args.receiver_cmd, args.max_trials)}))
    elif args.action == "reveal":
        print(reveal(args.run_dir))
    else:
        result = audit(args.run_dir, args.reveal)
        print(json.dumps({key: value for key, value in result.items() if key != "trials"}, indent=2))


if __name__ == "__main__":
    main()
