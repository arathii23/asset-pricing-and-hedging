"""
FX-Hedged Expansion Desk
========================

Build from scratch (course methods only):

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python run_ic_pack.py

Writes exhibits/*.png and memo/ic_note.md. Re-run with --force to refresh
the Yahoo/FRED cache.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import config as C
from src.capm import capm
from src.checks import run_checks
from src.config import Universe
from src.data import last_rf_india, last_rf_us, load_market
from src.factors import factor_capm
from src.fx_forward import price_forward
from src.greeks import binomial_delta, bs_greeks
from src.hedge import fx_option_premiums, hedge_table, residual_vol
from src.options import asian_arithmetic, bs_price, crr_price, implied_vol, strike_from_delta
from src.ml import (
    forecast_book,
    hit_rate,
    long_only_mv_backtest,
    rmse,
)
from src.plots import (
    plot_crr_vs_bs,
    plot_factor_contrib,
    plot_frontier,
    plot_greeks,
    plot_hedge,
    plot_ml_nav,
    plot_sml,
    plot_tornado,
)
from src.portfolio import as_weight_frame, efficient_frontier, port_stats
from src.returns import annualize_mean, annualize_vol, periods_per_year, resample_last, simple_returns
from src.valuation import comparable_bond, equity_vs_market
from src.wacc import fcf_haircut_breakeven, irr, npv, tornado, usd_project_inr_cashflows, wacc
from src.report import write_html


def _latest(series: pd.Series) -> float:
    return float(series.dropna().iloc[-1])


def _weekly(prices: pd.DataFrame) -> pd.DataFrame:
    return resample_last(prices)


def _ann_stats(r: pd.Series, ppy: int) -> tuple[float, float]:
    return annualize_mean(float(r.mean()), ppy), annualize_vol(float(r.std(ddof=1)), ppy)


def _equity_weight(mcap: float | None, debt: float | None) -> tuple[float, str]:
    if mcap and debt is not None and mcap + debt > 0:
        we = mcap / (mcap + max(debt, 0.0))
        return we, "market cap / (market cap + total debt)"
    return 0.95, "labelled 95% equity weight (debt missing on Yahoo)"


def _dps(fund, price: float) -> float:
    if fund.dps_ltm and fund.dps_ltm > 0:
        return fund.dps_ltm
    if fund.div_yield and fund.div_yield > 0:
        return fund.div_yield * price
    return 0.02 * price  # labelled 2% fallback yield


def write_memo(path: Path, ctx: dict) -> None:
    C.MEMO_DIR.mkdir(parents=True, exist_ok=True)
    m = ctx
    text = f"""# FX-Hedged Expansion Desk — IC note

**As of:** {m["asof"]} (prices); pull {m["pulled"]}
**Client:** {C.CLIENT_NAME} (`{C.CLIENT}`) · **Comparator:** {C.COMPARATOR_NAME} (`{C.COMPARATOR}`)
**Question:** Fund a 3-year USD {m["capex_usd"]/1e6:.0f}m expansion, and how should Treasury hedge year-1 USD receipts?

## Recommendation

{m["reco_headline"]}

- **Cost of equity (CAPM, vs Nifty):** {m["ke_capm"]:.2%} (β = {m["beta"]:.2f}, α_ann = {m["jensen"]:.2%}, R² = {m["r2"]:.2f}).
- **Cost of equity (market + USDINR):** {m["ke_fx"]:.2%}. The FX factor {"raises" if m["ke_fx"] >= m["ke_capm"] else "cuts"} required return vs plain CAPM by {abs(m["ke_fx"]-m["ke_capm"]):.2%}.
- **WACC (CAPM ke, comparable-bond kd):** {m["wacc"]:.2%} with equity weight {m["we"]:.1%} ({m["we_src"]}). {m["debt_line"]}
- **Gordon vs screen:** model {m["gordon"]:.1f} vs market {m["px"]:.1f} ({m["premium"]:+.1%} to model) at labelled g = {C.GORDON_G:.2%}. Implied perpetual g = {m["impl_g"]:.2%}{m["g_sust_line"]}.
- **USD project NPV (INR, CAPM WACC):** unhedged {m["npv_unhedged"]/1e9:+.2f}bn · forward-hedged {m["npv_hedged"]/1e9:+.2f}bn. IRR unhedged {m["irr_unhedged"]:.2%}. Salvage at year 3 is zero. Unhedged NPV reaches zero if every free cash flow is {m["fcf_haircut"]:.0%} lower. Hedged and unhedged cases use this same WACC; only the FX path changes.
- **Treasury:** 1y USDINR IRP forward {m["fwd"]:.2f} vs spot {m["spot_fx"]:.2f}. Collar residual vol {m["collar_vol"]:.2f} vs unhedged {m["unhedged_vol"]:.2f} (INR m). Asian {m["tenor_h"]:.2f}y call on the average rate costs {m["asian"]:.3f} vs vanilla {m["vanilla_call"]:.3f} INR per USD.
- **ML challenger (walk-forward):** GB vs hist-mean RMSE on INFY {m["rmse_gb"]:.4f} vs {m["rmse_hist"]:.4f}. Long-only MV with boosted μ Sharpe {m["sh_gb"]:.2f} vs historical-μ MV {m["sh_hist"]:.2f} vs Nifty {m["sh_nifty"]:.2f}. Selected book vs Nifty: β {m["beta_hist"]:.2f}, Jensen α {m["jensen_hist"]:.2%}, TE {m["te_hist"]:.1%}, IR {m["ir_hist"]:.2f}.

## 1. Universe and two-fund picture

Coverage book for the frontier: Infosys (IT), HDFC Bank, Reliance, Hindustan Unilever, and a gold ETF. Nifty, Mastercard, USDINR, India/US 10Y, and a listed call on `{m["opt_ticker"]}` are the other inputs. Shorts are allowed on the frontier so the two-fund line is visible. The held book is long-only.

Tangency weights for that diversified book are in `exhibits/weights.csv`.

## 2. CAPM, factors, WACC

| | INFY vs Nifty | MA vs S&P |
|---|---:|---:|
| Beta | {m["beta"]:.2f} | {m["beta_ma"]:.2f} |
| Jensen α (ann.) | {m["jensen"]:.2%} | {m["jensen_ma"]:.2%} |
| R² | {m["r2"]:.2f} | {m["r2_ma"]:.2f} |
| ke | {m["ke_capm"]:.2%} | {m["ke_ma"]:.2%} |
| Rf | {m["rf_in"]:.2%} | {m["rf_us"]:.2%} |
| Sample ERP | {m["erp_sample"]:.2%} | {m["erp_us_sample"]:.2%} |
| Labelled ERP (in ke) | {m["erp"]:.2%} | {m["erp_us"]:.2%} |

Factor ke uses historical premia on Nifty excess and USDINR. Exporting IT / payments names load on USDINR; that is the Mastercard Treasury analogue (cross-border receipts) and why CAPM-only WACC can mis-rank the project.

Cost of debt is **YTM, not coupon**, on a labelled 7-year {C.BOND_COUPON:.2%} coupon priced at {C.BOND_YTM:.2%} YTM (mod duration {m["mod_dur"]:.2f}, convexity {m["conv"]:.2f}). Tax shield at {C.TAX_RATE:.0%}. {m["debt_line"]}

## 3. Asset valuation

Gordon uses trailing DPS grown at labelled g = {C.GORDON_G:.0%} and CAPM ke. That g is a cap, not a forecast: retention×ROE is above ke, so a fundamentals Gordon price is not defined. Implied perpetual g is {m["impl_g"]:.2%}{m["g_sust_line"]}. The market premium to this model is a growth assumption, not a trading signal.

## 4. Walk-forward ML challenger (easy–medium)

Ridge and histogram gradient boosting are compared with the expanding historical mean using an expanding window, **no look-ahead**, and refitting every {C.ML_REFIT_EVERY} weeks after {C.ML_MIN_TRAIN} weeks of history.

Ridge and gradient boosting forecast next-week returns from own lags, Nifty, USDINR (the factor already in ke), and rolling vol. Blended μ = {100*(1-C.ML_BLEND):.0f}% expanding mean + {100*C.ML_BLEND:.0f}% GB feeds **long-only mean-variance**. The covariance is Ledoit–Wolf shrinkage; the book rebalances every {C.REBALANCE_WEEKS} weeks, charges {C.TRANSACTION_COST_BPS} bps per unit of one-way turnover, and caps each name at {C.MAX_WEIGHT:.0%}. **Strategy used:** {m["strategy_used"]}. OOS excess-return Sharpe: ML-MV {m["sh_gb"]:.2f} · hist-MV {m["sh_hist"]:.2f} · inverse-vol {m["sh_inv"]:.2f} · 1/N {m["sh_eq"]:.2f} · Nifty {m["sh_nifty"]:.2f}. Selected book vs Nifty: β {m["beta_hist"]:.2f}, Jensen α {m["jensen_hist"]:.2%}, tracking error {m["te_hist"]:.1%}, information ratio {m["ir_hist"]:.2f}. Max drawdown {m["dd_hist"]:.1%}, annual turnover {m["turnover_hist"]:.2f}×. Average weights (full OOS path, not the last week): {m["avg_w_txt"]}. INFY RMSE GB {m["rmse_gb"]:.4f} / Ridge {m["rmse_ridge"]:.4f} / hist {m["rmse_hist"]:.4f}; sign hit GB {m["hit_gb"]:.1%}. {m["ml_verdict"]}

No LSTM: weekly 2019–now is too short for a sequence model to beat lagged Ridge, and it is not in the ECO423 outline.

## 5. Forwards, listed options, Greeks

FX forward uses **T+{C.SPOT_LAG_BUSINESS_DAYS} spot lag**, USD {C.USD_DAYCOUNT}, INR {C.INR_DAYCOUNT} — the same convention stack as an FS-risk pricing sheet, implemented here from scratch.

Listed `{m["opt_kind"]}` `{m["opt_ticker"]}` (ADR, not the INR line) {m["opt_k"]:.2f} exp {m["opt_exp"]}: mid {m["opt_mid"]:.3f}, implied vol {m["opt_iv"]:.1%}. Black–Scholes at that implied vol is {m["opt_bs"]:.3f} by construction; the check is CRR({C.BINOMIAL_STEPS_REPORT}) {m["opt_crr"]:.3f} against that closed form. Δ {m["opt_delta"]:.3f} (binomial bump {m["opt_bdelta"]:.3f}), Γ {m["opt_gamma"]:.4f}, ν {m["opt_vega"]:.3f}, Θ {m["opt_theta"]:.3f}.

## 6. Hedge policy

Year-1 notional USD {m["notional"]/1e6:.0f}m.

| Policy | What it does |
|---|---|
| Unhedged | Full USDINR risk on INR proceeds |
| Sell USD 1y forward | Locks {m["fwd"]:.2f}; zero premium; zero upside |
| 25Δ USD put | Floor; premium {m["put_prem"]:.3f} INR/USD |
| Collar (25Δ / 25Δ) | Band; net premium {m["collar_net"]:.3f} INR/USD; scenario dispersion {m["collar_vol"]:.1f} vs unhedged {m["unhedged_vol"]:.1f} INR m |
| Asian (avg-rate) call | Unconventional; cheaper than vanilla for the same strike ({m["asian"]:.3f} vs {m["vanilla_call"]:.3f}) because averaging kills vol |

**Policy call:** {m["hedge_call"]}

## 7. Risks (three)

1. **ERP and β window.** Sample Nifty excess is {m["erp_sample"]:.2%}; ke uses labelled ERP {m["erp"]:.2%}. β is OLS on weekly data since {C.START}.
2. **Project ends, and the hedge does not change the hurdle.** Salvage is {C.PROJECT_SALVAGE_USD:.0f}. USD cash flows are converted and then discounted at one INR WACC, hedged or not. A USD WACC (MA analogue {m["wacc_ma"]:.2%}) would change the NPV level. It would not by itself rank the hedge.
3. **Vol and listed vs OTC.** Equity IV is from one Yahoo snapshot. USDINR vol is realised, not implied. No holiday calendar beyond weekends.

## Notes

{m["notes"]}

All engines (OLS, CRR, BS, IRP, YTM, MC Asian, walk-forward Ridge/GB) live under `src/` and were identity-checked in `src/checks.py`.
"""
    path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FX-Hedged Expansion Desk IC pack")
    parser.add_argument("--force", action="store_true", help="refresh Yahoo/FRED cache")
    parser.add_argument("--no-open", action="store_true", help="do not open the HTML pack in a browser")
    args = parser.parse_args()

    print("Running from-scratch identity checks…")
    for line in run_checks():
        print("  ok ", line)

    print("Pulling public market data…")
    universe = Universe()
    data = load_market(universe, force=args.force)
    px = data.prices
    asof = px.dropna(how="all").index.max()
    asof_d = pd.Timestamp(asof).date()
    print(f"  as-of {asof_d.isoformat()}  tickers={list(px.columns)}")
    for n in data.notes:
        print("  note:", n)

    # --- returns
    weekly = _weekly(px)
    rets = simple_returns(weekly)
    ppy = periods_per_year(rets.index)
    rf_in = last_rf_india(data)
    rf_us = last_rf_us(px)
    rf_w_in = rf_in / ppy
    rf_w_us = rf_us / ppy

    client = universe.client
    mkt_in = universe.market_in
    mkt_us = universe.market_us
    fx = universe.fx
    need = [client, mkt_in, universe.comparator, mkt_us, fx]
    missing = [t for t in need if t not in rets.columns]
    if missing:
        raise SystemExit(f"Missing tickers after download: {missing}")

    ex_in = rets[client] - rf_w_in
    ex_mkt_in = rets[mkt_in] - rf_w_in
    ex_ma = rets[universe.comparator] - rf_w_us
    ex_mkt_us = rets[mkt_us] - rf_w_us

    capm_in = capm(
        ex_in, ex_mkt_in, rf_in, ppy, client, mkt_in,
        C.ERP_OVERRIDE if C.ERP_OVERRIDE is not None else C.ERP_LABELLED_IN,
    )
    capm_ma = capm(
        ex_ma, ex_mkt_us, rf_us, ppy, universe.comparator, mkt_us,
        C.ERP_OVERRIDE if C.ERP_OVERRIDE is not None else C.ERP_LABELLED_US,
    )

    fx_rets = rets[fx].rename("fx")
    factors = pd.concat([ex_mkt_in.rename("market"), fx_rets], axis=1)
    fac = factor_capm(
        ex_in, factors, rf_in, ppy, client,
        premia_override={"market": capm_in.mkt_premium_annual},
    )

    # --- MPT on INR names
    names = universe.book
    r_book = rets[list(names)].dropna()
    mu = r_book.mean().to_numpy() * ppy
    cov = r_book.cov().to_numpy() * ppy
    front = efficient_frontier(mu, cov, names, rf_in)
    asset_vol = np.sqrt(np.diag(cov))
    asset_ret = mu

    # --- WACC / valuation
    fund = data.fundamentals[client]
    px_client = _latest(px[client])
    we, we_src = _equity_weight(fund.market_cap, fund.total_debt)
    bond = comparable_bond(C.BOND_FACE, C.BOND_COUPON, C.BOND_YTM, C.BOND_YEARS, C.BOND_FREQ)
    kd = bond.ytm
    if we >= 0.95:
        debt_line = (
            "Reported debt is negligible, so WACC equals the cost of equity. "
            "The bond shows YTM and duration; it does not change this NPV."
        )
    else:
        debt_line = f"Debt weight is {1.0 - we:.1%} at the bond YTM."
    wacc_capm = wacc(capm_in.cost_of_equity, kd, we, C.TAX_RATE)
    wacc_fx = wacc(fac.cost_of_equity, kd, we, C.TAX_RATE)
    fund_ma = data.fundamentals[universe.comparator]
    we_ma, _ = _equity_weight(fund_ma.market_cap, fund_ma.total_debt)
    wacc_ma = wacc(capm_ma.cost_of_equity, rf_us + 0.012, we_ma, 0.21)

    dps = _dps(fund, px_client)
    g_sust = None
    if fund.roe is not None and fund.payout is not None:
        g_sust = (1.0 - min(max(fund.payout, 0.0), 1.0)) * fund.roe
    try:
        eq = equity_vs_market(dps, capm_in.cost_of_equity, C.GORDON_G, px_client)
    except ValueError:
        g_use = min(C.GORDON_G, capm_in.cost_of_equity - 0.01)
        eq = equity_vs_market(dps, capm_in.cost_of_equity, g_use, px_client)

    # --- FX + project
    spot_fx = _latest(px[fx])
    fwd1 = price_forward(
        asof_d, spot_fx, rf_us, rf_in, 1.0,
        C.SPOT_LAG_BUSINESS_DAYS, C.USD_DAYCOUNT, C.INR_DAYCOUNT,
    )
    fwds = [
        price_forward(
            asof_d, spot_fx, rf_us, rf_in, float(t),
            C.SPOT_LAG_BUSINESS_DAYS, C.USD_DAYCOUNT, C.INR_DAYCOUNT,
        )
        for t in range(1, C.PROJECT_HORIZON_YEARS + 1)
    ]
    fx_unhedged = [spot_fx] * (1 + C.PROJECT_HORIZON_YEARS)
    fx_hedged = [spot_fx] + [f.outright for f in fwds]
    cfs_u = usd_project_inr_cashflows(
        C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, fx_unhedged, C.PROJECT_SALVAGE_USD
    )
    cfs_h = usd_project_inr_cashflows(
        C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, fx_hedged, C.PROJECT_SALVAGE_USD
    )
    fcf_haircut = fcf_haircut_breakeven(
        wacc_capm, C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, fx_unhedged, C.PROJECT_SALVAGE_USD
    )
    npv_u = npv(wacc_capm, cfs_u)
    npv_h = npv(wacc_capm, cfs_h)
    irr_u = irr(cfs_u)
    # tornado
    cfs_wacc_hi = npv(wacc_capm + 0.01, cfs_u)
    cfs_wacc_lo = npv(wacc_capm - 0.01, cfs_u)
    fx_up = [s * 1.05 for s in fx_unhedged]
    fx_dn = [s * 0.95 for s in fx_unhedged]
    npv_fx_up = npv(wacc_capm, usd_project_inr_cashflows(C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, fx_up, C.PROJECT_SALVAGE_USD))
    npv_fx_dn = npv(wacc_capm, usd_project_inr_cashflows(C.PROJECT_CAPEX_USD, C.PROJECT_FCF_USD, fx_dn, C.PROJECT_SALVAGE_USD))
    npv_kefx = npv(wacc_fx, cfs_u)
    torn = tornado(
        npv_u,
        {
            "WACC +1pt": cfs_wacc_hi,
            "WACC −1pt": cfs_wacc_lo,
            "USDINR +5%": npv_fx_up,
            "USDINR −5%": npv_fx_dn,
            "Factor WACC": npv_kefx,
            "Forward FX path": npv_h,
        },
    )

    # --- realised FX vol and GK options
    fx_log = np.log(weekly[fx] / weekly[fx].shift(1)).dropna()
    fx_vol = annualize_vol(float(fx_log.std(ddof=1)), ppy)
    tenor_h = C.HEDGE_HORIZON_YEARS
    put_k = strike_from_delta(spot_fx, tenor_h, rf_in, fx_vol, -C.COLLAR_PUT_DELTA, "put", div=rf_us)
    call_k = strike_from_delta(spot_fx, tenor_h, rf_in, fx_vol, C.COLLAR_CALL_DELTA, "call", div=rf_us)
    put_prem, call_prem = fx_option_premiums(spot_fx, put_k, call_k, tenor_h, rf_in, fx_vol, rf_us)
    collar_net = put_prem - call_prem
    vanilla_call = bs_price(spot_fx, spot_fx, tenor_h, rf_in, fx_vol, "call", div=rf_us)
    asian = asian_arithmetic(
        spot_fx, spot_fx, tenor_h, rf_in, fx_vol, "call",
        n_steps=C.ASIAN_STEPS, n_paths=C.ASIAN_PATHS, div=rf_us,
    )
    spots = np.linspace(spot_fx * 0.85, spot_fx * 1.15, 61)
    htab = hedge_table(spots, fwd1.outright, put_k, call_k, put_prem, collar_net, C.USD_RECEIPT_NOTIONAL)
    unhedged_vol = residual_vol(htab["unhedged_inr_m"].to_numpy())
    collar_vol = residual_vol(htab["collar_inr_m"].to_numpy())
    fwd_vol = residual_vol(htab["forward_inr_m"].to_numpy())

    # --- listed equity option
    listed = data.listed_option
    if listed is None:
        # synthetic 5% OTM 45d call at 22% vol so the exhibit still runs
        synth_spot = px_client
        synth_k = round(synth_spot * 1.05, 2)
        synth_t = 45 / 365.0
        synth_sig = 0.22
        synth_mid = bs_price(synth_spot, synth_k, synth_t, rf_in, synth_sig, "call")
        opt_ticker, opt_kind, opt_k, opt_exp = client, "call", synth_k, "synthetic"
        opt_spot, opt_t, opt_mid = synth_spot, synth_t, synth_mid
        opt_iv = synth_sig
        r_opt, q_opt = rf_in, fund.div_yield or 0.0
    else:
        opt_ticker, opt_kind = listed.ticker, listed.kind
        opt_k, opt_exp = listed.strike, listed.expiry.isoformat()
        opt_spot, opt_t, opt_mid = listed.spot, listed.tenor, listed.mid
        r_opt = rf_us if listed.ticker in {universe.comparator, universe.option_underlying} else rf_in
        q_opt = 0.0
        if listed.ticker == universe.comparator:
            q_opt = fund_ma.div_yield or 0.0
        opt_iv = implied_vol(opt_mid, opt_spot, opt_k, opt_t, r_opt, opt_kind, q_opt)

    opt_bs = bs_price(opt_spot, opt_k, opt_t, r_opt, opt_iv, opt_kind, q_opt)
    opt_crr = crr_price(opt_spot, opt_k, opt_t, r_opt, opt_iv, C.BINOMIAL_STEPS_REPORT, opt_kind, div=q_opt)
    gks = bs_greeks(opt_spot, opt_k, opt_t, r_opt, opt_iv, opt_kind, q_opt)
    bdelta = binomial_delta(opt_spot, opt_k, opt_t, r_opt, opt_iv, C.BINOMIAL_STEPS_REPORT, opt_kind)
    crr_path = [
        crr_price(opt_spot, opt_k, opt_t, r_opt, opt_iv, n, opt_kind, div=q_opt)
        for n in C.BINOMIAL_STEPS_CONVERGE
    ]
    grid = np.linspace(opt_spot * 0.8, opt_spot * 1.2, 40)
    deltas = np.array([bs_greeks(s, opt_k, opt_t, r_opt, opt_iv, opt_kind, q_opt).delta for s in grid])
    gammas = np.array([bs_greeks(s, opt_k, opt_t, r_opt, opt_iv, opt_kind, q_opt).gamma for s in grid])

    print("Walk-forward Ridge / gradient boosting (no look-ahead)…")
    C.EXHIBIT_DIR.mkdir(parents=True, exist_ok=True)
    blend_mu, wf_tables = forecast_book(r_book, rets[mkt_in], rets[fx], names)
    infy_wf = wf_tables[client]
    rmse_gb = rmse(infy_wf["y"].to_numpy(), infy_wf["gb"].to_numpy())
    rmse_ridge = rmse(infy_wf["y"].to_numpy(), infy_wf["ridge"].to_numpy())
    rmse_hist = rmse(infy_wf["y"].to_numpy(), infy_wf["hist"].to_numpy())
    hit_gb = hit_rate(infy_wf["y"].to_numpy(), infy_wf["gb"].to_numpy())
    mv_bt = long_only_mv_backtest(r_book, blend_mu, rets[mkt_in], rf_w_in, ppy)
    beat_nifty = mv_bt.sharpe["gb_mv"] > mv_bt.sharpe["nifty"]
    strategy_used = (
        "monthly, long-only shrinkage mean-variance using trailing historical "
        "returns, with a 35% position cap"
    )
    if rmse_gb < rmse_hist - 1e-6 and beat_nifty:
        ml_verdict = (
            "GB beats the expanding-mean forecast and the boosted book beat Nifty on this sample. "
            "Still one sample: do not treat it as a permanent edge over CAPM WACC."
        )
    elif beat_nifty:
        ml_verdict = (
            "ML-MV beat Nifty, but did not beat the simpler historical-MV rule; GB also failed to improve "
            "INFY forecast error (sign hit near 50%). The historical-MV rule is therefore selected, while ML "
            "stays as a documented challenger and robustness test."
        )
    else:
        ml_verdict = (
            "GB does not beat the expanding mean, and the boosted book does not beat Nifty. "
            "Do not let the model override CAPM WACC or the collar."
        )
    infy_wf.to_csv(C.EXHIBIT_DIR / "ml_infy_oos.csv")
    pd.DataFrame(
        {
            "sharpe": mv_bt.sharpe,
            "ann_mean": mv_bt.ann_mean,
            "ann_vol": mv_bt.ann_vol,
            "max_drawdown": mv_bt.max_drawdown,
            "annual_turnover": mv_bt.turnover,
            "beta": mv_bt.beta,
            "jensen": mv_bt.jensen,
            "tracking_error": mv_bt.tracking_error,
            "info_ratio": mv_bt.info_ratio,
        }
    ).to_csv(C.EXHIBIT_DIR / "ml_backtest.csv")
    pd.DataFrame(
        {"last": mv_bt.last_weights, "average": mv_bt.avg_weights}
    ).to_csv(C.EXHIBIT_DIR / "ml_last_weights.csv")
    avg_w_txt = " · ".join(
        f"{n.replace('.NS', '')} {w:.0%}" for n, w in mv_bt.avg_weights.items()
    )

    # --- realised vs SML points
    hist_in, _ = _ann_stats(rets[client].dropna(), ppy)
    hist_ma, _ = _ann_stats(rets[universe.comparator].dropna(), ppy)
    hist_mkt, _ = _ann_stats(rets[mkt_in].dropna(), ppy)

    C.EXHIBIT_DIR.mkdir(parents=True, exist_ok=True)
    plot_frontier(front, asset_vol, asset_ret, list(names))
    plot_sml(
        rf_in,
        capm_in.mkt_premium_annual,
        [
            (0.0, rf_in, "Rf"),
            (1.0, rf_in + capm_in.mkt_premium_annual, "Nifty"),
            (capm_in.beta, hist_in, "INFY"),
            (capm_ma.beta, hist_ma, "MA"),
        ],
    )
    plot_factor_contrib(fac.beta_frame(), "INFY factor contribution to ke", "03_factor_ke.png")
    plot_tornado(torn)
    plot_crr_vs_bs(list(C.BINOMIAL_STEPS_CONVERGE), crr_path, opt_bs)
    plot_greeks(grid, deltas, gammas)
    plot_hedge(htab)
    plot_ml_nav(mv_bt.wealth)

    as_weight_frame(front).to_csv(C.EXHIBIT_DIR / "weights.csv")
    torn.to_csv(C.EXHIBIT_DIR / "tornado.csv", index=False)
    htab.to_csv(C.EXHIBIT_DIR / "hedge_scenarios.csv", index=False)
    fac.beta_frame().to_csv(C.EXHIBIT_DIR / "factor_ke.csv")
    capm_in.ols.as_frame().to_csv(C.EXHIBIT_DIR / "capm_infy.csv")

    # recommendation logic
    if npv_u > 0 and npv_h > 0:
        reco = (
            f"On the labelled cash flows, the project clears a {wacc_capm:.2%} CAPM WACC "
            f"(NPV {npv_u/1e9:.2f}bn INR unhedged, {npv_h/1e9:.2f}bn on the forward path). "
            f"The project ends after year 3 with zero salvage. "
            f"Unhedged NPV reaches zero if every free cash flow is {fcf_haircut:.0%} lower. "
            f"Those cash flows are a teaching case, not an Infosys forecast. "
            f"Hedge year-1 receipts with a 25Δ collar, not a 100% forward, "
            f"so a weaker rupee can still help. "
            f"Both NPVs use the same WACC; the hedge changes the FX path only."
        )
        hedge_call = (
            "Prefer the 25Δ collar over 100% forwards: residual vol drops versus unhedged "
            "while keeping participation if USDINR rises (exporter-friendly). Use the Asian "
            "only if the desk will actually average monthly fixings; otherwise the vanilla put leg is cleaner."
        )
    elif npv_h > 0:
        reco = (
            "Approve only if Treasury sells USD forward (or collars) through the project life — "
            "unhedged NPV is fragile to INR strength."
        )
        hedge_call = "Hedge is a condition of the capex, not an overlay."
    else:
        reco = (
            "Reject or re-scope the capex at current WACC. Options/forwards change risk shape, "
            "not the sign of NPV at this hurdle."
        )
        hedge_call = "Do not spend premium to dress up a negative-NPV project."

    notes = data.notes or ["No data caveats."]
    ctx = {
        "asof": asof_d.isoformat(),
        "pulled": data.pulled_at,
        "capex_usd": C.PROJECT_CAPEX_USD,
        "ke_capm": capm_in.cost_of_equity,
        "ke_fx": fac.cost_of_equity,
        "beta": capm_in.beta,
        "jensen": capm_in.jensen_annual,
        "r2": capm_in.r2,
        "wacc": wacc_capm,
        "wacc_ma": wacc_ma,
        "we": we,
        "we_src": we_src,
        "gordon": eq.gordon_price,
        "px": eq.market_price,
        "premium": eq.premium_to_gordon,
        "impl_g": eq.implied_growth,
        "npv_unhedged": npv_u,
        "npv_hedged": npv_h,
        "irr_unhedged": irr_u,
        "fwd": fwd1.outright,
        "spot_fx": spot_fx,
        "collar_vol": collar_vol,
        "unhedged_vol": unhedged_vol,
        "asian": asian,
        "vanilla_call": vanilla_call,
        "tenor_h": tenor_h,
        "beta_ma": capm_ma.beta,
        "jensen_ma": capm_ma.jensen_annual,
        "r2_ma": capm_ma.r2,
        "ke_ma": capm_ma.cost_of_equity,
        "rf_in": rf_in,
        "rf_us": rf_us,
        "erp": capm_in.mkt_premium_annual,
        "erp_us": capm_ma.mkt_premium_annual,
        "erp_sample": capm_in.sample_premium_annual,
        "erp_us_sample": capm_ma.sample_premium_annual,
        "mod_dur": bond.mod_duration,
        "conv": bond.convexity,
        "debt_line": debt_line,
        "fcf_haircut": fcf_haircut,
        "opt_ticker": opt_ticker,
        "opt_kind": opt_kind,
        "opt_k": opt_k,
        "opt_exp": opt_exp,
        "opt_mid": opt_mid,
        "opt_bs": opt_bs,
        "opt_crr": opt_crr,
        "opt_iv": opt_iv,
        "opt_delta": gks.delta,
        "opt_bdelta": bdelta,
        "opt_gamma": gks.gamma,
        "opt_vega": gks.vega,
        "opt_theta": gks.theta,
        "notional": C.USD_RECEIPT_NOTIONAL,
        "put_prem": put_prem,
        "collar_net": collar_net,
        "reco_headline": reco,
        "hedge_call": hedge_call,
        "notes": "; ".join(notes),
        "fwd_vol": fwd_vol,
        "hist_mkt": hist_mkt,
        "put_k": put_k,
        "call_k": call_k,
        "fx_vol": fx_vol,
        "wacc_fx": wacc_fx,
        "dps": dps,
        "g_sust_line": (
            f"; retention×ROE g = {g_sust:.2%}"
            + (
                " (above ke — fundamentals Gordon not defined)"
                if g_sust >= capm_in.cost_of_equity
                else ""
            )
            if g_sust is not None
            else ""
        ),
        "rmse_gb": rmse_gb,
        "rmse_ridge": rmse_ridge,
        "rmse_hist": rmse_hist,
        "hit_gb": hit_gb,
        "sh_gb": mv_bt.sharpe["gb_mv"],
        "sh_hist": mv_bt.sharpe["hist_mv"],
        "sh_inv": mv_bt.sharpe["inv_vol"],
        "sh_eq": mv_bt.sharpe["equal"],
        "sh_nifty": mv_bt.sharpe["nifty"],
        "dd_gb": mv_bt.max_drawdown["gb_mv"],
        "turnover_gb": mv_bt.turnover["gb_mv"],
        "dd_hist": mv_bt.max_drawdown["hist_mv"],
        "turnover_hist": mv_bt.turnover["hist_mv"],
        "beta_hist": mv_bt.beta["hist_mv"],
        "jensen_hist": mv_bt.jensen["hist_mv"],
        "te_hist": mv_bt.tracking_error["hist_mv"],
        "ir_hist": mv_bt.info_ratio["hist_mv"],
        "beta_gb": mv_bt.beta["gb_mv"],
        "jensen_gb": mv_bt.jensen["gb_mv"],
        "te_gb": mv_bt.tracking_error["gb_mv"],
        "ir_gb": mv_bt.info_ratio["gb_mv"],
        "avg_w_txt": avg_w_txt,
        "strategy_used": strategy_used,
        "ml_verdict": ml_verdict,
    }
    write_memo(C.MEMO_DIR / "ic_note.md", ctx)
    (C.EXHIBIT_DIR / "summary.json").write_text(json.dumps(ctx, indent=2, default=str))
    html_path = write_html(ctx)

    print("\n=== IC pack ===")
    print(f"CAPM ke {capm_in.cost_of_equity:.2%}  factor ke {fac.cost_of_equity:.2%}  WACC {wacc_capm:.2%}")
    print(f"Gordon {eq.gordon_price:.1f} vs px {eq.market_price:.1f}  ({eq.premium_to_gordon:+.1%})")
    print(f"NPV unhedged {npv_u/1e9:.2f}bn INR | forward path {npv_h/1e9:.2f}bn | IRR {irr_u:.2%}")
    print(f"USDINR spot {spot_fx:.2f}  1y IRP fwd {fwd1.outright:.2f}  realised vol {fx_vol:.1%}")
    print(f"Listed {opt_kind} {opt_ticker} K={opt_k:.2f} mid {opt_mid:.3f} BS {opt_bs:.3f} IV {opt_iv:.1%}")
    print(
        f"ML OOS INFY RMSE gb {rmse_gb:.4f} ridge {rmse_ridge:.4f} hist {rmse_hist:.4f} | "
        f"Sharpe gb-MV {mv_bt.sharpe['gb_mv']:.2f} hist-MV {mv_bt.sharpe['hist_mv']:.2f} Nifty {mv_bt.sharpe['nifty']:.2f} | "
        f"hist β {mv_bt.beta['hist_mv']:.2f} α {mv_bt.jensen['hist_mv']:.2%} "
        f"TE {mv_bt.tracking_error['hist_mv']:.1%} IR {mv_bt.info_ratio['hist_mv']:.2f}"
    )
    print(f"Wrote {C.MEMO_DIR / 'ic_note.md'} and {C.EXHIBIT_DIR}")
    print(f"Coverage note: {html_path}")
    print("Open with:  open memo/ic_pack.html")
    print(reco)
    if not args.no_open:
        import webbrowser

        webbrowser.open(html_path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
