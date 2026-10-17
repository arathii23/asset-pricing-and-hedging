"""Mean-variance frontier and two-fund (CML) illustration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product

import numpy as np
import pandas as pd

from . import config as C


@dataclass
class Frontier:
    targets: np.ndarray
    vol: np.ndarray
    weights: np.ndarray
    names: tuple[str, ...]
    gmv_vol: float
    gmv_ret: float
    gmv_w: np.ndarray
    tangency_vol: float
    tangency_ret: float
    tangency_w: np.ndarray
    rf: float


def _inv_cov(cov: np.ndarray) -> np.ndarray:
    return np.linalg.pinv(cov)


def min_var_weights(mean: np.ndarray, cov: np.ndarray, target: float) -> np.ndarray:
    """Analytic min-variance weights with 1'w = 1 and w'μ = target (allowing shorts)."""
    n = len(mean)
    ones = np.ones(n)
    inv = _inv_cov(cov)
    A = ones @ inv @ ones
    B = ones @ inv @ mean
    C = mean @ inv @ mean
    det = A * C - B**2
    lam = (C - B * target) / det
    gam = (A * target - B) / det
    return inv @ (lam * ones + gam * mean)


def gmv_weights(cov: np.ndarray) -> np.ndarray:
    ones = np.ones(len(cov))
    inv = _inv_cov(cov)
    w = inv @ ones
    return w / w.sum()


def tangency_weights(mean: np.ndarray, cov: np.ndarray, rf: float) -> np.ndarray:
    excess = mean - rf
    inv = _inv_cov(cov)
    w = inv @ excess
    s = w.sum()
    if abs(s) < 1e-12:
        return np.ones(len(mean)) / len(mean)
    return w / s


def cap_weights(w: np.ndarray, cap: float) -> np.ndarray:
    """Project non-negative weights onto the simplex with a per-name cap."""
    w = np.maximum(np.asarray(w, dtype=float), 0.0)
    if not 0 < cap <= 1 or len(w) * cap < 1 - 1e-12:
        raise ValueError("The position cap must allow weights to add to 100%")
    s = w.sum()
    if s <= 1e-12:
        w = np.ones(len(w)) / len(w)
    else:
        w = w / s
    locked = np.zeros(len(w), dtype=bool)
    for _ in range(len(w)):
        over = (w > cap + 1e-12) & ~locked
        if not over.any():
            break
        w[over] = cap
        locked[over] = True
        residual = 1.0 - float(w[locked].sum())
        free = ~locked
        if residual <= 1e-12 or not free.any():
            break
        base = w[free]
        if float(base.sum()) <= 1e-12:
            w[free] = residual / int(free.sum())
        else:
            w[free] = residual * base / base.sum()
    total = float(w.sum())
    return w / total if total > 0 else np.ones(len(w)) / len(w)


@lru_cache(maxsize=16)
def feasible_weight_grid(n: int, cap: float, step: float = C.ALLOCATION_STEP) -> np.ndarray:
    """All feasible allocations in 5-percentage-point steps for the small book."""
    units, limit = round(1 / step), round(cap / step)
    if not 0 < cap <= 1 or n * cap < 1 - 1e-12 or not np.isclose(units * step, 1):
        raise ValueError("Infeasible weight grid or position cap")
    if not np.isclose(limit * step, cap) or n > 6:
        raise ValueError("Use a cap on the weight grid and at most six assets")
    rows = [(*row, units - sum(row)) for row in product(range(limit + 1), repeat=n - 1)
            if 0 <= units - sum(row) <= limit]
    if not rows:
        raise ValueError("No feasible allocation on the chosen grid")
    weights = np.asarray(rows, dtype=float) * step
    weights.setflags(write=False)
    return weights


def long_only_tangency(
    mean: np.ndarray,
    cov: np.ndarray,
    rf: float,
    cap: float | None = None,
) -> np.ndarray:
    """Maximise estimated Sharpe over a constrained 5%-increment weight grid.

    Every candidate already sums to 100%, has no shorts and obeys the cap.
    This is the best grid allocation, NOT a continuous optimum. The fixed grid
    is a transparent teaching/trade-sizing assumption, not a tuned parameter.
    The policy stays fully invested even if all estimated excess returns are negative.
    """
    mean, cov = np.asarray(mean, dtype=float), np.asarray(cov, dtype=float)
    if not np.isfinite(mean).all() or not np.isfinite(cov).all():
        raise ValueError("Expected returns and covariance must be finite")
    weights = feasible_weight_grid(len(mean), 1.0 if cap is None else float(cap))
    variance = np.einsum("ij,jk,ik->i", weights, cov, weights)
    scores = weights @ (mean - rf) / np.sqrt(np.maximum(variance, 1e-16))
    return weights[int(np.argmax(scores))].copy()


def port_stats(w: np.ndarray, mean: np.ndarray, cov: np.ndarray) -> tuple[float, float]:
    ret = float(w @ mean)
    vol = float(np.sqrt(w @ cov @ w))
    return ret, vol


def efficient_frontier(
    mean: np.ndarray,
    cov: np.ndarray,
    names: tuple[str, ...],
    rf: float,
    n_points: int = 40,
) -> Frontier:
    gmv_w = gmv_weights(cov)
    gmv_ret, gmv_vol = port_stats(gmv_w, mean, cov)
    tan_w = tangency_weights(mean, cov, rf)
    tan_ret, tan_vol = port_stats(tan_w, mean, cov)

    lo = min(gmv_ret, float(mean.min()) - 0.02)
    hi = max(float(mean.max()) + 0.04, tan_ret + 0.02)
    targets = np.linspace(lo, hi, n_points)
    vols = []
    weights = []
    for t in targets:
        w = min_var_weights(mean, cov, float(t))
        _, v = port_stats(w, mean, cov)
        vols.append(v)
        weights.append(w)
    return Frontier(
        targets=targets,
        vol=np.array(vols),
        weights=np.vstack(weights),
        names=names,
        gmv_vol=gmv_vol,
        gmv_ret=gmv_ret,
        gmv_w=gmv_w,
        tangency_vol=tan_vol,
        tangency_ret=tan_ret,
        tangency_w=tan_w,
        rf=rf,
    )


def cml_vol_grid(rf: float, tangency_ret: float, tangency_vol: float, vols: np.ndarray) -> np.ndarray:
    """Two-fund line: combinations of rf and the tangency (market) book."""
    slope = (tangency_ret - rf) / tangency_vol if tangency_vol > 0 else 0.0
    return rf + slope * vols


def as_weight_frame(frontier: Frontier) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "gmv": frontier.gmv_w,
            "tangency": frontier.tangency_w,
        },
        index=list(frontier.names),
    )
