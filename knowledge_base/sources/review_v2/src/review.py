"""Reproducible corrections and a small, interview-friendly decision record.

The versioned public-data snapshot is fixed. No model search, performance target,
live download, or silently invented company financial statement is used here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

import numpy as np
import pandas as pd

from . import config as C
from .capm import capm
from .factors import factor_capm
from .fx_forward import price_forward
from .greeks import bs_greeks
from .hedge import fx_option_premiums, hedge_table, receipt_hedge_comparison, residual_vol
from .ml import forecast_book, long_only_mv_backtest, rmse, hit_rate
from .options import asian_arithmetic, bs_price, crr_price, strike_from_delta
from .returns import simple_returns
from .valuation import equity_vs_market
from .wacc import fcf_haircut_breakeven, irr, npv, tornado, usd_project_inr_cashflows, wacc

REFERENCE = C.DATA_DIR / "reference"


def sample_hedge_paths(spot: float, final_change: float = -.05) -> tuple[list[str], np.ndarray]:
    final = spot * (1 + final_change)
    return ["Weak early, then recovers", "Gradual move", "Move only at the end"], np.array([
        [min(spot * .85, final)] * 11 + [final],
        np.linspace(spot, final, 12),
        [spot] * 11 + [final],
    ])


def hedge_comparison(m: dict, basis: str, hedge_ratio: float = 1.0, final_change: float = -.05) -> pd.DataFrame:
    labels, paths = sample_hedge_paths(m["spot_fx"], final_change)
    result = receipt_hedge_comparison(
        paths, basis, m["put_k"], m["call_k"], m["collar_net"], m["asian_put"],
        m["notional"], m["rf_in"], m["tenor_h"], hedge_ratio,
    )
    result.insert(0, "Path", labels)
    return result


def rebuild(summary: dict | None = None, weekly: pd.DataFrame | None = None) -> dict:
    if summary is None or weekly is None:
        frozen = json.loads((REFERENCE / "inputs.json").read_text())
        path = REFERENCE / "weekly_prices.csv"
        if hashlib.sha256(path.read_bytes()).hexdigest() != frozen["weekly_prices_sha256"]:
            raise ValueError("Frozen data hash changed; review provenance before rebuilding")
        summary = frozen["legacy_summary"]
        weekly = pd.read_csv(path, index_col=0, parse_dates=True)
    m = dict(summary)
    C.EXHIBIT_DIR.mkdir(parents=True, exist_ok=True)
    C.MEMO_DIR.mkdir(parents=True, exist_ok=True)
    weekly = weekly.loc[weekly.index <= pd.Timestamp(m["asof"])].copy()
    rets, ppy = simple_returns(weekly), 52
    rf_in, rf_us = float(m["rf_in"]), float(m["rf_us"])
    rf_w = rf_in / ppy
    cap = capm(rets[C.CLIENT] - rf_w, rets[C.MARKET_IN] - rf_w, rf_in, ppy, C.CLIENT, C.MARKET_IN, C.ERP_LABELLED_IN)
    fac = factor_capm(rets[C.CLIENT] - rf_w, pd.DataFrame({"market": rets[C.MARKET_IN] - rf_w, "fx": rets[C.FX]}), rf_in, ppy, C.CLIENT, {"market": C.ERP_LABELLED_IN})
    rate = wacc(cap.cost_of_equity, C.BOND_YTM, m["we"], C.TAX_RATE)
    valuation = equity_vs_market(m["dps"], cap.cost_of_equity, C.GORDON_G, m["px"])
    m.update(beta=cap.beta, jensen=cap.jensen_annual, r2=cap.r2, ke_capm=cap.cost_of_equity,
             ke_fx=fac.cost_of_equity, erp_sample=cap.sample_premium_annual, wacc=rate,
             wacc_fx=wacc(fac.cost_of_equity, C.BOND_YTM, m["we"], C.TAX_RATE),
             gordon=valuation.gordon_price, premium=valuation.premium_to_gordon, impl_g=valuation.implied_growth)
    cap.ols.as_frame().to_csv(C.EXHIBIT_DIR / "capm_infy.csv")
    fac.beta_frame().to_csv(C.EXHIBIT_DIR / "factor_ke.csv")
    spot = float(m["spot_fx"])
    asof = date.fromisoformat(m["asof"])
    forwards = [price_forward(asof, spot, rf_us, rf_in, float(t), C.SPOT_LAG_BUSINESS_DAYS, C.USD_DAYCOUNT, C.INR_DAYCOUNT).outright for t in range(1, 4)]
    flat = [spot] * 4
    flows = usd_project_inr_cashflows(C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, flat)
    forward_flows = usd_project_inr_cashflows(C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, [spot, *forwards])
    m.update(npv_unhedged=npv(rate, flows), npv_hedged=npv(rate, forward_flows), irr_unhedged=irr(flows), fwd=forwards[0],
             fcf_haircut=fcf_haircut_breakeven(rate, C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, flat))
    scenarios = {"WACC +1pp": npv(rate + .01, flows), "WACC −1pp": npv(rate - .01, flows)}
    for change in (-.05, .05):
        scenarios[f"Future USDINR {change:+.0%}"] = npv(rate, usd_project_inr_cashflows(C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, [spot] + [spot * (1 + change)] * 3))
    scenarios["Annual cash flow −10%"] = npv(rate, usd_project_inr_cashflows(C.PROJECT_CAPEX_USD, tuple(v * .9 for v in C.PROJECT_FCF_USD), flat))
    scenarios["Forward FX path"] = m["npv_hedged"]
    torn = tornado(m["npv_unhedged"], scenarios)
    torn.to_csv(C.EXHIBIT_DIR / "tornado.csv", index=False)

    vol = float(np.log(weekly[C.FX] / weekly[C.FX].shift(1)).std(ddof=1) * np.sqrt(ppy))
    put_k = strike_from_delta(spot, 1, rf_in, vol, -.25, "put", div=rf_us)
    call_k = strike_from_delta(spot, 1, rf_in, vol, .25, "call", div=rf_us)
    put, call = fx_option_premiums(spot, put_k, call_k, 1, rf_in, vol, rf_us)
    asian_put = asian_arithmetic(spot, put_k, 1, rf_in, vol, "put", C.ASIAN_STEPS, C.ASIAN_PATHS, div=rf_us)
    m.update(fx_vol=vol, put_k=put_k, call_k=call_k, put_prem=put, collar_net=put - call,
             asian_put=asian_put, premium_growth=float(np.exp(rf_in)),
             asian=asian_arithmetic(spot, spot, 1, rf_in, vol, "call", C.ASIAN_STEPS, C.ASIAN_PATHS, div=rf_us),
             vanilla_call=bs_price(spot, spot, 1, rf_in, vol, "call", div=rf_us))
    htab = hedge_table(np.linspace(spot * .85, spot * 1.15, 61), m["fwd"], put_k, call_k, put, put - call, m["notional"], m["premium_growth"])
    htab.to_csv(C.EXHIBIT_DIR / "hedge_scenarios.csv", index=False)
    m.update(unhedged_vol=residual_vol(htab["unhedged_inr_m"].to_numpy()), collar_vol=residual_vol(htab["collar_inr_m"].to_numpy()))
    for basis in ("terminal", "average"):
        hedge_comparison(m, basis).to_csv(C.EXHIBIT_DIR / f"hedge_{basis}_receipts.csv", index=False)
    g = bs_greeks(spot, put_k, 1, rf_in, vol, "put", rf_us)
    h, v, day = spot * 1e-4, 1e-5, 1e-4
    price = lambda s=spot, sigma=vol, tenor=1: bs_price(s, put_k, tenor, rf_in, sigma, "put", rf_us)
    validation = pd.DataFrame([
        ("Price", price(), crr_price(spot, put_k, 1, rf_in, vol, 500, "put", div=rf_us)),
        ("Delta", g.delta, (price(s=spot + h) - price(s=spot - h)) / (2 * h)),
        ("Gamma", g.gamma, (price(s=spot + h) - 2 * price() + price(s=spot - h)) / h ** 2),
        ("Vega per unit volatility", g.vega, (price(sigma=vol + v) - price(sigma=vol - v)) / (2 * v)),
        ("Theta per year", g.theta, (price(tenor=1 - day) - price(tenor=1 + day)) / (2 * day)),
    ], columns=["Quantity", "Formula", "Independent numerical check"])
    validation["Absolute difference"] = abs(validation["Formula"] - validation["Independent numerical check"])
    validation.to_csv(C.EXHIBIT_DIR / "option_validation.csv", index=False)

    book = rets[list(C.BOOK)].dropna()
    blend, forecasts = forecast_book(book, rets[C.MARKET_IN], rets[C.FX], C.BOOK)
    for name, forecast in forecasts.items():
        forecast.to_csv(C.EXHIBIT_DIR / f"forecast_{name.replace('.NS', '')}.csv", index_label="information_date")
    ridge_panel = pd.DataFrame({name: forecasts[name]["ridge_blend"] for name in C.BOOK})
    expanding_panel = pd.DataFrame({name: forecasts[name]["hist"] for name in C.BOOK})
    bt = long_only_mv_backtest(book, {"gb_mv": blend, "ridge_mv": ridge_panel, "expanding_mv": expanding_panel}, rets[C.MARKET_IN], rf_w, ppy)
    metrics = pd.DataFrame({"sharpe": bt.sharpe, "ann_mean": bt.ann_mean, "ann_vol": bt.ann_vol,
                            "max_drawdown": bt.max_drawdown, "annual_turnover": bt.turnover,
                            "beta": bt.beta, "jensen": bt.jensen, "tracking_error": bt.tracking_error, "info_ratio": bt.info_ratio})
    metrics.to_csv(C.EXHIBIT_DIR / "ml_backtest.csv")
    bt.returns.to_csv(C.EXHIBIT_DIR / "portfolio_returns.csv", index_label="date")
    bt.wealth.to_csv(C.EXHIBIT_DIR / "portfolio_nav.csv", index_label="date")
    bt.weights.to_csv(C.EXHIBIT_DIR / "portfolio_weight_path.csv", index=False)
    bt.trades.to_csv(C.EXHIBIT_DIR / "portfolio_trades.csv", index=False)
    pd.DataFrame({"last": bt.last_weights, "average": bt.avg_weights}).to_csv(C.EXHIBIT_DIR / "ml_last_weights.csv")
    for name, forecast in forecasts.items():
        forecast.to_csv(C.EXHIBIT_DIR / f"forecast_{name.replace('.NS', '')}.csv", index_label="information_date")
    forecasts[C.CLIENT].to_csv(C.EXHIBIT_DIR / "ml_infy_oos.csv")
    f = forecasts[C.CLIENT]
    m.update(rmse_gb=rmse(f.y.to_numpy(), f.gb.to_numpy()), rmse_ridge=rmse(f.y.to_numpy(), f.ridge.to_numpy()),
             rmse_hist=rmse(f.y.to_numpy(), f["hist"].to_numpy()), hit_gb=hit_rate(f.y.to_numpy(), f.gb.to_numpy()))
    for key, prefix in (("hist_mv", "hist"), ("gb_mv", "gb"), ("ridge_mv", "ridge"), ("expanding_mv", "expanding")):
        m.update({f"sh_{prefix}": bt.sharpe[key], f"dd_{prefix}": bt.max_drawdown[key],
                  f"turnover_{prefix}": bt.turnover[key], f"beta_{prefix}": bt.beta[key],
                  f"jensen_{prefix}": bt.jensen[key], f"te_{prefix}": bt.tracking_error[key], f"ir_{prefix}": bt.info_ratio[key]})
    m.update(sh_nifty=bt.sharpe["nifty"], sh_inv=bt.sharpe["inv_vol"], sh_eq=bt.sharpe["equal"])
    winner = metrics.sharpe.idxmax()
    m.update(audit_version=2, reviewed_at=date.today().isoformat(), weekly_end=weekly.index[-1].date().isoformat(),
             oos_start=bt.returns.index[0].date().isoformat(), oos_end=bt.returns.index[-1].date().isoformat(), oos_weeks=len(bt.returns),
             sample_winner=winner, strategy_used="Historical allocation is the interpretable reference rule, not a proven trading recommendation.",
             avg_w_txt=" · ".join(f"{name} {weight:.0%}" for name, weight in bt.avg_weights.items()),
             ml_verdict=f"Sample Sharpe: trailing historical {m['sh_hist']:.2f}, expanding-mean baseline {m['sh_expanding']:.2f}, Ridge {m['sh_ridge']:.2f}, gradient boosting {m['sh_gb']:.2f}. Compare ML first with the expanding baseline: it shares the same history window and allocation procedure. Highest sample Sharpe: {winner}. No untouched holdout; do not claim a durable edge or dividend-matched Nifty outperformance.",
             debt_line="Debt is very small in the frozen capital-structure input, so WACC is approximately, not exactly, cost of equity.")
    m["reco_headline"] = f"Illustrative expansion NPV is INR {m['npv_unhedged']/1e7:.1f} crore at {rate:.2%} WACC; a {m['fcf_haircut']:.1%} cash-flow shortfall removes the margin. This is not an Infosys forecast. Match the hedge to the receipt's fixing convention and hedge only confirmed exposure."
    m["hedge_call"] = "For a confirmed final-fixing receipt, a collar offers a floor and capped upside at a small model premium; a forward offers certainty. For an average-indexed receipt paid at year-end, the average-rate put matches the exposure. Neither is universally best."
    from .plots import plot_tornado, plot_hedge, plot_ml_nav
    plot_tornado(torn)
    plot_hedge(htab)
    plot_ml_nav(bt.wealth)
    write_review_note(m, metrics, validation)
    (C.EXHIBIT_DIR / "summary.json").write_text(json.dumps(m, indent=2) + "\n")
    return m


def write_review_note(m: dict, metrics: pd.DataFrame, validation: pd.DataFrame) -> None:
    lines = [
        "# Asset Pricing and Hedging — reviewed decision note", "",
        f"Market snapshot: {m['asof']}; completed weekly data through {m['weekly_end']}. Reviewed build: {m['reviewed_at']}.",
        "This is a 2026 extension/review. Do not present these results as having been available during May–July 2025.", "",
        "## 1. Should the company expand?", m["reco_headline"], "",
        "All dollar cash flows are hypothetical, unlevered cash after operating costs, cash tax, maintenance investment and working capital. They are not sales or dividends.", "",
        "| USD million | Year 1 | Year 2 | Year 3 |", "|---|---:|---:|---:|",
        "| Customer collections | 100 | 110 | 120 |", "| Cash operating costs and tax | −60 | −65 | −70 |",
        "| Reinvestment and working capital | −8 | −9 | −10 |", "| Free cash flow | 32 | 36 | 40 |", "",
        f"Spend USD 80m today; zero salvage after year 3. CAPM: {m['rf_in']:.2%} + {m['beta']:.3f} × {m['erp']:.2%} = {m['ke_capm']:.2%}. WACC: {m['wacc']:.2%}. Market-plus-FX cross-check: {m['ke_fx']:.2%}.",
        f"Gordon value: INR {m['gordon']:.2f} per share vs the saved INR {m['px']:.2f} price, at 5% assumed perpetual growth. A model gap is not proof of mispricing.",
        "The INR WACC is a teaching proxy for a project assumed to have similar risk to the reference company, not a project-specific independently estimated hurdle. Future FX shocks leave today's investment unchanged.", "",
        "## 2. Which currency protection fits the receipt?", m["hedge_call"], "",
        f"Separate USD {m['notional']/1e6:.0f}m Treasury receipt contract, not project year-one FCF. Put strike {m['put_k']:.3f}; call strike {m['call_k']:.3f}. Upfront model collar premium {m['collar_net']:.4f} and average-rate PUT premium {m['asian_put']:.4f} INR/USD.",
        "Compare the same monthly FX paths and the same receipt contract. All cash settles at year-end; an average-indexed year-end receipt is not twelve monthly cash collections. Premiums are financed to settlement. Partial hedging leaves part of the downside unprotected.",
        "A terminal collar can miss an average-indexed floor; an average-rate put can miss a final-fixing floor. Matching exposure matters more than choosing the cheapest option.",
        "Average-rate pricing uses 12 future fixings, 40,000 risk-neutral paths, seed 7. Scenario paths are illustrations, not forecasts or probability-weighted risk measures. Realised volatility, flat rates, no dealer spread, basis adjustment, default, collateral or hedge accounting.", "",
        "## 3. Does ML improve allocation?",
        f"Common evaluation period {m['oos_start']} to {m['oos_end']} ({m['oos_weeks']} weeks). Both Ridge and gradient boosting feed an allocation strategy: 80% expanding historical mean + 20% model forecast. Also test 100% expanding historical mean with the SAME window and optimiser, so a longer history is not mistaken for ML value. Training-only Ridge scaling, 104-week warm-up, refit every four weeks.",
        "All active strategies and equal weight rebalance every four weeks. Real holdings drift between trades. The allocation search checks every permitted 5-percentage-point target-weight combination: nonnegative, 100% invested and a 35% cap at rebalance. It chooses the highest estimated Sharpe on this fixed grid, NOT a continuous optimum. Costs include initial entry; subsequent one-way turnover is half the sum of absolute weight changes, charged at 10bps. Index reference has no charged cost.", "",
        "| Strategy | Excess Sharpe | Annual mean | Annual vol | Max drawdown |", "|---|---:|---:|---:|---:|",
    ]
    lines += [f"| {name} | {row.sharpe:.2f} | {row.ann_mean:.1%} | {row.ann_vol:.1%} | {row.max_drawdown:.1%} |" for name, row in metrics.iterrows()]
    lines += ["", m["ml_verdict"], "",
              "**Benchmark limitation:** Yahoo-adjusted stock returns include dividend adjustments; ^NSEI is a price-only index. This is NOT a fair dividend-inclusive market-outperformance test. A Nifty TRI or dividend-adjusted investable Nifty ETF is required before claiming that. The strongest comparison here is between rules on the SAME five-asset universe.",
              "Fixed five-name universe is chosen retrospectively. Constant 6.50% risk-free proxy is not a historical cash-rate series. End-of-week close execution is idealised; no slippage, taxes, market impact or liquidity constraint. Out-of-sample predictions are not an untouched strategy-selection holdout. No hyperparameter/weight tuning to preserve a résumé score.", "",
              "## 4. What changed from the original résumé?",
              "The old 0.30 vs 0.22 numbers used a clipped allocation heuristic, constant weights between rebalances and different benchmark cost assumptions. They are superseded, not a target to recover.",
              "The average-rate call illustration did not establish an exporter hedge. It is now supplemented by an actual average-rate put and path-by-path net receipt comparisons. Ridge now participates in allocation, not only forecast RMSE.",
              "CAPM, factor, WACC, Gordon and project DCF remain simple teaching models with labelled inputs. The frozen dividend/capital-structure inputs are inherited values, not independently reconstructed company filings. The archived ADR quote is not independent evidence of model accuracy: IV was backed out from that same quote, and the raw quote snapshot is unavailable.", "",
              "## 5. Numerical checks", "FX put formula vs 500-step tree, plus analytic Greeks vs central finite differences:", "",
              "| Quantity | Formula | Numerical | Absolute difference |", "|---|---:|---:|---:|"]
    lines += [f"| {row.iloc[0]} | {row.iloc[1]:.6f} | {row.iloc[2]:.6f} | {row.iloc[3]:.6f} |" for _, row in validation.iterrows()]
    lines += ["", "## Reproduce", "Run `python run_ic_pack.py --offline --no-open` using the checked-in reference snapshot. Tests: `python -m unittest discover -s tests -v`.", "",
              "Sources: [NSE price vs total return](https://www.niftyindices.com/resources/index-concepts/total-return-index), [scikit-learn training-only preprocessing](https://scikit-learn.org/stable/common_pitfalls.html).", ""]
    (C.MEMO_DIR / "ic_note.md").write_text("\n".join(lines))
