"""Verification suite for evalstats.py.

Three kinds of check, labelled in the output:
  [PAPER] reproduces a worked example or claim from a cited paper
  [INDEP] matches an implementation Claude did not write (scipy, statsmodels, scikit-learn,
          MLstatkit, ppi_py). Skipped, not failed, if that library is missing.
  [SIM]   Monte Carlo check of coverage or error rate against a known truth
Run:  python test_evalstats.py   (from this folder)
"""
import os
import sys
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evalstats as es

results = []


def check(kind, name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append((kind, name, status, str(detail)))
    print(f"{status} [{kind}] {name}" + (f"  ({detail})" if detail != "" else ""))


def skip(kind, name, why):
    results.append((kind, name, "SKIP", why))
    print(f"SKIP [{kind}] {name}  ({why})")


def have(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


rng = np.random.default_rng(1)

# ------------------------------------------------------------------ core [M]
check("PAPER", "Miller sec5: n=969 for delta=.03, w2=1/9", es.n_required(0.03, 1/9) == 969, es.n_required(0.03, 1/9))
m1, m10 = es.mde(198, 1/9, 1/6, 1/6, 1, 1), es.mde(198, 1/9, 1/6, 1/6, 10, 10)
check("PAPER", "Miller sec5: MDE 13.2% (K=1) / 7.5% (K=10), paper truncates", abs(m1 - .132) < .002 and abs(m10 - .075) < .002,
      f"{m1:.4f} / {m10:.4f}")
for K, red in [(2, 1/3), (4, 1/2), (6, 5/9)]:
    ratio = (1/12 + 1/(6*K)) / (1/12 + 1/6)
    check("PAPER", f"Miller sec3.1: K={K} cuts variance by {red:.3f}", abs((1 - ratio) - red) < 1e-12)
check("PAPER", "Miller sec4.2 inconsistency: corr .5 gives 1/12 (paper prints 1/9)", abs((1/6 - 2*.5/12) - 1/12) < 1e-12)

x = rng.uniform(size=2000)
sa, sb = x + rng.normal(0, .2, 2000), x + rng.normal(0, .2, 2000)
direct = es.compare_paired(sa, sb)["se"]
via = es.se_paired_from_corr(es.se_clt(sa), es.se_clt(sb), np.corrcoef(sa, sb)[0, 1])
check("PAPER", "Miller: paired SE direct == via correlation", abs(direct - via) / direct < 1e-3)
s01 = rng.binomial(1, .6, 500).astype(float)
check("PAPER", "Miller Eq.4 with singleton clusters == Eq.1", abs(es.se_clustered(s01, np.arange(500)) - es.se_clt(s01)) < 1e-12)

cov_cl = cov_nv = 0
for r in range(1000):
    th = rng.beta(2, 2, 100)
    sc = rng.binomial(1, np.repeat(th, 10)).astype(float)
    cl = np.repeat(np.arange(100), 10)
    lo, hi = es.ci_normal(sc.mean(), es.se_clustered(sc, cl)); cov_cl += lo <= .5 <= hi
    lo, hi = es.ci_normal(sc.mean(), es.se_clt(sc)); cov_nv += lo <= .5 <= hi
check("SIM", "Clustered 95% CI covers truth ~95% (100 clusters x 10)", .92 <= cov_cl/1000 <= .97, f"{cov_cl/1000:.3f}")
check("SIM", "Naive 95% CI under-covers on clustered data", cov_nv/1000 < .85, f"{cov_nv/1000:.3f}")

nq, K = 3000, 40
xa = rng.uniform(size=nq); xb = np.clip(xa + rng.normal(0, .15, nq), 0, 1)
A = rng.binomial(1, xa[:, None], (nq, K)); B = rng.binomial(1, xb[:, None], (nq, K))
vc = es.variance_components(A, B)
check("SIM", "Variance components recover sigma_A^2", abs(vc["sigma2_a"] - np.mean(xa*(1-xa))) < .01, f"{vc['sigma2_a']:.4f}")

# ------------------------------------------------------------------ small-sample [B]
for S_, N_ in [(0, 20), (7, 20), (20, 20), (13, 15)]:
    w = es.wilson_ci(S_, N_); ref = stats.binomtest(S_, N_).proportion_ci(0.95, method="wilson")
    check("INDEP", f"Wilson == scipy (S={S_}, N={N_})", abs(w[0]-ref.low) < 1e-9 and abs(w[1]-ref.high) < 1e-9)
mx = max(abs(float(es._bvn_cdf(np.array(h), np.array(k), np.array(rho))) -
             stats.multivariate_normal([0, 0], [[1, rho], [rho, 1]]).cdf([h, k]))
         for h, k, rho in [(.3, -.5, .4), (-1.2, -.7, .9), (1.5, 2, -.6), (0, .8, .5), (.4, 0, -.3), (-2, 1, .1)])
check("INDEP", "Bivariate normal CDF == scipy", mx < 1e-5, f"max err {mx:.1e}")
cw = cc = 0
for r in range(4000):
    th = rng.uniform(); y = rng.binomial(1, th, 20)
    lo, hi = es.wilson_ci(y.sum(), 20); cw += lo <= th <= hi
    lo, hi = es.ci_normal(y.mean(), es.se_bernoulli(y.mean(), 20)); cc += lo <= th <= hi
check("SIM", "Bowyer: Wilson ~95% coverage at N=20", .93 <= cw/4000 <= .97, f"{cw/4000:.3f}")
check("SIM", "Bowyer: CLT under-covers at N=20", cc/4000 < .93, f"{cc/4000:.3f}")
pr = es.bayes_paired_diff(np.array([1]*16 + [0]*4), np.array([1]*8 + [0]*12))
check("SIM", "Paired Bayes: CI excludes 0 when A wins 8/8 discordant", pr["diff_ci"][0] > 0, pr["diff_ci"])
v = rng.normal(3, 1, 12)
check("INDEP", "t-interval == scipy", np.allclose(es.t_ci(v), stats.t.interval(.95, 11, loc=v.mean(), scale=stats.sem(v))))

# ------------------------------------------------------------------ paired module
ya = rng.binomial(1, .7, 80); yb = np.where(rng.uniform(size=80) < .8, ya, 1 - ya)
mc = es.mcnemar_exact(ya, yb)
if have("statsmodels"):
    from statsmodels.stats.contingency_tables import mcnemar
    tab = [[int(((ya == 1) & (yb == 1)).sum()), mc["a_only"]], [mc["b_only"], int(((ya == 0) & (yb == 0)).sum())]]
    ref = mcnemar(tab, exact=True).pvalue
    check("INDEP", "McNemar exact == statsmodels", abs(mc["p"] - ref) < 1e-12, f"{mc['p']:.5f} vs {ref:.5f}")
else:
    skip("INDEP", "McNemar exact == statsmodels", "statsmodels missing")

d = rng.normal(.3, 1, 12)
sf = es.sign_flip_test(d)
ref = stats.permutation_test((d,), lambda z: np.mean(z), permutation_type="samples", n_resamples=np.inf,
                             alternative="two-sided").pvalue
check("INDEP", "Sign-flip exact (n=12) == scipy permutation_test", abs(sf["p"] - ref) < 1e-9, f"{sf['p']:.5f} vs {ref:.5f}")
d40 = rng.normal(.4, 1, 40)
sf40 = es.sign_flip_test(d40, n_resamples=200000)
ref40 = stats.permutation_test((d40,), lambda z: np.mean(z), permutation_type="samples", n_resamples=200000,
                               alternative="two-sided", random_state=3).pvalue
check("INDEP", "Sign-flip Monte Carlo (n=40) ~ scipy", abs(sf40["p"] - ref40) < .01, f"{sf40['p']:.4f} vs {ref40:.4f}")
rej = 0
for r in range(3000):
    rej += es.sign_flip_test(rng.standard_t(3, 10))["p"] < .05
check("SIM", "Sign-flip false-positive rate ~5% under null (n=10, heavy tails)", rej/3000 <= .06, f"{rej/3000:.3f}")

# ------------------------------------------------------------------ power / resolution [K]
check("PAPER", "Kotawala Eq.5 with rho=0 == unpaired variance",
      abs(es.paired_binary_variance(.6, .5, 0) - (.24 + .25)) < 1e-12)
res = es.resolution(gap=.03, sd_diff=np.sqrt(1/9), n=969)
check("PAPER", "Resolution q ~1 at Miller's own n=969 example", abs(res["q"] - 1) < .002 and abs(res["mde"] - .03) < 1e-4,
      f"q={res['q']:.4f}, mde={res['mde']:.4f}")
check("PAPER", "Kotawala: q>=1 iff |T| >= 2.80", abs((stats.norm.ppf(.975) + stats.norm.ppf(.8)) - 2.8016) < 1e-3)

# ------------------------------------------------------------------ clusters
de = es.design_effect(np.repeat(rng.binomial(1, .5, 50), 10).astype(float), np.repeat(np.arange(50), 10))
check("SIM", "Perfectly correlated clusters of 10 -> design effect ~10", 8.5 < de["design_effect"] < 10.5, f"{de['design_effect']:.2f}")

# ------------------------------------------------------------------ multiple comparisons
pv = np.array([.001, .008, .039, .041, .042, .06, .074, .205, .212, .216])
if have("statsmodels"):
    from statsmodels.stats.multitest import multipletests
    for meth, fn in [("holm", es.holm), ("fdr_bh", es.benjamini_hochberg)]:
        rj, padj, _, _ = multipletests(pv, alpha=.05, method=meth)
        ours = fn(pv)
        check("INDEP", f"{meth} == statsmodels (adjusted p and decisions)", np.allclose(ours["p_adj"], padj) and
              (ours["reject"] == rj).all())
    pv2 = rng.uniform(size=37)
    for meth, fn in [("holm", es.holm), ("fdr_bh", es.benjamini_hochberg)]:
        check("INDEP", f"{meth} == statsmodels on 37 random p-values", np.allclose(fn(pv2)["p_adj"], multipletests(pv2, method=meth)[1]))
else:
    skip("INDEP", "Holm/BH == statsmodels", "statsmodels missing")
fwer = 0
for r in range(2000):
    fwer += es.holm(rng.uniform(size=10))["reject"].any()
check("SIM", "Holm family-wise error <= 5% with 10 true nulls", fwer/2000 <= .06, f"{fwer/2000:.3f}")

# ------------------------------------------------------------------ AUC [DL]
lab = np.r_[np.ones(60), np.zeros(90)].astype(int)
sc_a = np.r_[rng.normal(1, 1, 60), rng.normal(0, 1, 90)]
sc_b = sc_a + rng.normal(0, .8, 150)
ad = es.auc_delong(sc_a, lab)
if have("sklearn"):
    from sklearn.metrics import roc_auc_score
    check("INDEP", "AUC point estimate == scikit-learn", abs(ad["auc"] - roc_auc_score(lab, sc_a)) < 1e-12)
else:
    skip("INDEP", "AUC == scikit-learn", "sklearn missing")
if have("MLstatkit"):
    from MLstatkit import Delong_test
    z_ref, p_ref, ci_a_ref, ci_b_ref, auc_a_ref, auc_b_ref, info = Delong_test(lab, sc_a, sc_b, alpha=.95)
    cmp_ = es.delong_compare(sc_a, sc_b, lab)
    check("INDEP", "DeLong comparison p-value == MLstatkit", abs(cmp_["p"] - p_ref) < 1e-6 and info["method"] == "delong",
          f"{cmp_['p']:.6f} vs {p_ref:.6f}")
    check("INDEP", "DeLong variance of AUC difference == MLstatkit", abs(cmp_["se"] ** 2 - info["var_diff"]) < 1e-9)
    check("INDEP", "DeLong single-AUC CI == MLstatkit", np.allclose(ad["ci"], ci_a_ref, atol=1e-6), f"{ad['ci']} vs {ci_a_ref}")
else:
    skip("INDEP", "DeLong == MLstatkit", "MLstatkit missing")
covd = 0
for r in range(1000):
    s = np.r_[rng.normal(1, 1, 100), rng.normal(0, 1, 100)]
    lo, hi = es.auc_delong(s, np.r_[np.ones(100), np.zeros(100)].astype(int))["ci"]
    covd += lo <= stats.norm.cdf(1 / np.sqrt(2)) <= hi
check("SIM", "DeLong 95% CI coverage ~95% at 100+100", .93 <= covd/1000 <= .97, f"{covd/1000:.3f}")
inv = es.auc_delong(-sc_a, lab)
check("SIM", "Inverted scores are flagged", inv["flag"] is not None and inv["flag"].startswith("INVERTED"), inv["flag"])

# ------------------------------------------------------------------ zero failures [CP]
up = es.failure_rate_upper(0, 10)
check("PAPER", "0 failures in 10: upper bound = 1 - 0.05^(1/10) = 25.9%", abs(up - (1 - .05 ** .1)) < 1e-12, f"{up:.4f}")
check("PAPER", "Rule of three: 0 in 300 -> about 1%", abs(es.failure_rate_upper(0, 300) - 3/300) < .0005)
if have("statsmodels"):
    from statsmodels.stats.proportion import proportion_confint
    ok = all(abs(es.failure_rate_upper(k, n) - proportion_confint(k, n, alpha=.10, method="beta")[1]) < 1e-9
             for k, n in [(0, 10), (1, 20), (3, 50), (0, 300)])
    check("INDEP", "One-sided 95% bound == statsmodels Clopper-Pearson (two-sided 90%) upper", ok)
else:
    skip("INDEP", "Clopper-Pearson == statsmodels", "statsmodels missing")
check("PAPER", "Runs needed for <=5% failure rate with 0 failures = 59", es.runs_needed(.05) == 59, es.runs_needed(.05))

# ------------------------------------------------------------------ equivalence [TOST]
xa_, xb_ = rng.normal(10, 2, 30), rng.normal(10.1, 2, 30)
t = es.tost_paired(xa_ - xb_, -1, 1)
if have("statsmodels"):
    from statsmodels.stats.weightstats import ttost_paired
    ref = ttost_paired(xa_, xb_, -1, 1)[0]
    check("INDEP", "TOST paired == statsmodels ttost_paired", abs(t["p_tost"] - ref) < 1e-9, f"{t['p_tost']:.6f} vs {ref:.6f}")
else:
    skip("INDEP", "TOST == statsmodels", "statsmodels missing")
check("SIM", "TOST verdict matches 90% CI inside bounds", t["equivalent"] == (-1 < t["ci_90"][0] and t["ci_90"][1] < 1))

# ------------------------------------------------------------------ judge [PPI, LEE]
n_lab, n_unl = 150, 3000
truth = rng.binomial(1, .62, n_lab + n_unl)
judge = np.where(truth == 1, rng.binomial(1, .9, n_lab + n_unl), rng.binomial(1, .25, n_lab + n_unl))
pp = es.ppi_mean(truth[:n_lab], judge[:n_lab], judge[n_lab:])
if have("ppi_py"):
    from ppi_py import ppi_mean_ci, ppi_mean_pointestimate
    ref_ci = ppi_mean_ci(truth[:n_lab].astype(float), judge[:n_lab].astype(float), judge[n_lab:].astype(float), alpha=.05, lam=1)
    ref_pt = ppi_mean_pointestimate(truth[:n_lab].astype(float), judge[:n_lab].astype(float), judge[n_lab:].astype(float), lam=1)
    check("INDEP", "PPI point estimate == ppi_py (lam=1)", abs(pp["theta"] - float(np.ravel(ref_pt)[0])) < 1e-9)
    check("INDEP", "PPI CI == ppi_py (lam=1)", abs(pp["ci"][0] - float(np.ravel(ref_ci[0])[0])) < 2e-3 and
          abs(pp["ci"][1] - float(np.ravel(ref_ci[1])[0])) < 2e-3, f"{pp['ci']} vs {ref_ci}")
else:
    skip("INDEP", "PPI == ppi_py", "ppi_py missing")
er = es.judge_error_rates(truth[:n_lab], judge[:n_lab])
rg = es.rogan_gladen(judge.mean(), .75, .9)
check("PAPER", "Rogan-Gladen with true q0=.75, q1=.9 recovers ~.62 from a biased judge", abs(rg - .62) < .03,
      f"naive judge {judge.mean():.3f} -> corrected {rg:.3f}")
covp = 0
for r in range(500):
    tr = rng.binomial(1, .62, 2150)
    jd = np.where(tr == 1, rng.binomial(1, .9, 2150), rng.binomial(1, .25, 2150))
    lo, hi = es.ppi_mean(tr[:150], jd[:150], jd[150:])["ci"]; covp += lo <= .62 <= hi
check("SIM", "PPI 95% CI covers the true rate ~95%", .92 <= covp/500 <= .98, f"{covp/500:.3f}")

# ------------------------------------------------------------------ prompts [MZ]
mp = es.multiprompt(np.array([[1, 1, 0, 1], [1, 0, 0, 1], [1, 1, 1, 1]]))
check("PAPER", "CPS = (1-(MaxP-AvgP))*MaxP", abs(mp["cps"] - (1 - (1.0 - 0.75)) * 1.0) < 1e-12, mp["cps"])
rs = es.rank_stability(np.array([[.9, .8, .7], [.5, .6, .4], [.1, .2, .3]]))
check("SIM", "Rank stability: identical rankings -> tau 1", abs(rs["mean_tau"] - 1) < 1e-12)

# ------------------------------------------------------------------ repeats [W, PK]
xi = rng.uniform(size=400)
S = rng.binomial(1, xi[:, None], (400, 30))
nc = es.noise_components(S)
check("SIM", "Noise split: prediction var ~ E[x(1-x)] = 1/6", abs(nc["pred_var"] - np.mean(xi*(1-xi))) < .01, f"{nc['pred_var']:.4f}")
check("SIM", "Noise split: data var ~ Var(x) = 1/12", abs(nc["data_var"] - np.var(xi)) < .015, f"{nc['data_var']:.4f}")
from itertools import combinations
from math import comb
ok = True
for n_, c_, k_ in [(10, 3, 1), (10, 3, 5), (8, 0, 2), (8, 8, 2), (12, 5, 4)]:
    brute = 1 - comb(n_ - c_, k_) / comb(n_, k_)
    ok &= abs(es.pass_at_k([n_], [c_], k_)["pass_at_k"] - brute) < 1e-12
check("INDEP", "pass@k estimator == direct combinatorial formula (Chen et al.)", ok)

# ------------------------------------------------------------------ sequential [SAVI]
false_stop = 0
for r in range(2000):
    a_ = rng.binomial(1, .6, 300); b_ = rng.binomial(1, .6, 300)
    false_stop += es.sequential_paired_binary(a_, b_)["reject"]
check("SIM", "Anytime-valid test: false stops <= 5% with peeking after every unit", false_stop/2000 <= .05,
      f"{false_stop/2000:.4f}")
naive_stop = 0
for r in range(1000):
    a_ = rng.binomial(1, .6, 300); b_ = rng.binomial(1, .6, 300)
    for t_ in range(20, 301, 10):
        if es.mcnemar_exact(a_[:t_], b_[:t_])["p"] < .05:
            naive_stop += 1
            break
check("SIM", "Contrast: naive peeking with McNemar inflates false stops above 5%", naive_stop/1000 > .08, f"{naive_stop/1000:.3f}")
power_hits = sum(es.sequential_paired_binary(rng.binomial(1, .8, 300), rng.binomial(1, .5, 300))["reject"] for _ in range(300))
check("SIM", "Anytime-valid test still detects a real 30-point gap", power_hits/300 > .9, f"{power_hits/300:.3f}")

# ------------------------------------------------------------------ SNR [SN]
sn = es.signal_to_noise([.50, .60, .70], [.60, .61, .59, .60])
check("PAPER", "SNR = (max gap / mean) / (rel. std)", abs(sn["snr"] - ((.2/.6) / (np.std([.6, .61, .59, .6], ddof=1)/.6))) < 1e-12)

# ------------------------------------------------------------------ summary
n_pass = sum(r[2] == "PASS" for r in results)
n_fail = sum(r[2] == "FAIL" for r in results)
n_skip = sum(r[2] == "SKIP" for r in results)
print(f"\n{n_pass} passed, {n_fail} failed, {n_skip} skipped")
if "--markdown" in sys.argv:
    with open(sys.argv[sys.argv.index("--markdown") + 1], "w") as fh:
        fh.write("| Kind | Check | Result | Detail |\n|---|---|---|---|\n")
        for kind, name, status, detail in results:
            fh.write(f"| {kind} | {name} | {status} | {detail.replace('|', '/')} |\n")
sys.exit(1 if n_fail else 0)
