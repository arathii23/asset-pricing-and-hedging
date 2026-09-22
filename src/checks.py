"""Offline identities — run these before any market pull."""

from __future__ import annotations

from datetime import date

from .fx_forward import price_forward
from .mathutil import add_intercept, ols
from .options import bs_price, crr_price, put_call_parity
from .valuation import bond_price, ytm_from_price


class CheckFailure(AssertionError):
    pass


def _close(a: float, b: float, tol: float, label: str) -> None:
    if abs(a - b) > tol:
        raise CheckFailure(f"{label}: {a:.8f} vs {b:.8f} (tol {tol})")


def run_checks() -> list[str]:
    logs: list[str] = []
    s, k, t, r, sig = 100.0, 100.0, 1.0, 0.05, 0.20
    call = bs_price(s, k, t, r, sig, "call")
    put = bs_price(s, k, t, r, sig, "put")
    gap = put_call_parity(call, put, s, k, t, r)
    _close(gap, 0.0, 1e-10, "put-call parity")
    logs.append(f"put-call parity gap {gap:.2e}")

    crr = crr_price(s, k, t, r, sig, steps=250, kind="call")
    _close(crr, call, 0.08, "CRR 250 vs BS")
    logs.append(f"CRR250 {crr:.4f} vs BS {call:.4f}")

    px = bond_price(100, 0.07, 0.08, 7, 2)
    y = ytm_from_price(px, 100, 0.07, 7, 2, guess=0.05)
    _close(y, 0.08, 1e-8, "YTM round-trip")
    logs.append(f"bond YTM round-trip {y:.6f}")

    fwd = price_forward(date(2026, 9, 15), 83.0, 0.04, 0.065, 1.0, 2, "act360", "act365")
    if not (fwd.outright > fwd.spot):
        raise CheckFailure("INR>USD rates should put USDINR forward above spot")
    logs.append(f"1y USDINR forward {fwd.outright:.4f} vs spot {fwd.spot:.4f}")

    import numpy as np

    rng = np.random.default_rng(0)
    m = rng.normal(0.001, 0.02, 800)
    a = 0.0002 + 1.3 * m + rng.normal(0, 0.005, 800)
    fit = ols(a, add_intercept(m), names=("a", "b"))
    _close(float(fit.beta[1]), 1.3, 0.05, "OLS beta recovery")
    logs.append(f"OLS beta {fit.beta[1]:.3f} (true 1.30)")
    return logs
