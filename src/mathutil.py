"""Elementary functions used everywhere: normal CDF/PDF, day-count, OLS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import erf, exp, pi, sqrt

import numpy as np
import pandas as pd


def norm_cdf(x: float | np.ndarray) -> float | np.ndarray:
    """Φ(x) via erf — no scipy."""
    x_arr = np.asarray(x, dtype=float)
    out = 0.5 * (1.0 + erf_vec(x_arr / sqrt(2.0)))
    if np.ndim(x) == 0:
        return float(out)
    return out


def erf_vec(z: np.ndarray) -> np.ndarray:
    vectorized = np.vectorize(erf, otypes=[float])
    return vectorized(z)


def norm_pdf(x: float | np.ndarray) -> float | np.ndarray:
    x_arr = np.asarray(x, dtype=float)
    out = np.exp(-0.5 * x_arr**2) / sqrt(2.0 * pi)
    if np.ndim(x) == 0:
        return float(out)
    return out


def norm_ppf(p: float) -> float:
    """Inverse Φ by bisection — used to hit a target option delta."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if float(norm_cdf(mid)) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def year_fraction(start: date, end: date, basis: str) -> float:
    """ACT/365 or ACT/360. Weekends skipped only in the spot-lag helper."""
    days = (end - start).days
    if days < 0:
        raise ValueError("end before start")
    if basis == "act365":
        return days / 365.0
    if basis == "act360":
        return days / 360.0
    raise ValueError(f"unknown day-count {basis}")


def add_business_days(start: date, n: int) -> date:
    """Skip Saturday/Sunday only. Holiday calendars are labelled as a limitation."""
    d = start
    stepped = 0
    step = 1 if n >= 0 else -1
    target = abs(n)
    while stepped < target:
        d += timedelta(days=step)
        if d.weekday() < 5:
            stepped += 1
    return d


@dataclass
class OLSResult:
    beta: np.ndarray
    se: np.ndarray
    tstat: np.ndarray
    r2: float
    resid: np.ndarray
    n: int
    k: int
    names: tuple[str, ...]

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "coef": self.beta,
                "se": self.se,
                "t": self.tstat,
            },
            index=list(self.names),
        )


def ols(y: np.ndarray, X: np.ndarray, names: tuple[str, ...] | None = None) -> OLSResult:
    """OLS with intercept already inside X. Covariance: s^2 (X'X)^{-1}."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    if names is None:
        names = tuple(f"b{i}" for i in range(k))
    xtx = X.T @ X
    beta = np.linalg.solve(xtx, X.T @ y)
    resid = y - X @ beta
    dof = max(n - k, 1)
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(xtx)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    tstat = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    y_dm = y - y.mean()
    sst = float(y_dm @ y_dm)
    r2 = 1.0 - float(resid @ resid) / sst if sst > 0 else np.nan
    return OLSResult(beta=beta, se=se, tstat=tstat, r2=r2, resid=resid, n=n, k=k, names=names)


def add_intercept(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    return np.column_stack([np.ones(len(X)), X])
