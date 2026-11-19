# DogWhistle in the PoPLi setting

We applied DogWhistle’s score to the pricing decisions Kevin Yandoka Denamganaï released with PoPLi. [Paper, arXiv 2610.37849](https://arxiv.org/abs/2610.37849)

The PoPLi archive is available under the MIT licence. [Pinned revision `039b6b7268b0a1ac4a82e89c52e4f123cad5cf58`](https://github.com/Near32/PartnerOutsiderPositiveListening/tree/039b6b7268b0a1ac4a82e89c52e4f123cad5cf58) · [Licence](https://github.com/Near32/PartnerOutsiderPositiveListening/blob/039b6b7268b0a1ac4a82e89c52e4f123cad5cf58/LICENSE)

For each listener, DogWhistle subtracts the average disagreement within each message version from the disagreement between replies to the original and reworded messages. It subtracts the outsider’s score from the partner’s score, averages turns within each market, then weights the ten markets in each condition equally. The second outsider (C0′) also receives its own last asking price.

| DogWhistle comparison | Mean gap with code | Mean gap without code |
|---|---:|---:|
| Partner and outsider C0 | +0.560 | −0.037 |
| Partner and second outsider C0′ | +0.547 | −0.024 |

DogWhistle’s adapted score was higher with the code present in both comparisons, in agreement with PoPLi’s published result. This retrospective application used saved decisions and made no new model calls.

## Reproduce the DogWhistle scores

The [evidence zip](dogwhistle_popli_reanalysis.zip) contains the [scorer](score_saved_decisions.py) and [expected scores](scores.csv). From this directory or the extracted zip, use a temporary directory outside the repository. The first invocation downloads the two pinned inputs and saves them only if their SHA-256 digests match the values recorded by the DogWhistle scorer. The final command reproduces the scores offline from that cache.

```sh
cache=$(mktemp -d)
python3 -B score_saved_decisions.py --fetch "$cache"
python3 -B score_saved_decisions.py "$cache"
```

From the extracted zip, `python3 -B archived_score.py "$cache"` also reproduces the archived DogWhistle gaps and their 95% market bootstrap intervals (20,000 resamples, seed 20261118).
