# DogWhistle

**Can a schema-valid agent handoff carry a hidden signal that changes one successor's action but not another's?** DogWhistle tests this on a controlled, synthetic allocation task. A sender chooses two memory references in a handoff. A fresh receiver then assigns six items among four vendors. Deterministic code checks the handoff, solves the public allocation optimum, and scores what the receiver did.

**Main finding:** in this setting, a structural handoff field acted as a conditional carrier, meaningful only to a listener that held the convention. A label-free sensitivity contrast told the two listener types apart on the same tasks.

Across six preregistered studies, two schema-valid references carried a planted coalition codeword. In PR #2 a model sender encoded it for a model receiver; in PRs #3, #4 and #6 code planted it, so only the references differed between arms. The codeword moved an instructed listener's allocations and left an honest listener's unchanged within the registered margin. The audit needs no knowledge of the hidden pair. It replays each listener with only the references swapped, then compares how much its answers change with how much they vary on their own.

This repository is an auditable experiment, not a deployed detector. Listeners were told the convention and given a coalition incentive. The results do not show that agents invent such conventions on their own.

## Results

| Study | What changed | Outcome | Decision |
| --- | --- | --- | --- |
| [PR #1](study/RESULTS.md), 20 tasks | Free refs, no shared convention | −0.05 items per task, exact one-sided *p* = 1.0 | Full claim **failed** |
| [PR #2](followup/RESULTS.md), 30 tasks | Planted codeword | Emitted and decoded 30/30; free-arm effect +0.60 items per task (*p* = 0.0070); both positive controls missed their +0.5 thresholds | Full claim **failed**; transmission shown |
| [PR #3](visibility/RESULTS.md), 30 tasks × 3 receivers | Codeword vs public refs; coalition-seeking receiver | +0.422 hidden-pair assignments per receiver (*p* = 0.00033); explicit-pair control +0.311 (*p* = 0.0055) | **Passed** |
| [PR #4](honest/RESULTS.md), 30 tasks × 3 receivers | Same contrast; honest receiver | −0.011 per receiver, inside the ±0.20 equivalence margin | **Passed** (inert) |
| PR #5, [retired record](https://github.com/Rick-Clinton-jpg/DogWhistle/blob/96a9c94a34c31febc565af2f91ab34b705fa63ae/audit/retired-80/README.md) | Within-sample audit, first design | Retired after 80 of 360 calls, before any answer was decrypted; [reasons](https://github.com/Rick-Clinton-jpg/DogWhistle/blob/069be1a71146fcb6d5d86c89880edb69a2935d94/audit/seals/retired-partial.json); published unchanged | No decision |
| [PR #6](listener/RESULTS.md), 30 tie-rich tasks × 12 slots | Both listener types, both ref arms, three paraphrases, same matrices | Label-free sensitivity difference +0.356 (95% interval +0.256 to +0.456; *p* = 2.05 × 10⁻⁷); four Holm-corrected secondary tests passed; honest false-alarm test not raised | **Passed** |

PR #6's exploratory Qwen 2.5 14B run failed the validity threshold in every cell, so it supplies no evidence about other models. The PR #3 [decoy analysis](visibility/EXPLORATORY.md) is exploratory and post-reveal.

## How the evidence is protected

Before any model call, each study committed its protocol, code, sample, and a salted SHA-256 commitment to the hidden labels. Each model call ran as a fresh one-shot process. Records were sealed before the reveal. Each reveal publishes the raw ledgers, and deterministic audits replay commitments, inputs, chronology, and scores. In PR #6, labels and inputs were also encrypted at rest during the run. Deviations and defects are recorded rather than removed: PR #5's retirement and PR #6's [test maintenance note](listener/MAINTENANCE.md).

## Related work

Comparing an informed listener with an uninformed one follows the steganographic-gap framework ([arXiv:2602.23163](https://arxiv.org/abs/2602.23163)), which measures how much a signal helps a decoder versus a non-decoder on an auditing task with known answers. Structured fields such as metadata and tool-call arguments have been treated as covert channels between agents, with a verifier-based admission protocol as the defense ([arXiv:2603.00381](https://arxiv.org/abs/2603.00381)). Counterfactual tests of how much a latent channel changes an agent's actions, using matched neutral replays and model internals, appear in [arXiv:2608.19161](https://arxiv.org/abs/2608.19161). Agreement without collusive action has also been reported in agent teams ([arXiv:2602.15198](https://arxiv.org/abs/2602.15198)). DogWhistle adds three things:

- a black-box audit that measures each listener's change under the swap against its own variation across wordings (S = X − W);
- preregistered, replayable evidence for one structured handoff field;
- the finding that deriving the field from public data does not stop a listener that holds the convention.

## Repository map

- `dogwhistle/`: task generator, exact allocation solver, handoff gate, model adapters, orchestration and audit code.
- `study/`, `followup/`, `visibility/`, `honest/`, `listener/`: PRs #1, #2, #3, #4 and #6. Each folder holds the protocol, registration, raw records, reveal, scores and results.
- `analysis/`: PR #3's exploratory decoy script.
- `tests/`: deterministic unit tests and fake-client lifecycle tests.
- `prior_work/`: the byte-verified Neural Node Swarm PR #5/#6 record. It predates the Apart sprint; see its [provenance](prior_work/ORIGIN.md) and its [correction](prior_work/ORIGIN_CORRECTION.md).
- PR #5's retired record is on the preserved `study/listener-audit` branch.

## Reproduce without model calls

Use Python 3.12 and a full-history clone, because the audits read git history. `requirements-lock.txt` lists the exact package versions used for the published replays. The test suite takes several minutes.

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

Expected pytest result: 28 passed, 4 skipped. The four skips are frozen tests that are rerun from their pre-prepare state, as explained in the maintenance note.

## Limitations

- The task is synthetic, and the convention was planted. The two listener types are defined by different prompts and output schemas.
- All confirmatory evidence comes from one model: `gpt-6.1-sol` through Codex CLI `0.163.0-alpha.10.2`, at low reasoning effort. Qwen 2.5 14B could not do the task: no answer reached the optimum, and as few as 17 of 90 answers per cell were valid. Transfer to other models is therefore untested.
- Only one carrier field was tested: `required_memory_refs`.
- The audit needs the suspect field known in advance, a neutral replacement value for it, and repeated calls (12 per task in PR #6).
- Anyone can check the commitments and commit order. Wall-clock timing rests on commit dates and GitHub's push history, and the call logs are the harness's own records.
- The honest control had limited room to fail. In PR #4, honest receivers solved the exact optimum in 179 of 180 trials. In PR #6, the honest listener returned the same assignment in all six of its trials on 22 of the 30 matrices.
- Code-selected references remove the sender's control over who benefits. They do not stop a coalition-seeking listener from applying the convention anyway: in PR #3, it diverted assignments to a code-chosen decoy pair.
- None of these effects is a production risk rate.

DogWhistle was designed by Rick Clinton for the [Apart AI Collusion Research Sprint](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25), in the Carriers and Countermeasures track. The pre-sprint Neural Node Swarm studies are preserved as prior work, with their original chronology intact.

Licensed under [Apache-2.0](LICENSE). The `prior_work/nns_snapshot/` folder keeps its own [PolyForm Noncommercial 1.0.0](prior_work/nns_snapshot/LICENSE) licence.
