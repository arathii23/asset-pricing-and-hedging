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
) -> pd.DataFrame:
    unhedged = inr_per_usd_unhedged(spots)
    fwd = inr_per_usd_forward(forward, spots)
    put = inr_per_usd_put(spots, put_k, put_prem_inr)
    collar = inr_per_usd_collar(spots, put_k, call_k, collar_net_inr)
    return pd.DataFrame(
        {
            "usd_inr": spots,
            "unhedged_inr_m": unhedged * notional_usd / 1e6,
            "forward_inr_m": fwd * notional_usd / 1e6,
            "put_inr_m": put * notional_usd / 1e6,
            "collar_inr_m": collar * notional_usd / 1e6,
        }
    )


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
