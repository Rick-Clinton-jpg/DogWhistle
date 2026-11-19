# Does DogWhistle’s score rise with code-following?

On the first GPT-6 Luna pilot’s saved decisions, cases with higher code adherence generally scored higher. The association was strong when the two measures used the same answers. When they used disjoint answers, the relationship was weak. This post hoc analysis uses all 12 held-out cases and both public states, with zero new model requests.

| Comparison | Observations | Pearson r | Spearman ρ |
|---|---:|---:|---:|
| Case means across both public states | 12 | 0.771 | 0.673 |
| Case and public-state combinations | 24 | 0.784 | 0.851 |
| Public state 0 alone | 12 | 0.678 | 0.454 |
| Public state 1 alone | 12 | 0.949 | 0.937 |
| Adherence in one state, gap in the other state of the same case, both directions | 24 | −0.053 | −0.080 |

**What the association measures.** Adherence is the fraction of the informed listener’s choices matching the assigned convention. Each case-state has six choices, from two reference orders crossed with three prompt wordings. The primary audit gap subtracts the second uninformed listener’s sensitivity from the informed listener’s sensitivity. The uninformed listener’s score was exactly zero in all 24 case-states, so the correlations also describe the informed listener’s sensitivity alone. Both variables use the same six informed choices in each of the first four rows. At the case level they share all twelve.

**Checks with disjoint answers.** Using state 0 adherence and state 1’s audit gap gave rank correlation −0.065. Reversing the states gave +0.122. As a second check within the same public state, we measured adherence from one wording’s two answers and calculated a reduced gap from the other two wordings’ four answers. The three wording splits gave rank correlations of −0.084, −0.101 and +0.060. These checks have few answers per estimate. Cross-state comparisons can also lose a real effect specific to one state.

**Interpretation.** The score tracked observed code use descriptively on the original answers. Those two summaries can rise together by construction: changing the action in the prescribed direction helps both. Reversing the convention consistently could also produce a high sensitivity score with low prescribed adherence, because DogWhistle measures action change in either direction. The results therefore do not establish a proportional relationship or predict adherence on other decisions.

Case-state rows share cases, all cases share response packets, and the analysis was chosen after the primary results were known. Correlations are descriptive. Spearman correlations use average ranks for exact ties. Each case and state received the same weight. [Case-level values](active_listener_association_cases.csv) · [Case-by-state values](active_listener_association_public_states.csv)

## Reproduce offline

Extract the [shared gate and association evidence zip](../worked-example-gate/dogwhistle_followup_evidence.zip). From the extracted directory, regenerate the tables and correlations from the saved Luna choices.

```sh
python3 -B work/followup/association.py
```
