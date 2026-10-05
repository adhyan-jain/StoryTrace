"""Cluster bootstrap CIs and paired cluster permutation tests (unit of analysis = base STORY, not item).

Each story contributes 3 matched items; items within a story share a world, so resampling items would understate variance.
"""
from __future__ import annotations
from typing import Callable, Dict, Tuple
import numpy as np
from .metrics import summarize

B = 10000


def metric_fn(name: str) -> Callable[[np.ndarray], float]:
    def f(c):
        v = summarize(c)[name]
        return np.nan if v is None else v
    return f


def boot_ci(M: np.ndarray, name: str, seed: int = 0, b: int = B) -> Tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    f = metric_fn(name)
    S = len(M)
    idx = rng.integers(0, S, size=(b, S))
    vals = np.array([f(M[i].sum(0)) for i in idx])
    return f(M.sum(0)), *np.nanpercentile(vals, [2.5, 97.5])


def paired_diff(MA: np.ndarray, MB: np.ndarray, name: str, seed: int = 0, b: int = B) -> Dict[str, float]:
    """A - B on stories present in both (rows aligned). Bootstrap CI + sign-flip permutation p (two-sided)."""
    assert MA.shape == MB.shape
    rng = np.random.default_rng(seed)
    f = metric_fn(name)
    S = len(MA)
    obs = f(MA.sum(0)) - f(MB.sum(0))
    idx = rng.integers(0, S, size=(b, S))
    boot = np.array([f(MA[i].sum(0)) - f(MB[i].sum(0)) for i in idx])
    flips = rng.integers(0, 2, size=(b, S)).astype(bool)
    perm = np.empty(b)
    for j in range(b):
        fl = flips[j][:, None]
        perm[j] = f(np.where(fl, MB, MA).sum(0)) - f(np.where(fl, MA, MB).sum(0))
    p = (1 + np.sum(np.abs(perm[~np.isnan(perm)]) >= abs(obs) - 1e-12)) / (1 + np.sum(~np.isnan(perm)))
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])
    return {"diff": obs, "ci_lo": lo, "ci_hi": hi, "p_perm": p, "n_stories": S}


def holm(pvals: Dict[str, float]) -> Dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def cohens_h(p1: float, p2: float) -> float:
    return 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
