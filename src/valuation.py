"""Gordon equity value and a coupon-bond YTM / duration book."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def gordon(dps_next: float, ke: float, g: float) -> float:
    if ke <= g:
        raise ValueError(f"Gordon requires ke > g (ke={ke:.4f}, g={g:.4f})")
    return dps_next / (ke - g)


def implied_g(price: float, dps_next: float, ke: float) -> float:
    return ke - dps_next / price


def bond_price(face: float, coupon_rate: float, ytm: float, years: float, freq: int) -> float:
    n = int(round(years * freq))
    c = face * coupon_rate / freq
    y = ytm / freq
    times = np.arange(1, n + 1)
    pv_coupons = float(np.sum(c / (1 + y) ** times))
    pv_face = face / (1 + y) ** n
    return pv_coupons + pv_face


def macaulay_duration(face: float, coupon_rate: float, ytm: float, years: float, freq: int) -> float:
    n = int(round(years * freq))
    c = face * coupon_rate / freq
    y = ytm / freq
    price = bond_price(face, coupon_rate, ytm, years, freq)
    times = np.arange(1, n + 1) / freq
    cfs = np.full(n, c)
    cfs[-1] += face
    w = cfs / (1 + y) ** (times * freq)
    return float(times @ w / price)


def modified_duration(mac: float, ytm: float, freq: int) -> float:
    return mac / (1 + ytm / freq)


def convexity(face: float, coupon_rate: float, ytm: float, years: float, freq: int) -> float:
    n = int(round(years * freq))
    c = face * coupon_rate / freq
    y = ytm / freq
    price = bond_price(face, coupon_rate, ytm, years, freq)
    k = np.arange(1, n + 1)
    cfs = np.full(n, c)
    cfs[-1] += face
    conv = float(np.sum(cfs * k * (k + 1) / (1 + y) ** (k + 2)))
    return conv / (price * freq**2)


def ytm_from_price(
    price: float,
    face: float,
    coupon_rate: float,
    years: float,
    freq: int,
    guess: float = 0.08,
) -> float:
    y = guess
    for _ in range(60):
        p = bond_price(face, coupon_rate, y, years, freq)
        dur = modified_duration(
            macaulay_duration(face, coupon_rate, y, years, freq), y, freq
        )
        dp_dy = -p * dur
        if abs(dp_dy) < 1e-18:
            break
        y_new = y - (p - price) / dp_dy
        if abs(y_new - y) < 1e-12:
            return float(max(y_new, -0.99))
        y = y_new
    return float(y)


@dataclass
class BondSnapshot:
    price: float
    ytm: float
    mac_duration: float
    mod_duration: float
    convexity: float
    coupon: float
    years: float


def comparable_bond(face: float, coupon: float, ytm: float, years: float, freq: int) -> BondSnapshot:
    px = bond_price(face, coupon, ytm, years, freq)
    mac = macaulay_duration(face, coupon, ytm, years, freq)
    mod = modified_duration(mac, ytm, freq)
    conv = convexity(face, coupon, ytm, years, freq)
    return BondSnapshot(
        price=px,
        ytm=ytm,
        mac_duration=mac,
        mod_duration=mod,
        convexity=conv,
        coupon=coupon,
        years=years,
    )


@dataclass
class EquityValuation:
    dps_next: float
    ke: float
    g: float
    gordon_price: float
    market_price: float
    premium_to_gordon: float
    implied_growth: float


def equity_vs_market(dps_ltm: float, ke: float, g: float, market_price: float) -> EquityValuation:
    dps_next = dps_ltm * (1 + g)
    model = gordon(dps_next, ke, g)
    return EquityValuation(
        dps_next=dps_next,
        ke=ke,
        g=g,
        gordon_price=model,
        market_price=market_price,
        premium_to_gordon=market_price / model - 1.0,
        implied_growth=implied_g(market_price, dps_next, ke),
    )
