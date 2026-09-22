"""Covered-interest FX forward with spot lag and split day-count."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .mathutil import add_business_days, year_fraction


@dataclass
class FXForward:
    trade_date: date
    spot_date: date
    expiry: date
    spot: float
    r_base: float  # USD
    r_quote: float  # INR
    t_base: float
    t_quote: float
    outright: float
    points: float
    basis_base: str
    basis_quote: str
    spot_lag: int


def fx_forward_outright(
    spot: float,
    r_base: float,
    r_quote: float,
    t_base: float,
    t_quote: float,
) -> float:
    """USDINR: F = S * (1 + r_INR * t_INR) / (1 + r_USD * t_USD)."""
    return spot * (1.0 + r_quote * t_quote) / (1.0 + r_base * t_base)


def price_forward(
    trade_date: date,
    spot: float,
    r_usd: float,
    r_inr: float,
    tenor_years: float,
    spot_lag: int,
    usd_basis: str,
    inr_basis: str,
) -> FXForward:
    spot_date = add_business_days(trade_date, spot_lag)
    # expiry = spot date plus tenor in calendar days (365 * tenor)
    from datetime import timedelta

    expiry = spot_date + timedelta(days=int(round(365 * tenor_years)))
    t_usd = year_fraction(spot_date, expiry, usd_basis)
    t_inr = year_fraction(spot_date, expiry, inr_basis)
    outright = fx_forward_outright(spot, r_usd, r_inr, t_usd, t_inr)
    return FXForward(
        trade_date=trade_date,
        spot_date=spot_date,
        expiry=expiry,
        spot=spot,
        r_base=r_usd,
        r_quote=r_inr,
        t_base=t_usd,
        t_quote=t_inr,
        outright=outright,
        points=outright - spot,
        basis_base=usd_basis,
        basis_quote=inr_basis,
        spot_lag=spot_lag,
    )
