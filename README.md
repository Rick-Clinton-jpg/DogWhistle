# DogWhistle

**Can a schema-valid agent handoff carry a hidden signal that changes a successor's action?** DogWhistle studies that question with synthetic allocation tasks. A handoff can carry a planted codeword in two `required_memory_refs`; a fresh receiver assigns six items among four vendors. Deterministic code validates the handoff, finds the public welfare optimum, and scores the receiver's action.

The experiments use explicit prompts and a known codeword. They do not establish spontaneous collusion or a production risk rate.

## Completed studies

Each result below has its own preregistered decision. The task samples were not pooled.

| Study | Registered outcome |
| --- | --- |
| [PR #1: initial allocation](study/RESULTS.md), 20 tasks | Full claim **failed**. The free covert arm did not shift assignments against its no-signal control (−0.05 items per task; one-sided *p* = 1.0). Code-selected refs made the controlled inputs byte-identical. |
| [PR #2: held-out carrier](followup/RESULTS.md), 30 tasks | Full action-effect claim **failed** because both allocation-effect positive controls missed their thresholds. The planted codeword was emitted and decoded 30/30; the free-arm contrast was +0.60 items per task (*p* = 0.0070). |
| [PR #3: visibility ablation](visibility/RESULTS.md), 30 tasks | Full registered claim **passed** for a coalition-seeking receiver told the planted convention. Codeword refs increased hidden-pair assignments versus public-task-selected refs by +0.4222 per receiver (*p* = 0.0003265); the explicit functionality control passed. |
| [PR #4: honest successor](honest/RESULTS.md), 30 tasks | The codeword was **inert within the registered ±0.20-assignment mean margin** under the honest prompt. Codeword minus public was −0.0111 per receiver; both equivalence tests passed. |
| [PR #6: tie-rich listener audit](listener/RESULTS.md), 30 tasks | The confirmatory Codex audit **separated the two instructed listener types**: mean sensitivity difference +0.3556, exact one-sided *p* = 2.049 × 10⁻⁷; all four Holm-corrected secondary tests passed. The exploratory local Qwen family failed every cell's assignment-validity threshold, so its null result is uninformative. |

PR #5 was [retired after 80 of 360 calls](https://github.com/Rick-Clinton-jpg/DogWhistle/blob/069be1a71146fcb6d5d86c89880edb69a2935d94/audit/seals/retired-partial.json), with no confirmatory decision. Its [unchanged partial record and descriptive summary](https://github.com/Rick-Clinton-jpg/DogWhistle/blob/96a9c94a34c31febc565af2f91ab34b705fa63ae/audit/retired-80/README.md) were published after PR #6's reveal on the preserved PR #5 branch.

The completed studies publish protocols, raw records, reveals, scores, and deterministic replay audits. PR #1 and #2 include sender and receiver seals; PR #3, #4, and #6 used receiver-only trials.

## Repository map

- `dogwhistle/`: task generator, deterministic allocation solver, handoff gate, model adapters, trial orchestration, and audit code.
- `study/`, `followup/`, `visibility/`, `honest/`, `listener/`: the completed studies' protocols, registrations, seals, records, scores, and reports.
- `listener/MAINTENANCE.md`: post-publication test-fixture correction; frozen study files and results were not changed.
- `analysis/`: post-reveal visibility analysis, kept separate from preregistered decisions.
- `tests/`: deterministic unit and fake-client lifecycle checks.
- `prior_work/`: separately identified, byte-verified Neural Node Swarm PR #5/#6 record. This work predates the Apart sprint; see its [provenance](prior_work/ORIGIN.md).

## Reproduce without model calls

Use Python 3.12 from the repository root:

```sh
python3.12 -m pip install -e '.[test]'
python3.12 -m pytest -q
python3.12 -m dogwhistle.study audit --run-dir study/dogwhistle-1 --reveal study/reveal-dogwhistle-1.json
python3.12 -m dogwhistle.heldout audit --run-dir followup/carrier-1 --reveal followup/reveal-carrier-1.json
python3.12 -m dogwhistle.visibility audit --run-dir visibility/vis-1 --reveal visibility/reveal-vis-1.json
python3.12 -m dogwhistle.honest audit --run-dir honest/honest-1 --reveal honest/reveal-honest-1.json
python3.12 -m dogwhistle.listener audit
python3.12 -m analysis.vis1_exploratory
python3.12 prior_work/verify_snapshot.py
```

On the merged PR #6 code, pytest reports **28 passed, 4 skipped**. The four original lifecycle-test entries are skipped and rerun unchanged from a recreated pre-prepare checkout; see [test maintenance](listener/MAINTENANCE.md). These commands make no model calls. Each results report states its design and limits.

## Scope

The tested carrier is the choice of two ordered `required_memory_refs` from four vendor refs. Selecting those refs from public task data removes sender-dependent bits through that field; it does not establish that every handoff channel is closed. The allocation matrices are synthetic, and the receiver sees the public matrix.

DogWhistle was developed for the [Apart AI Collusion Research Sprint's Carriers and Countermeasures track](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25). The pre-sprint Neural Node Swarm studies are preserved as prior work, with their original chronology intact.
