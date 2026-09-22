"""Black–Scholes Greeks (analytic) and a one-step binomial delta check."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt

from .mathutil import norm_cdf, norm_pdf
from .options import bs_d1_d2, crr_price


@dataclass
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


def bs_greeks(
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    vol: float,
    kind: str = "call",
    div: float = 0.0,
) -> Greeks:
    d1, d2 = bs_d1_d2(spot, strike, tenor, rate, vol, div)
    df_q = exp(-div * tenor)
    df_r = exp(-rate * tenor)
    pdf = float(norm_pdf(d1))
    if kind == "call":
        delta = df_q * float(norm_cdf(d1))
        theta = (
            -spot * df_q * pdf * vol / (2 * sqrt(tenor))
            - rate * strike * df_r * float(norm_cdf(d2))
            + div * spot * df_q * float(norm_cdf(d1))
        )
        rho = strike * tenor * df_r * float(norm_cdf(d2))
    elif kind == "put":
        delta = -df_q * float(norm_cdf(-d1))
        theta = (
            -spot * df_q * pdf * vol / (2 * sqrt(tenor))
            + rate * strike * df_r * float(norm_cdf(-d2))
            - div * spot * df_q * float(norm_cdf(-d1))
        )
        rho = -strike * tenor * df_r * float(norm_cdf(-d2))
    else:
        raise ValueError(kind)
    gamma = df_q * pdf / (spot * vol * sqrt(tenor))
    vega = spot * df_q * pdf * sqrt(tenor)
    return Greeks(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho)


def binomial_delta(
    spot: float,
    strike: float,
    tenor: float,
    rate: float,
    vol: float,
    steps: int,
    kind: str,
    bump: float = 0.01,
) -> float:
    up = crr_price(spot * (1 + bump), strike, tenor, rate, vol, steps, kind)
    dn = crr_price(spot * (1 - bump), strike, tenor, rate, vol, steps, kind)
    return (up - dn) / (2 * spot * bump)
