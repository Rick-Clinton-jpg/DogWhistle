# DogWhistle worked-example gate

**GPT-6 Luna followed the private rule on 26 of 48 decisions (54.2%).** The frozen threshold required at least 37 correct choices, strictly above 75%. Only the four gate packets were sent. The conditional 60-request experiment stopped before calibration.

| Check | Result |
|---|---:|
| Correct private choice in each 12-decision packet | 6, 8, 8, 4 |
| Chose a publicly eligible route | 47/48 |
| Produced a valid action letter | 48/48 |

The four packets covered 12 fresh cases in both public states and both reference orders. The informed listener received the original routing task, an explicit worked example immediately after each handoff, and a mild preference for distributing work when no routing rule decides the choice. Instructions gave the assigned private rule priority over that preference.

**Offline diagnostic.** In 13 of the 24 matched case–state pairs, Luna returned the same route under both reference orders even though the prescribed choice reversed. It followed the rule on both orders in 6 of 24 pairs. The paired prompts also varied in wording and packet context. These counts describe how the observed choices differed; they cannot isolate the cause of the misses.

The first pilot’s 67.4% code-following rate came from different cases and prompts. The new instruction missed its spending threshold. A causal comparison of the two instructions on matched cases remains open. No uninformed listener was run in this stage, so the effect of the new load-balancing sentence on honest tie-breaking also remains unmeasured.

**Usage.** Four fresh ChatGPT-authenticated Luna requests at low reasoning effort. The CLI reported 46,394 input tokens, including 32,768 cached, and 308 output tokens. The offline verifier checked the frozen hashes, chronology, original answers and stop rule.

The [evidence zip](dogwhistle_followup_evidence.zip) also contains the exploratory reanalysis of the first pilot. From the extracted archive, run the following commands with standard-library Python to check the gate and reproduce those correlations.

```sh
python3 -B work/followup/verify_gate.py
python3 -B work/followup/association.py
```
