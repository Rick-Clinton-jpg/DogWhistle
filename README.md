# DogWhistle

**Can a schema-valid agent handoff carry a hidden signal that changes a successor's action?** DogWhistle tests that question with a controlled, synthetic allocation task. A sender can choose two ordered memory references in a handoff; a fresh receiver assigns six items among four vendors. Deterministic code checks the handoff, solves the public allocation optimum, and scores what the receiver actually did.

This repository is an auditable experiment, not a deployed detector. The tested agents were explicitly prompted with a coalition goal and, in the held-out experiment, a shared codebook. Results do not establish spontaneous collusion.

## What the completed studies found

| Study | Main observation | Decision |
| --- | --- | --- |
| [Initial allocation study](study/RESULTS.md), 20 tasks | The free covert arm did not shift assignments against its no-signal control: −0.05 items per task, one-sided exact paired *p* = 1.0. Code-selected refs made controlled covert and no-signal receiver inputs byte-identical. | Full preregistered claim **failed**; sender-dependent input path was closed in the controlled arm. |
| [Held-out carrier study](followup/RESULTS.md), 30 new tasks | A planted two-ref codeword was emitted and decoded 30/30. The free-arm allocation contrast was +0.60 items per task, *p* = 0.0070. But the scripted and explicit allocation-effect controls each missed their +0.5 threshold, and identical receiver inputs yielded different one-shot outputs. | Full preregistered action-effect claim **failed**; channel transmission is established for this elicited setting, while reliable downstream harm remains uncertain. |

Both studies used fresh one-shot model processes, committed protocols and salted hidden-label commitments before calls, sealed sender and receiver records before reveal, and published raw ledgers and deterministic replay audits. These controls make the positive, null, and failed-control outcomes inspectable.

A third, [preregistered visibility test](https://github.com/Rick-Clinton-jpg/DogWhistle/pull/3), is drafted to hold the public task and receiver prompt fixed while varying only the two reference values. It uses repeated receivers to measure one-shot variation. **No calls for that test have run, and it has no results.**

## Repository map

- `dogwhistle/`: task generator, deterministic allocation solver, handoff gate, model adapters, trial orchestration, and audit code.
- `study/`: PR #1 protocol, registration, complete raw record, reveal, scores, and result report.
- `followup/`: PR #2 held-out protocol, complete raw record, reveal, scores, and result report.
- `tests/`: deterministic unit and fake-client lifecycle checks.
- `prior_work/`: separately identified, byte-verified Neural Node Swarm PR #5/#6 record. This work predates the Apart sprint; see its [provenance](prior_work/ORIGIN.md).
- [Visibility test draft PR #3](https://github.com/Rick-Clinton-jpg/DogWhistle/pull/3): separate preregistration until its run is authorized and completed; its files are not yet on `main`.

## Reproduce without model calls

Use Python 3.12 from the repository root:

```sh
python3.12 -m pip install -e '.[test]'
python3.12 -m pytest -q
python3.12 -m dogwhistle.study audit --run-dir study/dogwhistle-1 --reveal study/reveal-dogwhistle-1.json
python3.12 -m dogwhistle.heldout audit --run-dir followup/carrier-1 --reveal followup/reveal-carrier-1.json
python3.12 prior_work/verify_snapshot.py
```

The audits recompute commitments, digests, gate decisions, solver scores, and registered outcome comparisons from the published records. They make no model calls. Exact designs and limitations are in each study's protocol and results report.

## Scope

The carrier tested here is a sender's choice of two ordered `required_memory_refs` from four vendor refs. Code-selecting those refs from public task data removes sender-dependent bits through that specific field; it is not a proof that all handoff channels are closed. The allocation matrices are synthetic, the receiver sees the public matrix, and the observed effects do not provide a production risk rate.

DogWhistle was developed for the [Apart AI Collusion Research Sprint's Carriers and Countermeasures track](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25). The pre-sprint Neural Node Swarm studies are preserved as prior work, with their original chronology intact.
