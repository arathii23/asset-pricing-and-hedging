"""USD receipt hedges in INR: forward, put, collar, residual P&L."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .options import bs_price


@dataclass
class HedgePolicy:
    name: str
    description: str
    premium_usd: float


def inr_per_usd_unhedged(spot_t: np.ndarray) -> np.ndarray:
    return spot_t


def inr_per_usd_forward(forward: float, spot_t: np.ndarray) -> np.ndarray:
    return np.full_like(spot_t, forward, dtype=float)


def inr_per_usd_put(spot_t: np.ndarray, strike: float, premium_inr: float) -> np.ndarray:
    """Long USD put: floor at K, paid for with premium (INR per USD)."""
    return np.maximum(spot_t, strike) - premium_inr


def inr_per_usd_collar(
    spot_t: np.ndarray,
    put_k: float,
    call_k: float,
    net_premium_inr: float,
) -> np.ndarray:
    """Long put, short call on USDINR: proceeds in [put_k, call_k] minus net premium."""
    return np.clip(spot_t, put_k, call_k) - net_premium_inr


def hedge_table(
    spots: np.ndarray,
    forward: float,
    put_k: float,
    call_k: float,
    put_prem_inr: float,
    collar_net_inr: float,
    notional_usd: float,
    premium_growth: float = 1.0,
) -> pd.DataFrame:
    """Receipt-date proceeds. Grow an upfront INR premium to that same date."""
    unhedged = inr_per_usd_unhedged(spots)
    fwd = inr_per_usd_forward(forward, spots)
    put = inr_per_usd_put(spots, put_k, put_prem_inr * premium_growth)
    collar = inr_per_usd_collar(spots, put_k, call_k, collar_net_inr * premium_growth)
    return pd.DataFrame(
        {
            "usd_inr": spots,
            "unhedged_inr_m": unhedged * notional_usd / 1e6,
            "forward_inr_m": fwd * notional_usd / 1e6,
            "put_inr_m": put * notional_usd / 1e6,
            "collar_inr_m": collar * notional_usd / 1e6,
        }
    )


def receipt_hedge_comparison(
    fixings: np.ndarray, receipt_basis: str, put_k: float, call_k: float,
    collar_premium: float, asian_put_premium: float, notional: float,
    rate_inr: float, tenor: float = 1.0, hedge_ratio: float = 1.0,
) -> pd.DataFrame:
    """Compare hedges against the SAME receipt contract on each path.

    Each row has monthly FX fixings. All receipts and option payoffs settle at
    year-end. Receipt conversion is either final fixing or arithmetic average.
    An average-indexed, year-end receipt is NOT monthly cash already collected.
    """
    paths = np.asarray(fixings, dtype=float)
    if paths.ndim != 2 or paths.shape[1] < 1 or not np.isfinite(paths).all() or (paths <= 0).any():
        raise ValueError("Provide positive monthly FX fixings for each path")
    if not 0 <= hedge_ratio <= 1 or put_k > call_k or notional <= 0:
        raise ValueError("Invalid hedge ratio, strikes, or receipt amount")
    terminal, average = paths[:, -1], paths.mean(axis=1)
    if receipt_basis not in {"terminal", "average"}:
        raise ValueError("Receipt basis must be terminal or average")
    base = terminal if receipt_basis == "terminal" else average
    growth = np.exp(rate_inr * tenor)
    collar_payoff = np.maximum(put_k - terminal, 0) - np.maximum(terminal - call_k, 0)
    asian_payoff = np.maximum(put_k - average, 0)
    return pd.DataFrame({
        "Final rate": terminal, "Average rate": average,
        "Unhedged (INR)": notional * base,
        "Terminal collar (INR)": notional * (base + hedge_ratio * (collar_payoff - collar_premium * growth)),
        "Average-rate put (INR)": notional * (base + hedge_ratio * (asian_payoff - asian_put_premium * growth)),
    })


def residual_vol(series: np.ndarray) -> float:
    return float(np.std(series, ddof=1))


def fx_option_premiums(
    spot: float,
    put_k: float,
    call_k: float,
    tenor: float,
    rate_inr: float,
    vol: float,
    div_usd: float,
) -> tuple[float, float]:
    """
    USDINR quoted as INR per USD. A USD put is a put on the FX rate.
    `div_usd` is the USD rate (foreign) in the Garman–Kohlhagen sense.
    """
    put = bs_price(spot, put_k, tenor, rate_inr, vol, "put", div=div_usd)
    call = bs_price(spot, call_k, tenor, rate_inr, vol, "call", div=div_usd)
    return put, call
