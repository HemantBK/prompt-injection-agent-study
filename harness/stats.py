"""Hand-rolled statistics: Wilson interval, exact McNemar, Fisher exact, seed bootstrap.

Pinned by tests/test_stats.py against textbook values. No scipy dependency."""
from __future__ import annotations

import math
import random


def wilson(k, n, z=1.959964):
    """Wilson score interval for k successes in n trials. Returns (p_hat, lo, hi)."""
    if n == 0:
        return (float("nan"), 0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def binom_two_sided(k, n, p=0.5):
    """Exact two-sided binomial test p-value (sum of probabilities <= P(k))."""
    pk = math.comb(n, k) * p ** k * (1 - p) ** (n - k)
    total = 0.0
    for i in range(n + 1):
        pi = math.comb(n, i) * p ** i * (1 - p) ** (n - i)
        if pi <= pk * (1 + 1e-9):
            total += pi
    return min(1.0, total)


def mcnemar_exact(b, c):
    """Exact McNemar on discordant pairs: b = (before success, after fail), c = (before fail, after success)."""
    n = b + c
    if n == 0:
        return 1.0
    return binom_two_sided(min(b, c), n, 0.5)


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact test for table [[a, b], [c, d]] (sum of tables at least as extreme)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def pmf(x):
        return math.comb(r1, x) * math.comb(n - r1, c1 - x) / math.comb(n, c1)

    p_obs = pmf(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs * (1 + 1e-9)))


def bootstrap_rate(successes_by_seed, n_boot=2000, seed=0, alpha=0.05):
    """successes_by_seed: list of 0/1 (one per seed) or list of lists (reps per seed).
    Resamples SEEDS with replacement. Returns (mean, lo, hi)."""
    rng = random.Random(seed)
    groups = [g if isinstance(g, (list, tuple)) else [g] for g in successes_by_seed]
    if not groups:
        return (float("nan"), float("nan"), float("nan"))
    means = []
    for _ in range(n_boot):
        sample = [rng.choice(groups) for _ in groups]
        flat = [x for g in sample for x in g]
        means.append(sum(flat) / len(flat))
    means.sort()
    mean = sum(x for g in groups for x in g) / sum(len(g) for g in groups)
    return (mean, means[int(alpha / 2 * n_boot)], means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))])


def fmt_rate(k, n):
    p, lo, hi = wilson(k, n)
    return "{}/{} = {:.0%} [{:.0%}, {:.0%}]".format(k, n, p, lo, hi)
