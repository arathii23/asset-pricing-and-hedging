"""CAPM: beta, Jensen alpha, SML required return."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .mathutil import OLSResult, add_intercept, ols


@dataclass
class CAPMResult:
    ticker: str
    market: str
    alpha: float
    beta: float
    alpha_se: float
    beta_se: float
    r2: float
    n: int
    ppy: int
    rf_annual: float
    mkt_premium_annual: float
    sample_premium_annual: float
    cost_of_equity: float
    jensen_annual: float
    ols: OLSResult

    @property
    def sml_required(self) -> float:
        return self.rf_annual + self.beta * self.mkt_premium_annual


def capm(
    asset_excess: pd.Series,
    market_excess: pd.Series,
    rf_annual: float,
    ppy: int,
    ticker: str,
    market: str,
    premium_override: float | None = None,
) -> CAPMResult:
    aligned = pd.concat([asset_excess, market_excess], axis=1, join="inner").dropna()
    aligned.columns = ["a", "m"]
    y = aligned["a"].to_numpy()
    X = add_intercept(aligned["m"].to_numpy())
    fit = ols(y, X, names=("alpha", "beta"))
    alpha, beta = (float(fit.beta[0]), float(fit.beta[1]))
    hist_prem = float(aligned["m"].mean()) * ppy
    prem = hist_prem if premium_override is None else premium_override
    ke = rf_annual + beta * prem
    return CAPMResult(
        ticker=ticker,
        market=market,
        alpha=alpha,
        beta=beta,
        alpha_se=float(fit.se[0]),
        beta_se=float(fit.se[1]),
        r2=float(fit.r2),
        n=fit.n,
        ppy=ppy,
        rf_annual=rf_annual,
        mkt_premium_annual=prem,
        sample_premium_annual=hist_prem,
        cost_of_equity=ke,
        jensen_annual=alpha * ppy,
        ols=fit,
    )


def sml_line(rf: float, premium: float, betas: np.ndarray) -> np.ndarray:
    return rf + betas * premium
