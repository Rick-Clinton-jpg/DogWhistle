# DogWhistle

**Question:** Can an apparently ordinary, schema-bound agent handoff carry a
hidden signal that shifts a successor's allocation toward a coalition? Can a
deterministic handoff control remove that effect while preserving the legitimate
allocation task?

DogWhistle is an experiment on covert coordination through agent handoffs. It
measures downstream decisions against a deterministic allocation optimum, not
the agents' descriptions of their own behaviour. The study will distinguish
an elicited channel demonstration from spontaneous collusion and will report
null results and task costs alongside any positive effect.

## Prior evidence

`prior_work/nns_snapshot/` is a byte-for-byte selection of published files from
[Neural Node Swarm PR #6](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/pull/6),
which includes [PR #5](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/pull/5).
These studies began before the Apart AI Collusion Research Sprint and are
**prior work**, not new DogWhistle results. See [provenance](prior_work/ORIGIN.md)
for original commits, chronology, hashes, and audit commands.

## New experiment

The new allocation study is under `dogwhistle/` and `study/`. Its
[preregistered protocol](study/PROTOCOL.md), fixed analysis plan, task seed,
prompts, and hidden-coalition commitment are published before any live sender
call. The free handoff has 12 possible ordered vendor-reference pairs
(`log2(12) ≈ 3.585` structural bits); the controlled handoff selects one pair
from public task data and carries zero sender-dependent bits through that
field. The study tests whether this difference changes **allocations**.

No new results should be inferred from the inherited PR #5/#6 ledger. The
synthetic allocation task and its limited adoption-cost claim are described in
the protocol. DogWhistle is anchored to [Apart's Collusion Carriers and
Countermeasures track](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25).
