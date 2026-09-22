"""Return construction — simple, log, excess, annualisation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def simple_returns(prices: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    return prices.pct_change().dropna(how="all")


def log_returns(prices: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    return np.log(prices / prices.shift(1)).dropna(how="all")


def excess(returns: pd.Series | pd.DataFrame, rf_per_period: float | pd.Series) -> pd.Series | pd.DataFrame:
    return returns.sub(rf_per_period, axis=0)


def periods_per_year(index: pd.DatetimeIndex) -> int:
    if len(index) < 3:
        return 52
    delta = np.median(np.diff(index.values).astype("timedelta64[D]").astype(float))
    if delta <= 1.5:
        return 252
    if delta <= 9:
        return 52
    return 12


def annualize_mean(mean_per_period: float, ppy: int) -> float:
    return float(mean_per_period) * ppy


def annualize_vol(std_per_period: float, ppy: int) -> float:
    return float(std_per_period) * np.sqrt(ppy)


def resample_last(prices: pd.DataFrame, rule: str = "W-FRI") -> pd.DataFrame:
    return prices.resample(rule).last().dropna(how="all")
