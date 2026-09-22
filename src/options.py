"""Binomial (CRR) and Black–Scholes, put-call parity, Asian MC, implied vol."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, sqrt

import numpy as np

from .mathutil import norm_cdf, norm_pdf, norm_ppf


def bs_d1_d2(
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    vol: float,
    div: float = 0.0,
) -> tuple[float, float]:
    if tenor <= 0 or vol <= 0 or spot <= 0 or strike <= 0:
        raise ValueError("BS requires positive S, K, T, sigma")
    d1 = (log(spot / strike) + (rate - div + 0.5 * vol * vol) * tenor) / (vol * sqrt(tenor))
    d2 = d1 - vol * sqrt(tenor)
    return d1, d2


def bs_price(
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    vol: float,
    kind: str = "call",
    div: float = 0.0,
) -> float:
    d1, d2 = bs_d1_d2(spot, strike, tenor, rate, vol, div)
    df_q = exp(-div * tenor)
    df_r = exp(-rate * tenor)
    if kind == "call":
        return float(spot * df_q * norm_cdf(d1) - strike * df_r * norm_cdf(d2))
    if kind == "put":
        return float(strike * df_r * norm_cdf(-d2) - spot * df_q * norm_cdf(-d1))
    raise ValueError(kind)


def put_call_parity(
    call: float,
    put: float,
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    div: float = 0.0,
) -> float:
    """Returns C - P - (S e^{-qT} - K e^{-rT}). Zero if parity holds."""
    return call - put - (spot * exp(-div * tenor) - strike * exp(-rate * tenor))


def crr_price(
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    vol: float,
    steps: int,
    kind: str = "call",
    american: bool = False,
    div: float = 0.0,
) -> float:
    """Cox–Ross–Rubinstein. European by default; American via early exercise."""
    dt = tenor / steps
    u = exp(vol * sqrt(dt))
    d = 1.0 / u
    a = exp((rate - div) * dt)
    p = (a - d) / (u - d)
    if not (0 < p < 1):
        # fall back to risk-neutral clip for extreme vol/step combos
        p = min(max(p, 1e-8), 1 - 1e-8)
    disc = exp(-rate * dt)
    j = np.arange(steps + 1)
    st = spot * (u ** (steps - j)) * (d**j)
    if kind == "call":
        v = np.maximum(st - strike, 0.0)
        exercise = lambda s: np.maximum(s - strike, 0.0)
    elif kind == "put":
        v = np.maximum(strike - st, 0.0)
        exercise = lambda s: np.maximum(strike - s, 0.0)
    else:
        raise ValueError(kind)
    for i in range(steps - 1, -1, -1):
        v = disc * (p * v[:-1] + (1.0 - p) * v[1:])
        if american:
            st = spot * (u ** (i - np.arange(i + 1))) * (d ** np.arange(i + 1))
            v = np.maximum(v, exercise(st))
    return float(v[0])


def strike_from_delta(
    spot: float,
    tenor: float,
    rate: float,
    vol: float,
    delta: float,
    kind: str = "put",
    div: float = 0.0,
) -> float:
    """Invert BS delta for a strike. `delta` is signed (put ~ -0.25, call ~ 0.25)."""
    from math import exp, sqrt

    df_q = exp(-div * tenor)
    if kind == "call":
        p = min(max(delta / df_q, 1e-6), 1 - 1e-6)
        d1 = norm_ppf(p)
    elif kind == "put":
        p = min(max(-delta / df_q, 1e-6), 1 - 1e-6)
        d1 = -norm_ppf(p)
    else:
        raise ValueError(kind)
    return float(
        spot
        * exp(
            -(d1 * vol * sqrt(tenor) - (rate - div + 0.5 * vol * vol) * tenor)
        )
    )


def implied_vol(
    target: float,
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    kind: str = "call",
    div: float = 0.0,
    guess: float = 0.25,
) -> float:
    sigma = guess
    for _ in range(60):
        price = bs_price(spot, strike, tenor, rate, sigma, kind, div)
        d1, _ = bs_d1_d2(spot, strike, tenor, rate, sigma, div)
        vega = spot * exp(-div * tenor) * float(norm_pdf(d1)) * sqrt(tenor)
        if vega < 1e-12:
            break
        sigma_new = sigma - (price - target) / vega
        sigma_new = min(max(sigma_new, 1e-4), 5.0)
        if abs(sigma_new - sigma) < 1e-8:
            return float(sigma_new)
        sigma = sigma_new
    return float(sigma)


def asian_arithmetic(
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    vol: float,
    kind: str = "call",
    n_steps: int = 12,
    n_paths: int = 40_000,
    seed: int = 7,
    div: float = 0.0,
) -> float:
    """Risk-neutral MC, arithmetic average of the path (unconventional / Treasury)."""
    rng = np.random.default_rng(seed)
    dt = tenor / n_steps
    drift = (rate - div - 0.5 * vol * vol) * dt
    shock = vol * sqrt(dt)
    z = rng.standard_normal((n_paths, n_steps))
    log_s = np.log(spot) + np.cumsum(drift + shock * z, axis=1)
    paths = np.exp(log_s)
    avg = paths.mean(axis=1)
    if kind == "call":
        payoff = np.maximum(avg - strike, 0.0)
    else:
        payoff = np.maximum(strike - avg, 0.0)
    return float(exp(-rate * tenor) * payoff.mean())


@dataclass
class OptionQuote:
    kind: str
    strike: float
    tenor: float
    spot: float
    market: float
    iv: float
    bs: float
    crr: float
    parity_gap: float
