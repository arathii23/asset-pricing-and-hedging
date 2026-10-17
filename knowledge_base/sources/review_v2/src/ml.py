"""Easy–medium ML allocation challenger. No LSTM, no look-ahead.

Walk-forward Ridge and histogram gradient boosting forecast next-week equity
returns. Predicted μ (shrunk toward the expanding mean) replaces historical μ
inside long-only mean-variance. The models are challengers: the IC keeps the
simpler historical-return rule unless ML improves out-of-sample results.

Features are course objects: own lags, Nifty, USDINR factor, rolling vol.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.covariance import LedoitWolf
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config as C
from .portfolio import cap_weights, long_only_tangency


def _lags(s: pd.Series, lags: tuple[int, ...]) -> pd.DataFrame:
    return pd.concat({f"l{k}": s.shift(k) for k in lags}, axis=1)


def design_matrix(
    own: pd.Series,
    market: pd.Series,
    fx: pd.Series,
) -> pd.DataFrame:
    """Information at t: lags of own return, Nifty, USDINR, 8-week vols."""
    parts = {
        "own": _lags(own, (0, 1, 3)),
        "mkt": _lags(market, (0, 1)),
        "fx": _lags(fx, (0, 1)),
    }
    x = pd.concat(parts, axis=1)
    x.columns = [f"{a}_{b}" for a, b in x.columns]
    x["own_vol8"] = own.rolling(8).std()
    x["fx_vol8"] = fx.rolling(8).std()
    return x


def walk_forward_reg(
    y: pd.Series,
    x: pd.DataFrame,
    min_train: int = C.ML_MIN_TRAIN,
    refit_every: int = C.ML_REFIT_EVERY,
) -> pd.DataFrame:
    """Predict y_{t+1} using X_t. Fits only on rows strictly before t."""
    aligned = pd.concat([y.rename("y"), x], axis=1).dropna()
    feat = [c for c in aligned.columns if c != "y"]
    n = len(aligned)
    pred_ridge = np.full(n, np.nan)
    pred_gb = np.full(n, np.nan)
    ridge = gb = None
    last_fit = -10**9
    for i in range(min_train, n):
        if ridge is None or (i - last_fit) >= refit_every:
            y_tr = aligned["y"].iloc[:i].to_numpy()
            x_tr = aligned[feat].iloc[:i].to_numpy()
            ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(x_tr, y_tr)
            gb = HistGradientBoostingRegressor(
                max_depth=3,
                max_iter=80,
                learning_rate=0.08,
                random_state=7,
            ).fit(x_tr, y_tr)
            last_fit = i
        x_i = aligned[feat].iloc[i : i + 1].to_numpy()
        pred_ridge[i] = float(ridge.predict(x_i)[0])
        pred_gb[i] = float(gb.predict(x_i)[0])
    out = aligned[["y"]].copy()
    out["ridge"] = pred_ridge
    out["gb"] = pred_gb
    out["hist"] = aligned["y"].shift(1).expanding().mean()
    out["blend"] = (1.0 - C.ML_BLEND) * out["hist"] + C.ML_BLEND * out["gb"]
    out["ridge_blend"] = (1.0 - C.ML_BLEND) * out["hist"] + C.ML_BLEND * out["ridge"]
    return out.dropna()


def rmse(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def hit_rate(y_sign: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.mean(np.sign(yhat) == np.sign(y_sign)))


def _beta(r: np.ndarray, rm: np.ndarray) -> float:
    """Course CAPM β = Cov(Rp, Rm) / Var(Rm). Same slope as excess-return OLS if rf is constant."""
    var_m = float(np.var(rm, ddof=1))
    if var_m <= 1e-18:
        return 0.0
    return float(np.cov(r, rm, ddof=1)[0, 1] / var_m)


def _jensen_annual(r: np.ndarray, rm: np.ndarray, beta: float, rf_ann: float, ppy: int) -> float:
    """α = (E[Rp] − rf) − β(E[Rm] − rf), annualised. Same object as the INFY Jensen line."""
    return (float(np.mean(r)) * ppy - rf_ann) - beta * (float(np.mean(rm)) * ppy - rf_ann)


def _te_ir(r: np.ndarray, rm: np.ndarray, ppy: int) -> tuple[float, float]:
    """Tracking error and information ratio versus the benchmark."""
    active = r - rm
    te = float(np.std(active, ddof=1) * np.sqrt(ppy))
    ir = float(np.mean(active) * ppy / te) if te > 1e-12 else 0.0
    return te, ir


@dataclass
class MVBacktest:
    wealth: pd.DataFrame
    last_weights: pd.Series
    avg_weights: pd.Series
    sharpe: dict[str, float]
    ann_mean: dict[str, float]
    ann_vol: dict[str, float]
    max_drawdown: dict[str, float]
    turnover: dict[str, float]
    beta: dict[str, float]
    jensen: dict[str, float]
    tracking_error: dict[str, float]
    info_ratio: dict[str, float]
    returns: pd.DataFrame
    weights: pd.DataFrame
    trades: pd.DataFrame


def long_only_mv_backtest(
    rets: pd.DataFrame,
    pred_mu: pd.DataFrame | dict[str, pd.DataFrame],
    market: pd.Series,
    rf_per_period: float,
    ppy: int,
    lookback: int = C.ML_COV_LOOKBACK,
) -> MVBacktest:
    """
    Monthly rebalance on weekly data. Expected returns use only data known at
    t; covariance is Ledoit-Wolf shrinkage on the trailing year. All optimized
    books are long-only, capped at rebalance, and charged transaction costs.
    Holdings drift with asset returns between trades. Equal weight is rebalanced
    and charged on the same schedule. Nifty is a cost-free PRICE-index reference.
    """
    names = list(rets.columns)
    panels = {"gb_mv": pred_mu} if isinstance(pred_mu, pd.DataFrame) else pred_mu
    idx = rets.dropna().index
    for panel in panels.values():
        idx = idx.intersection(panel.dropna(how="any").index)
    keys = [*panels, "hist_mv", "inv_vol", "equal"]
    rec = {k: [] for k in (*keys, "nifty")}
    dates = []
    equal_w = np.ones(len(names)) / len(names)
    held = {key: equal_w.copy() for key in keys}
    turnover_total = {k: 0.0 for k in held}
    hist_w_path: list[np.ndarray] = []
    weight_rows, trade_rows = [], []
    last_hist_target = equal_w.copy()
    cost_rate = C.TRANSACTION_COST_BPS / 10_000.0
    loc = rets.index.get_indexer(idx)
    for step, (pos, t) in enumerate(zip(loc, idx)):
        nxt = pos + 1
        if nxt >= len(rets):
            break
        dt_next = rets.index[nxt]
        r_next = rets.iloc[nxt][names].to_numpy()
        if dt_next not in market.index or not np.isfinite(market.loc[dt_next]) or not np.isfinite(r_next).all():
            continue
        window = rets.iloc[max(0, pos + 1 - lookback) : pos + 1]
        if len(window) < 26:
            continue
        costs = {k: 0.0 for k in held}
        if len(dates) % C.REBALANCE_WEEKS == 0:
            cov = LedoitWolf().fit(window.to_numpy()).covariance_ * ppy
            mu_hist = window.mean().to_numpy() * ppy
            rf_ann = rf_per_period * ppy
            vol = np.sqrt(np.clip(np.diag(cov), 1e-12, None))
            targets = {
                **{key: long_only_tangency(panel.loc[t, names].to_numpy() * ppy, cov, rf_ann, cap=C.MAX_WEIGHT)
                   for key, panel in panels.items()},
                "hist_mv": long_only_tangency(mu_hist, cov, rf_ann, cap=C.MAX_WEIGHT),
                "inv_vol": cap_weights(1.0 / vol, C.MAX_WEIGHT),
                "equal": equal_w.copy(),
            }
            for key, target in targets.items():
                one_way_turnover = 1.0 if not dates else 0.5 * float(np.abs(target - held[key]).sum())
                turnover_total[key] += one_way_turnover
                costs[key] = one_way_turnover * cost_rate
                held[key] = target
                trade_rows.append({"decision_date": t, "return_date": dt_next, "strategy": key,
                                   "one_way_turnover": one_way_turnover, "cost_fraction": costs[key],
                                   **dict(zip(names, target))})
            last_hist_target = targets["hist_mv"].copy()
        r_m = float(market.loc[dt_next])
        hist_w_path.append(held["hist_mv"].copy())
        for key in keys:
            weight_rows.append({"date": dt_next, "strategy": key, **dict(zip(names, held[key]))})
            gross = float(held[key] @ r_next)
            rec[key].append((1.0 - costs[key]) * (1.0 + gross) - 1.0)
            held[key] = held[key] * (1 + r_next) / (1 + gross)
        rec["nifty"].append(r_m)
        dates.append(rets.index[nxt])
    wealth_r = pd.DataFrame(rec, index=pd.DatetimeIndex(dates))
    wealth = (1.0 + wealth_r).cumprod()
    sharpe, means, vols, drawdowns = {}, {}, {}, {}
    beta, jensen, te, ir = {}, {}, {}, {}
    rf_ann = rf_per_period * ppy
    rm_s = wealth_r["nifty"]
    for col in wealth_r.columns:
        r = wealth_r[col].dropna()
        means[col] = float(r.mean()) * ppy
        vols[col] = float(r.std(ddof=1)) * np.sqrt(ppy)
        sharpe[col] = (means[col] - rf_ann) / vols[col] if vols[col] > 0 else 0.0
        nav = wealth[col].dropna()
        peaks = np.maximum.accumulate(np.r_[1.0, nav.to_numpy()])[1:]
        drawdowns[col] = float(np.min(nav.to_numpy() / peaks - 1.0))
        pair = pd.concat([r, rm_s], axis=1, join="inner").dropna()
        rp = pair.iloc[:, 0].to_numpy()
        rmk = pair.iloc[:, 1].to_numpy()
        b = _beta(rp, rmk)
        beta[col] = b
        jensen[col] = _jensen_annual(rp, rmk, b, rf_ann, ppy)
        te[col], ir[col] = _te_ir(rp, rmk, ppy)
    years = len(wealth_r) / ppy if len(wealth_r) else 1.0
    annual_turnover = {
        key: value / years for key, value in turnover_total.items()
    }
    annual_turnover["nifty"] = 0.0
    avg_w = (
        np.mean(np.vstack(hist_w_path), axis=0) if hist_w_path else equal_w
    )
    return MVBacktest(
        wealth=wealth,
        last_weights=pd.Series(last_hist_target, index=names),
        avg_weights=pd.Series(avg_w, index=names),
        sharpe=sharpe,
        ann_mean=means,
        ann_vol=vols,
        max_drawdown=drawdowns,
        turnover=annual_turnover,
        beta=beta,
        jensen=jensen,
        tracking_error=te,
        info_ratio=ir,
        returns=wealth_r,
        weights=pd.DataFrame(weight_rows),
        trades=pd.DataFrame(trade_rows),
    )


def forecast_book(
    rets: pd.DataFrame,
    market: pd.Series,
    fx: pd.Series,
    names: tuple[str, ...],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Blended μ panel for MV, plus per-name walk-forward tables."""
    tables: dict[str, pd.DataFrame] = {}
    blend = {}
    for n in names:
        x = design_matrix(rets[n], market, fx)
        wf = walk_forward_reg(rets[n].shift(-1), x)
        tables[n] = wf
        blend[n] = wf["blend"]
    return pd.DataFrame(blend), tables
