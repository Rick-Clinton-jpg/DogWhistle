"""evalstats: reference implementation for EVAL mode.

Every function is tagged with its source. Tags:
  [M]    Miller (2024) Adding Error Bars to Evals, arXiv:2411.00640
  [B]    Bowyer, Aitchison, Ivanova (2025) Don't Use the CLT..., ICML 2025, arXiv:2503.01747
  [K]    Kotawala (2026) Resolution Diagnostics for Paired LLM Evaluation, arXiv:2605.30315
  [EC]   Chandrahas (2026) evalci, arXiv:2607.04429 (McNemar, sign-flip permutation, Holm/BH)
  [HOLM] Holm (1979); [BH] Benjamini & Hochberg (1995)
  [DL]   DeLong, DeLong & Clarke-Pearson (1988); fast midrank form: Sun & Xu (2014)
  [KV]   Kampf et al. (2025) AUC interval coverage, Modern Stochastics: Theory and Applications
  [CP]   Clopper & Pearson (1934); rule of three: Hanley & Lippman-Hand (1983)
  [TOST] Schuirmann (1987); Lakens (2017)
  [LEE]  Lee et al. (2026) How to Correctly Report LLM-as-a-Judge Evaluations, arXiv:2511.21140
  [PPI]  Angelopoulos et al. (2023) Prediction-Powered Inference, arXiv:2301.09633
  [CH]   Chen et al. (2026) Efficient Inference for Noisy LLM-as-a-Judge Evaluation, arXiv:2601.05420
  [MZ]   Mizrahi et al. (2024) State of What Art? Multi-Prompt LLM Evaluation, TACL
  [W]    Wang (2025) Measuring all the noises of LLM Evals, arXiv:2512.21326
  [PK]   Chen et al. (2021) Evaluating LLMs Trained on Code (unbiased pass@k), arXiv:2107.03374
  [SAVI] Ramdas, Grunwald, Vovk, Shafer (2023) Game-theoretic statistics and safe
         anytime-valid inference, Statistical Science
  [SN]   Heineman et al. (2025) Signal and Noise, arXiv:2508.13144
  [EXT]  not from a cited source (standard statistics or a derivation); flag it when used.
Requires: numpy, scipy.
"""
import numpy as np
from scipy import stats, special


def _z(p):
    """z_p = (1-p)th percentile of the standard normal (Miller's notation)."""
    return stats.norm.ppf(1 - p)


# ---------------------------------------------------------------- [M] single model
def se_clt(s):
    """[M] Eq.1  SE = sqrt( (1/(n-1)) * sum (s_i - s_bar)^2 / n ). Any finite-variance score."""
    s = np.asarray(s, float)
    return float(np.sqrt(np.var(s, ddof=1) / len(s)))


def se_bernoulli(p_hat, n):
    """[M] Eq.2  SE = sqrt(p(1-p)/n). ONLY valid when every score is 0 or 1."""
    return float(np.sqrt(p_hat * (1 - p_hat) / n))


def ci_normal(est, se, alpha=0.05):
    """[M] Eq.3/5  est +/- z_{alpha/2} * SE  (1.96 for 95%)."""
    h = _z(alpha / 2) * se
    return (est - h, est + h)


def se_clustered(s, clusters):
    """[M] Eq.4  SE^2 = SE_CLT^2 + (1/n^2) sum_c sum_i sum_{j!=i} (s_ic - s_bar)(s_jc - s_bar)."""
    s = np.asarray(s, float)
    clusters = np.asarray(clusters)
    n = len(s)
    u = s - s.mean()
    cross = sum(u[clusters == c].sum() ** 2 for c in np.unique(clusters)) - (u ** 2).sum()
    return float(np.sqrt(se_clt(s) ** 2 + cross / n ** 2))


def question_means(scores_nk):
    """[M] Sec 3.1  Resampling: average the K answers per question FIRST, then compute SE
    across questions. Never pool all n*K answers into one SE."""
    return np.asarray(scores_nk, float).mean(axis=1)


# ---------------------------------------------------------------- [M] two models
def compare_unpaired(mean_a, se_a, mean_b, se_b, alpha=0.05):
    """[M] Sec 4.1  diff, SE = sqrt(SE_A^2 + SE_B^2), CI (Eq.5), z (Eq.6).
    Use only when per-question scores are unavailable or question sets differ."""
    d = mean_a - mean_b
    se = float(np.sqrt(se_a ** 2 + se_b ** 2))
    return {"diff": d, "se": se, "ci": ci_normal(d, se, alpha), "z": d / se}


def compare_paired(s_a, s_b, clusters=None, alpha=0.05):
    """[M] Sec 4.2  Eq.7 paired SE on per-question differences; Eq.8 if clustered.
    Also returns Pearson correlation of question scores (report it)."""
    s_a, s_b = np.asarray(s_a, float), np.asarray(s_b, float)
    d = s_a - s_b
    n = len(d)
    if clusters is None:
        se = se_clt(d)
    else:  # Eq.8: (1/n) * sqrt( sum_c sum_i sum_j (d_ic - d_bar)(d_jc - d_bar) )
        clusters = np.asarray(clusters)
        u = d - d.mean()
        se = float(np.sqrt(sum(u[clusters == c].sum() ** 2 for c in np.unique(clusters))) / n)
    m = float(d.mean())
    return {"diff": m, "se": se, "ci": ci_normal(m, se, alpha), "z": m / se,
            "corr": float(np.corrcoef(s_a, s_b)[0, 1]), "n": n}


def se_paired_from_corr(se_a, se_b, corr):
    """[M] Sec 4.2  SE_paired = sqrt(SE_A^2 + SE_B^2 - 2 SE_A SE_B Corr(s_A, s_B))."""
    return float(np.sqrt(se_a ** 2 + se_b ** 2 - 2 * se_a * se_b * corr))


# ---------------------------------------------------------------- [M] power analysis
def n_required(delta, omega2, sigma2_a=0.0, sigma2_b=0.0, k_a=1, k_b=1, alpha=0.05, power=0.80):
    """[M] Eq.9  n = (z_{a/2} + z_b)^2 (w^2 + sA^2/KA + sB^2/KB) / delta^2  (paired design)."""
    beta = 1 - power
    v = omega2 + sigma2_a / k_a + sigma2_b / k_b
    return int(np.ceil((_z(alpha / 2) + _z(beta)) ** 2 * v / delta ** 2))


def mde(n, omega2, sigma2_a=0.0, sigma2_b=0.0, k_a=1, k_b=1, alpha=0.05, power=0.80):
    """[M] Eq.10  delta = (z_{a/2} + z_b) sqrt( (w^2 + sA^2/KA + sB^2/KB) / n )."""
    beta = 1 - power
    v = omega2 + sigma2_a / k_a + sigma2_b / k_b
    return float((_z(alpha / 2) + _z(beta)) * np.sqrt(v / n))


def variance_components(s_a_nk, s_b_nk, clusters=None):
    """[M] App. C  Estimate w^2, sigma_A^2, sigma_B^2 from PILOT data with K >> 1 answers
    per question (arrays shaped n x K). Clusters optional (pass one label per question).
    If you subsample questions for the pilot, sample whole clusters."""
    a, b = np.asarray(s_a_nk, float), np.asarray(s_b_nk, float)
    n, k = a.shape
    groups = np.arange(n) if clusters is None else np.asarray(clusters)
    xa, xb = a.mean(axis=1), b.mean(axis=1)
    dx = (xa - xb) - (xa - xb).mean()
    omega2 = sum(dx[groups == c].sum() ** 2 for c in np.unique(groups)) / n

    def sig2(s, x):
        e = s - x[:, None]  # n x K residuals
        return sum((e[groups == c].sum(axis=0) ** 2).sum() for c in np.unique(groups)) / (n * (k - 1))

    return {"omega2": float(omega2), "sigma2_a": float(sig2(a, xa)), "sigma2_b": float(sig2(b, xb))}


# ---------------------------------------------------------------- [B] small-sample methods
def wilson_ci(successes, n, alpha=0.05):
    """[B] Eq.12  Wilson score interval, single model, binary IID scores."""
    p, z = successes / n, _z(alpha / 2)
    centre = (p + z ** 2 / (2 * n)) / (1 + z ** 2 / n)
    half = (z / (2 * n)) / (1 + z ** 2 / n) * np.sqrt(4 * n * p * (1 - p) + z ** 2)
    return (float(centre - half), float(centre + half))


def bayes_beta_ci(successes, n, alpha=0.05):
    """[B] Eq.7  Posterior Beta(1+S, 1+N-S) under uniform prior; quantile interval."""
    lo, hi = stats.beta(1 + successes, 1 + n - successes).interval(1 - alpha)
    return (float(lo), float(hi))


def bayes_compare_independent(s_a, n_a, s_b, n_b, alpha=0.05, draws=20000, seed=0):
    """[B] Sec 3.3  Independent Beta posteriors -> credible intervals for the difference
    and the odds ratio, plus P(A > B). Use when per-question pairing is unavailable."""
    rng = np.random.default_rng(seed)
    pa = rng.beta(1 + s_a, 1 + n_a - s_a, draws)
    pb = rng.beta(1 + s_b, 1 + n_b - s_b, draws)
    q = [100 * alpha / 2, 100 * (1 - alpha / 2)]
    odds = (pa / (1 - pa)) / (pb / (1 - pb))
    return {"diff_ci": tuple(np.percentile(pa - pb, q)), "or_ci": tuple(np.percentile(odds, q)),
            "p_a_gt_b": float((pa > pb).mean())}


def bayes_clustered_ci(successes_per_cluster, n_per_cluster, alpha=0.05, k=10000, seed=0):
    """[B] Sec 3.2 / App E.1  Hierarchical Beta-Binomial model, importance sampling.
    theta ~ Beta(1,1), d ~ Gamma(1,1), Y_t ~ BetaBin(N_t, d*theta, d*(1-theta))."""
    rng = np.random.default_rng(seed)
    S, N = np.asarray(successes_per_cluster), np.asarray(n_per_cluster)
    th = rng.beta(1, 1, size=(k, 1))
    d = rng.gamma(1, 1, size=(k, 1))
    logw = stats.betabinom(N, d * th, d * (1 - th)).logpmf(S).sum(-1)
    w = np.exp(logw - logw.max())
    w /= w.sum()
    post = th[rng.choice(k, size=k, replace=True, p=w)].ravel()
    return tuple(np.percentile(post, [100 * alpha / 2, 100 * (1 - alpha / 2)]))


def _bvn_cdf(h, kk, rho):
    """P(X<=h, Y<=k) for standard bivariate normal with correlation rho, via Owen's T.
    Vectorised. [EXT] numerical helper; checked against scipy in the test suite."""
    h = np.where(np.abs(h) < 1e-12, 1e-12, h)
    kk = np.where(np.abs(kk) < 1e-12, 1e-12, kk)
    r = np.sqrt(1 - rho ** 2)
    a_h = (kk - rho * h) / (h * r)
    a_k = (h - rho * kk) / (kk * r)
    adj = np.where(h * kk > 0, 0.0, 0.5)
    return 0.5 * (stats.norm.cdf(h) + stats.norm.cdf(kk)) - special.owens_t(h, a_h) - special.owens_t(kk, a_k) - adj


def bayes_paired_diff(y_a, y_b, alpha=0.05, k=10000, seed=0):
    """[B] Sec 3.4 / App E.2  Paired binary scores (same questions, two models/conditions).
    Latent bivariate-normal model, importance sampling. Returns CI on theta_A - theta_B
    and P(A > B)."""
    rng = np.random.default_rng(seed)
    y_a, y_b = np.asarray(y_a), np.asarray(y_b)
    S = int((y_a * y_b).sum()); T = int((y_a * (1 - y_b)).sum())
    U = int(((1 - y_a) * y_b).sum()); V = int(((1 - y_a) * (1 - y_b)).sum())
    ta, tb = rng.beta(1, 1, k), rng.beta(1, 1, k)
    rho = 2 * rng.beta(4, 2, k) - 1
    mu_a, mu_b = stats.norm.ppf(ta), stats.norm.ppf(tb)
    tv = _bvn_cdf(-mu_a, -mu_b, rho)  # P(a<0, b<0): both wrong
    ts, tt, tu = ta + tb + tv - 1, 1 - tb - tv, 1 - ta - tv
    ok = (ts > 0) & (tt > 0) & (tu > 0) & (tv > 0)
    logw = np.full(k, -np.inf)
    logw[ok] = S * np.log(ts[ok]) + T * np.log(tt[ok]) + U * np.log(tu[ok]) + V * np.log(tv[ok])
    w = np.exp(logw - logw[ok].max())
    w /= w.sum()
    idx = rng.choice(k, size=k, replace=True, p=w)
    diff = (ta - tb)[idx]
    return {"diff_ci": tuple(np.percentile(diff, [100 * alpha / 2, 100 * (1 - alpha / 2)])),
            "p_a_gt_b": float((diff > 0).mean()), "table": {"both_right": S, "a_only": T, "b_only": U, "both_wrong": V}}


def bayes_confusion_metric_ci(tp, fp, fn, tn, metric, alpha=0.05, draws=4000, seed=0):
    """[B] Sec 3.5  Dirichlet(1 + counts) posterior over the confusion matrix; push samples
    through any metric(tp, fp, fn, tn) (e.g. F1). Use for metrics that are not simple averages."""
    rng = np.random.default_rng(seed)
    p = rng.dirichlet(np.array([tp, fp, fn, tn]) + 1, draws)
    vals = metric(p[:, 0], p[:, 1], p[:, 2], p[:, 3])
    return tuple(np.percentile(vals, [100 * alpha / 2, 100 * (1 - alpha / 2)]))


def f1(tp, fp, fn, tn):
    """[B] Eq.10"""
    return 2 * tp / (2 * tp + fp + fn)


def t_ci(values, alpha=0.05):
    """[B] App A.1  mean +/- t_{a/2, n-1} * SE. For small-n CONTINUOUS scores (or paired
    differences). Exact only if values are roughly normal: look at them before trusting it.
    [B] shows t-intervals are far too wide for small-n BINARY data; do not use them there."""
    v = np.asarray(values, float)
    m, se = float(v.mean()), se_clt(v)
    h = stats.t.ppf(1 - alpha / 2, len(v) - 1) * se
    return (m - h, m + h)


def bootstrap_ci(data, stat, clusters=None, alpha=0.05, b=10000, seed=0):
    """Percentile bootstrap. [M] allows it only for complicated estimators (e.g. AUC) at
    LARGE n. [B] shows it under-covers at small n; if n is small, report that caveat.
    With clusters, resamples whole clusters."""
    rng = np.random.default_rng(seed)
    data = np.asarray(data)
    if clusters is None:
        idx = [rng.integers(0, len(data), len(data)) for _ in range(b)]
    else:
        clusters = np.asarray(clusters)
        labs = np.unique(clusters)
        members = {c: np.flatnonzero(clusters == c) for c in labs}
        idx = [np.concatenate([members[c] for c in rng.choice(labs, len(labs))]) for _ in range(b)]
    vals = np.array([stat(data[i]) for i in idx])
    return tuple(np.percentile(vals, [100 * alpha / 2, 100 * (1 - alpha / 2)]))


def p_from_z(z):
    """Two-sided p-value for a z statistic (normal approximation)."""
    return float(2 * stats.norm.sf(abs(z)))


# ================================================================ MODULE: paired
def mcnemar_exact(y_a, y_b):
    """[EC] Exact McNemar test for paired BINARY scores. Only discordant units count:
    b = A right & B wrong, c = A wrong & B right. Under H0, b ~ Binomial(b+c, 1/2)."""
    y_a, y_b = np.asarray(y_a).astype(int), np.asarray(y_b).astype(int)
    b = int(((y_a == 1) & (y_b == 0)).sum())
    c = int(((y_a == 0) & (y_b == 1)).sum())
    p = 1.0 if b + c == 0 else float(stats.binomtest(b, b + c, 0.5).pvalue)
    return {"a_only": b, "b_only": c, "discordant": b + c, "p": p}


def sign_flip_test(d, n_resamples=100000, exact_max_n=16, seed=0):
    """[EC] Paired sign-flip permutation test on per-unit differences d (any score type).
    Exact (all 2^n sign patterns) when n <= exact_max_n, else Monte Carlo with +1 correction.
    No normality assumption; this is the small-n test for CONTINUOUS paired data."""
    d = np.asarray(d, float)
    n, obs = len(d), abs(d.mean())
    if n <= exact_max_n:
        signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
        means = np.abs((signs * d).mean(axis=1))
        return {"p": float(np.mean(means >= obs - 1e-12)), "exact": True, "n": n}
    rng = np.random.default_rng(seed)
    count = 0
    for start in range(0, n_resamples, 10000):
        m = min(10000, n_resamples - start)
        signs = rng.choice([-1.0, 1.0], size=(m, n))
        count += int((np.abs((signs * d).mean(axis=1)) >= obs - 1e-12).sum())
    return {"p": (count + 1) / (n_resamples + 1), "exact": False, "n": n}


# ================================================================ MODULE: power & resolution
def paired_binary_variance(p_a, p_b, rho):
    """[K] Eq.5  sigma_D^2 = pA qA + pB qB - 2 rho sqrt(pA qA pB qB)."""
    qa, qb = 1 - p_a, 1 - p_b
    return float(p_a * qa + p_b * qb - 2 * rho * np.sqrt(p_a * qa * p_b * qb))


def resolution(d=None, gap=None, sd_diff=None, n=None, alpha=0.05, power=0.80):
    """[K] Resolution diagnostics for a paired comparison.
    Give per-unit differences d, OR (gap, sd_diff, n).
    N* = (z_{a/2} + z_b)^2 sd_D^2 / gap^2 ;  q = n / N* ;  MDE(n) = (z_{a/2}+z_b) sd_D / sqrt(n).
    q >= 1: the benchmark can resolve a gap this size. q < 1 does NOT mean 'no difference'."""
    if d is not None:
        d = np.asarray(d, float)
        n, gap, sd_diff = len(d), float(d.mean()), float(np.std(d, ddof=1))
    zsum = _z(alpha / 2) + _z(1 - power)
    n_star = np.inf if gap == 0 else zsum ** 2 * sd_diff ** 2 / gap ** 2
    return {"gap": gap, "sd_diff": sd_diff, "n": n, "n_star": float(np.ceil(n_star)) if np.isfinite(n_star) else np.inf,
            "q": float(n / n_star) if np.isfinite(n_star) else 0.0, "mde": float(zsum * sd_diff / np.sqrt(n))}


# ================================================================ MODULE: clusters
def design_effect(s, clusters):
    """Empirical design effect DE = (SE_clustered / SE_CLT)^2 and effective sample size n/DE.
    [EXT] Kish's definition, applied to [M] Eq.4. Planning form [K]: DE = 1 + (m_bar - 1) * ICC."""
    s = np.asarray(s, float)
    de = (se_clustered(s, clusters) / se_clt(s)) ** 2
    return {"design_effect": float(de), "n": len(s), "n_effective": float(len(s) / de)}


# ================================================================ MODULE: multiple comparisons
def holm(pvals, alpha=0.05):
    """[HOLM] Step-down family-wise error control. Use for CONFIRMATORY claims."""
    p = np.asarray(pvals, float)
    m, order = len(p), np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return {"p_adj": adj, "reject": adj <= alpha, "m": m, "method": "holm"}


def benjamini_hochberg(pvals, alpha=0.05):
    """[BH] False-discovery-rate control. Use for EXPLORATORY screening of many comparisons."""
    p = np.asarray(pvals, float)
    m, order = len(p), np.argsort(p)
    adj = np.empty(m)
    running = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        running = min(running, min(1.0, m * p[i] / (rank + 1)))
        adj[i] = running
    return {"p_adj": adj, "reject": adj <= alpha, "m": m, "method": "bh"}


# ================================================================ MODULE: detector AUC
def _delong_components(scores, labels):
    """[DL] Midrank structural components (Sun & Xu 2014). Returns AUC, V10 (positives), V01 (negatives)."""
    scores, labels = np.asarray(scores, float), np.asarray(labels).astype(int)
    x, y = scores[labels == 1], scores[labels == 0]
    m, n = len(x), len(y)
    if m < 2 or n < 2:
        raise ValueError("need at least 2 positives and 2 negatives")
    tz = stats.rankdata(np.concatenate([x, y]))
    tx, ty = stats.rankdata(x), stats.rankdata(y)
    v10 = (tz[:m] - tx) / n
    v01 = 1 - (tz[m:] - ty) / m
    return float(v10.mean()), v10, v01


def auc_delong(scores, labels, alpha=0.05):
    """[DL] AUC with DeLong SE and normal CI (clipped to [0,1]).
    Orientation check: AUC < 0.5 means higher scores point to the NEGATIVE class. Check the
    score direction and the label coding before anything else. [KV]: DeLong under-covers at
    small n (about 90% for a nominal 95% at n=20), so treat small-n intervals as optimistic."""
    auc, v10, v01 = _delong_components(scores, labels)
    se = float(np.sqrt(np.var(v10, ddof=1) / len(v10) + np.var(v01, ddof=1) / len(v01)))
    lo, hi = ci_normal(auc, se, alpha)
    flag = None
    if hi < 0.5:
        flag = "INVERTED: whole CI below 0.5. Score direction or labels are almost certainly flipped."
    elif auc < 0.5:
        flag = "AUC below 0.5: check score direction and label coding."
    return {"auc": auc, "se": se, "ci": (max(0.0, lo), min(1.0, hi)), "n_pos": len(v10), "n_neg": len(v01), "flag": flag}


def delong_compare(scores_a, scores_b, labels, alpha=0.05):
    """[DL] Compare two correlated AUCs measured on the SAME labelled items. diff = AUC_A - AUC_B."""
    auc_a, v10a, v01a = _delong_components(scores_a, labels)
    auc_b, v10b, v01b = _delong_components(scores_b, labels)
    s10 = np.cov(np.vstack([v10a, v10b]))
    s01 = np.cov(np.vstack([v01a, v01b]))
    S = s10 / len(v10a) + s01 / len(v01a)
    var = S[0, 0] + S[1, 1] - 2 * S[0, 1]
    diff = auc_a - auc_b
    se = float(np.sqrt(var)) if var > 0 else float("nan")
    z = diff / se if var > 0 else float("nan")
    return {"auc_a": auc_a, "auc_b": auc_b, "diff": diff, "se": se, "ci": ci_normal(diff, se, alpha),
            "z": z, "p": p_from_z(z) if var > 0 else float("nan")}


# ================================================================ MODULE: zero / rare failures
def failure_rate_upper(failures, n, alpha=0.05):
    """[CP] One-sided (1-alpha) upper bound on the true failure rate after `failures` in n
    INDEPENDENT trials. With 0 failures this equals 1 - alpha^(1/n) (~3/n, the rule of three)."""
    if failures >= n:
        return 1.0
    return float(stats.beta.ppf(1 - alpha, failures + 1, n - failures))


def runs_needed(max_failure_rate, alpha=0.05, failures_allowed=0):
    """[CP] Independent runs needed so that, if at most `failures_allowed` failures occur,
    the (1-alpha) upper bound on the failure rate is <= max_failure_rate."""
    if failures_allowed == 0:
        return int(np.ceil(np.log(alpha) / np.log(1 - max_failure_rate)))
    n = failures_allowed + 1
    while failure_rate_upper(failures_allowed, n, alpha) > max_failure_rate:
        n += 1
    return n


# ================================================================ MODULE: equivalence / no harm
def tost_paired(d, low, high, alpha=0.05):
    """[TOST] Two one-sided t-tests on per-unit paired differences d against equivalence
    bounds (low, high), set BEFORE seeing data. Equivalent iff p_tost < alpha, which is the same
    as the (1 - 2*alpha) CI (90% for alpha=.05) lying inside (low, high)."""
    d = np.asarray(d, float)
    n, m, se = len(d), float(d.mean()), se_clt(d)
    df = n - 1
    p_low = float(stats.t.sf((m - low) / se, df))
    p_high = float(stats.t.cdf((m - high) / se, df))
    h = stats.t.ppf(1 - alpha, df) * se
    p = max(p_low, p_high)
    return {"mean_diff": m, "se": se, "ci_90": (m - h, m + h), "p_low": p_low, "p_high": p_high,
            "p_tost": p, "equivalent": p < alpha}


def tost_normal(est, se, low, high, alpha=0.05):
    """[TOST] Normal-approximation TOST for a large-n estimate with its SE (e.g. [M] paired SE)."""
    p_low = float(stats.norm.sf((est - low) / se))
    p_high = float(stats.norm.cdf((est - high) / se))
    h = _z(alpha) * se
    return {"ci_90": (est - h, est + h), "p_tost": max(p_low, p_high), "equivalent": max(p_low, p_high) < alpha}


def noninferiority(est, se, margin, alpha=0.05):
    """[TOST] One-sided test that est > -margin (the new condition is no worse than baseline
    by more than `margin`). est = new - baseline, oriented so higher is better."""
    p = float(stats.norm.sf((est + margin) / se))
    return {"lower_bound": est - _z(alpha) * se, "p": p, "noninferior": p < alpha}


# ================================================================ MODULE: judge correction
def judge_error_rates(human, judge, alpha=0.05):
    """[LEE] From a human-labelled calibration set: sensitivity q1 = P(judge=1 | human=1) and
    specificity q0 = P(judge=0 | human=0), each with a Wilson interval [B12]."""
    h, j = np.asarray(human).astype(int), np.asarray(judge).astype(int)
    n1, n0 = int((h == 1).sum()), int((h == 0).sum())
    tp, tn = int(((h == 1) & (j == 1)).sum()), int(((h == 0) & (j == 0)).sum())
    return {"q1": tp / n1, "q1_ci": wilson_ci(tp, n1, alpha), "q0": tn / n0, "q0_ci": wilson_ci(tn, n0, alpha),
            "agreement": float((h == j).mean()), "n_pos": n1, "n_neg": n0}


def rogan_gladen(p_hat, q0, q1):
    """[LEE] Eq.7  theta = (p_hat + q0 - 1) / (q0 + q1 - 1). Point estimate only.
    Undefined when q0 + q1 <= 1 (judge no better than chance). Clipped to [0,1]."""
    if q0 + q1 <= 1:
        raise ValueError("q0 + q1 <= 1: the judge is no better than chance; correction is undefined")
    return float(np.clip((p_hat + q0 - 1) / (q0 + q1 - 1), 0, 1))


def ppi_mean(y_labelled, f_labelled, f_unlabelled, alpha=0.05):
    """[PPI] Prediction-powered mean. y = human labels on the calibration set, f = judge outputs
    on the same items, f_unlabelled = judge outputs on everything else.
    theta = mean(f_unlab) - mean(f_lab - y);  CI = theta +/- z sqrt(var(f_lab - y)/n + var(f_unlab)/N).
    Requires the calibration items to be a random sample from the same pool, and the judge fixed
    (not tuned on them). [CH]: PPI beats the Rogan-Gladen correction in finite samples."""
    y, f, fu = (np.asarray(a, float) for a in (y_labelled, f_labelled, f_unlabelled))
    rect = f - y
    theta = float(fu.mean() - rect.mean())
    se = float(np.sqrt(np.var(rect, ddof=1) / len(y) + np.var(fu, ddof=1) / len(fu)))
    return {"theta": theta, "se": se, "ci": ci_normal(theta, se, alpha), "n_labelled": len(y), "n_unlabelled": len(fu),
            "naive_judge_mean": float(np.concatenate([f, fu]).mean())}


# ================================================================ MODULE: prompt sensitivity
def multiprompt(scores_pn):
    """[MZ] scores_pn: P prompts x n items. AvgP, MaxP, CPS = (1 - (MaxP - AvgP)) * MaxP.
    SE of AvgP averages each item over prompts first, then [M1] across items. That treats your
    prompt set as fixed; generalising to unseen paraphrases needs many prompts [EXT]."""
    s = np.asarray(scores_pn, float)
    per_prompt = s.mean(axis=1)
    avgp, maxp = float(per_prompt.mean()), float(per_prompt.max())
    return {"per_prompt": per_prompt, "avgp": avgp, "maxp": maxp, "minp": float(per_prompt.min()),
            "cps": (1 - (maxp - avgp)) * maxp, "se_avgp": se_clt(s.mean(axis=0))}


def rank_stability(model_by_prompt):
    """[MZ] Mean Kendall's tau between model rankings under every pair of prompts.
    model_by_prompt: M models x P prompts (scores). Low or negative tau = rankings are brittle."""
    s = np.asarray(model_by_prompt, float)
    taus = [stats.kendalltau(s[:, i], s[:, j])[0] for i in range(s.shape[1]) for j in range(i + 1, s.shape[1])]
    return {"mean_tau": float(np.nanmean(taus)), "min_tau": float(np.nanmin(taus)), "pairs": len(taus)}


# ================================================================ MODULE: repeated sampling
def noise_components(scores_nk):
    """[W] Split noise for n items x K samples. prediction variance = mean within-item variance;
    data variance = Var(item means) - pred_var/K. SE with K samples = sqrt(Var(item means)/n) [M].
    Always say which noise an error bar reports."""
    s = np.asarray(scores_nk, float)
    n, k = s.shape
    xbar = s.mean(axis=1)
    pred_var = float(np.var(s, axis=1, ddof=1).mean())
    data_var = max(float(np.var(xbar, ddof=1)) - pred_var / k, 0.0)
    return {"pred_var": pred_var, "data_var": data_var, "se_with_K": se_clt(xbar),
            "se_single_sample": float(np.sqrt((data_var + pred_var) / n)), "n": n, "K": k}


def pass_at_k(n_samples, n_correct, k):
    """[PK] Unbiased per-item pass@k = 1 - C(n-c, k)/C(n, k), averaged over items, with [M1] SE."""
    n_samples, n_correct = np.atleast_1d(n_samples), np.atleast_1d(n_correct)
    vals = []
    for n, c in zip(n_samples, n_correct):
        if n < k:
            raise ValueError("need n_samples >= k for every item")
        vals.append(1.0 if n - c < k else 1.0 - float(np.prod(1.0 - k / np.arange(n - c + 1, n + 1))))
    vals = np.array(vals)
    return {"pass_at_k": float(vals.mean()), "se": se_clt(vals) if len(vals) > 1 else float("nan"), "per_item": vals}


# ================================================================ MODULE: sequential
def sequential_paired_binary(y_a, y_b, alpha=0.05):
    """[SAVI] Anytime-valid sign test for paired BINARY results arriving in order.
    Mixture e-value over discordant pairs: E_t = 2^m * Beta(b+1, c+1), m = b + c.
    Under H0 (A and B equally good) E_t is a test martingale, so by Ville's inequality you may
    look after every unit and stop the first time E_t >= 1/alpha. [EXT] derivation of the mixture."""
    y_a, y_b = np.asarray(y_a).astype(int), np.asarray(y_b).astype(int)
    b = np.cumsum((y_a == 1) & (y_b == 0))
    c = np.cumsum((y_a == 0) & (y_b == 1))
    log_e = (b + c) * np.log(2) + special.betaln(b + 1, c + 1)
    e = np.exp(log_e)
    hit = np.flatnonzero(e >= 1 / alpha)
    return {"e_final": float(e[-1]), "stop_at_unit": int(hit[0]) + 1 if len(hit) else None,
            "reject": bool(len(hit)), "a_only": int(b[-1]), "b_only": int(c[-1]), "e_path": e}


# ================================================================ MODULE: signal-to-noise
def signal_to_noise(model_scores, rerun_scores):
    """[SN] signal = max pairwise gap between models / mean model score;
    noise = relative std of ONE model's repeated scores (seeds or checkpoints); SNR = signal/noise."""
    m = np.asarray(model_scores, float)
    r = np.asarray(rerun_scores, float)
    signal = float((m.max() - m.min()) / m.mean())
    noise = float(np.std(r, ddof=1) / r.mean())
    return {"signal": signal, "noise": noise, "snr": signal / noise if noise > 0 else float("inf")}
