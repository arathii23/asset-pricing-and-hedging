"""Multifactor OLS. Default: market + USDINR (exporter / Mastercard hook)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .mathutil import OLSResult, add_intercept, ols


@dataclass
class FactorResult:
    ticker: str
    names: tuple[str, ...]
    alpha: float
    betas: dict[str, float]
    r2: float
    n: int
    ppy: int
    rf_annual: float
    premia: dict[str, float]
    cost_of_equity: float
    ols: OLSResult

    def beta_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "beta": [self.betas[n] for n in self.names],
                "premium": [self.premia[n] for n in self.names],
                "contrib": [self.betas[n] * self.premia[n] for n in self.names],
            },
            index=list(self.names),
        )


def factor_capm(
    asset_excess: pd.Series,
    factors: pd.DataFrame,
    rf_annual: float,
    ppy: int,
    ticker: str,
    premia_override: dict[str, float] | None = None,
) -> FactorResult:
    names = tuple(factors.columns)
    aligned = pd.concat([asset_excess.rename("y"), factors], axis=1, join="inner").dropna()
    y = aligned["y"].to_numpy()
    X = add_intercept(aligned[list(names)].to_numpy())
    fit = ols(y, X, names=("alpha", *names))
    alpha = float(fit.beta[0])
    betas = {n: float(fit.beta[i + 1]) for i, n in enumerate(names)}
    hist = {n: float(aligned[n].mean()) * ppy for n in names}
    premia = dict(hist)
    if premia_override:
        premia.update(premia_override)
    ke = rf_annual + sum(betas[n] * premia[n] for n in names)
    return FactorResult(
        ticker=ticker,
        names=names,
        alpha=alpha,
        betas=betas,
        r2=float(fit.r2),
        n=fit.n,
        ppy=ppy,
        rf_annual=rf_annual,
        premia=premia,
        cost_of_equity=ke,
        ols=fit,
    )
