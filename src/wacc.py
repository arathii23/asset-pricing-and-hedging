"""WACC and USD-project NPV / IRR."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def wacc(ke: float, kd: float, equity_weight: float, tax: float) -> float:
    we = float(equity_weight)
    wd = 1.0 - we
    return we * ke + wd * kd * (1.0 - tax)


def npv(rate: float, cashflows: list[float]) -> float:
    """cashflows[0] is t=0 (usually negative capex)."""
    return float(sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cashflows)))


def irr(cashflows: list[float], guess: float = 0.1, lo: float = -0.9, hi: float = 5.0) -> float:
    """Sign-change bisection; npv(lo) and npv(hi) should bracket 0."""
    f_lo = npv(lo, cashflows)
    f_hi = npv(hi, cashflows)
    if f_lo * f_hi > 0:
        # fall back to Newton from guess
        r = guess
        for _ in range(80):
            f = npv(r, cashflows)
            df = sum(-t * cf / (1.0 + r) ** (t + 1) for t, cf in enumerate(cashflows))
            if abs(df) < 1e-18:
                break
            r_new = r - f / df
            if abs(r_new - r) < 1e-10:
                return float(r_new)
            r = r_new
        return float(r)
    a, b, fa = lo, hi, f_lo
    for _ in range(80):
        m = 0.5 * (a + b)
        fm = npv(m, cashflows)
        if abs(fm) < 1e-12:
            return float(m)
        if fa * fm <= 0:
            b = m
        else:
            a, fa = m, fm
    return float(0.5 * (a + b))


@dataclass
class ProjectCase:
    name: str
    inr_cashflows: list[float]
    npv: float
    irr: float


def usd_project_inr_cashflows(
    capex_usd: float,
    fcf_usd: tuple[float, ...],
    fx_path: list[float],
    salvage_usd: float = 0.0,
) -> list[float]:
    """fx_path[0] converts capex; fx_path[t] converts year-t FCF. INR per USD.

    Salvage is added to the last year. The labelled case uses zero: the project ends.
    """
    if len(fx_path) != 1 + len(fcf_usd):
        raise ValueError("fx_path must be 1 + horizon")
    cfs = [-capex_usd * fx_path[0]]
    for t, fcf in enumerate(fcf_usd, start=1):
        cfs.append(fcf * fx_path[t])
    cfs[-1] += salvage_usd * fx_path[-1]
    return cfs


def fcf_haircut_breakeven(
    rate: float,
    capex_usd: float,
    fcf_usd: tuple[float, ...],
    fx_path: list[float],
    salvage_usd: float = 0.0,
) -> float:
    """How far every free cash flow must fall before NPV is zero. Same NPV formula."""
    def at(haircut: float) -> float:
        cut = tuple(fcf * (1.0 - haircut) for fcf in fcf_usd)
        return npv(rate, usd_project_inr_cashflows(capex_usd, cut, fx_path, salvage_usd))

    if at(0.0) <= 0.0:
        return 0.0
    lo, hi = 0.0, 1.0
    if at(hi) > 0.0:
        return 1.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if at(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return float(hi)


def tornado(base_npv: float, cases: dict[str, float]) -> pd.DataFrame:
    rows = []
    for label, value in cases.items():
        rows.append({"case": label, "npv": value, "delta": value - base_npv})
    return pd.DataFrame(rows).sort_values("delta")
