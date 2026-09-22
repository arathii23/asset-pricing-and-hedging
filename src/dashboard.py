"""Interactive analyst dashboard built on the saved IC base case."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from . import config as C
from .fx_forward import price_forward
from .greeks import bs_greeks
from .options import asian_arithmetic, bs_price, crr_price
from .wacc import irr, npv, usd_project_inr_cashflows

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = C.EXHIBIT_DIR / "summary.json"


def pct(x: float, digits: int = 2) -> str:
    return f"{100.0 * float(x):.{digits}f}%"


def bn(x: float) -> str:
    return f"{float(x) / 1e9:+.2f} bn INR"


@st.cache_data
def load_summary() -> dict:
    return json.loads(SUMMARY.read_text()) if SUMMARY.exists() else {}


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = C.EXHIBIT_DIR / name
    return pd.read_csv(path, index_col=0) if path.exists() else pd.DataFrame()


def forward_path(m: dict, spot: float) -> list[float]:
    asof = date.fromisoformat(str(m["asof"]))
    return [spot] + [
        price_forward(
            asof,
            spot,
            float(m["rf_us"]),
            float(m["rf_in"]),
            float(year),
            C.SPOT_LAG_BUSINESS_DAYS,
            C.USD_DAYCOUNT,
            C.INR_DAYCOUNT,
        ).outright
        for year in range(1, C.PROJECT_HORIZON_YEARS + 1)
    ]


def project_scenario(
    m: dict,
    capex_usd: float,
    fcf_change: float,
    wacc: float,
    fx_change: float,
    use_forwards: bool,
) -> tuple[list[float], list[float], tuple[float, ...], float, float]:
    spot = float(m["spot_fx"]) * (1.0 + fx_change)
    fx_path = (
        forward_path(m, spot)
        if use_forwards
        else [spot] * (1 + C.PROJECT_HORIZON_YEARS)
    )
    fcf = tuple(value * (1.0 + fcf_change) for value in C.PROJECT_FCF_USD)
    cashflows = usd_project_inr_cashflows(
        capex_usd, fcf, fx_path, C.PROJECT_SALVAGE_USD
    )
    return cashflows, fx_path, fcf, npv(wacc, cashflows), irr(cashflows)


def render_sidebar(m: dict) -> None:
    with st.sidebar:
        st.markdown("### Base case")
        st.success("Locked published result")
        st.metric("As of", str(m.get("asof", "—")))
        st.metric("CAPM WACC", pct(m["wacc"]))
        st.metric("Unhedged NPV", bn(m["npv_unhedged"]))
        st.caption(
            "Scenario controls never overwrite the saved recommendation or resume metrics."
        )
        st.divider()
        st.markdown("**Data**")
        st.caption(f"Public market data · pulled {m.get('pulled', '—')}")
        if m.get("notes"):
            st.warning(str(m["notes"]))


def render_overview(m: dict) -> None:
    st.subheader("Investment committee decision")
    st.success(m.get("reco_headline", ""))
    st.info(m.get("hedge_call", ""))

    cols = st.columns(5)
    cols[0].metric("CAPM WACC", pct(m["wacc"]))
    cols[1].metric("Project IRR", pct(m["irr_unhedged"]))
    cols[2].metric("Unhedged NPV", bn(m["npv_unhedged"]))
    cols[3].metric("Forward-path NPV", bn(m["npv_hedged"]))
    cols[4].metric("FCF downside to NPV = 0", pct(m["fcf_haircut"], 0))

    capital, hedge, portfolio = st.columns(3)
    with capital:
        st.markdown("#### Capital budget")
        st.write(f"Cost of equity: **{pct(m['ke_capm'])}**")
        st.write(f"Equity weight: **{pct(m['we'], 1)}**")
        st.write(f"Gordon value / market: **{m['gordon']:.1f} / {m['px']:.1f}**")
        st.caption(m.get("debt_line", ""))
    with hedge:
        reduction = 1.0 - float(m["collar_vol"]) / float(m["unhedged_vol"])
        st.markdown("#### Treasury hedge")
        st.write(f"USDINR spot / forward: **{m['spot_fx']:.2f} / {m['fwd']:.2f}**")
        st.write(f"Collar dispersion reduction: **{pct(reduction, 0)}**")
        st.write(f"Collar net premium: **{m['collar_net']:.3f} INR/USD**")
        st.caption("The collar is selected; the ML model does not set hedge policy.")
    with portfolio:
        st.markdown("#### Portfolio rule")
        st.write(f"Selected Sharpe / Nifty: **{m['sh_hist']:.2f} / {m['sh_nifty']:.2f}**")
        st.write(f"Beta / Jensen alpha: **{m['beta_hist']:.2f} / {pct(m['jensen_hist'])}**")
        st.write(f"Maximum drawdown: **{pct(m['dd_hist'], 1)}**")
        st.caption("Historical mean-variance beat the ML challenger out of sample.")

    chart_map = {
        "Capital allocation — NPV sensitivity": "04_npv_tornado.png",
        "Treasury — hedge outcomes": "07_hedge_pnl.png",
        "Portfolio — walk-forward NAV": "08_ml_nav.png",
        "Asset pricing — security market line": "02_sml.png",
        "Portfolio theory — frontier and CML": "01_frontier_cml.png",
        "Options — binomial convergence": "05_crr_vs_bs.png",
        "Options — Greeks": "06_greeks.png",
        "Factor model — cost of equity": "03_factor_ke.png",
    }
    st.subheader("Decision exhibits")
    chosen = st.selectbox("Select exhibit", list(chart_map))
    chart = C.EXHIBIT_DIR / chart_map[chosen]
    if chart.exists():
        st.image(str(chart), caption=chosen, width="stretch")

    with st.expander("Key limitations"):
        st.markdown(
            f"""
- Cash flows are a labelled teaching case, not an Infosys forecast.
- The project ends after year {C.PROJECT_HORIZON_YEARS} with zero salvage value.
- Hedged and unhedged cases use the same INR WACC; the FX path changes.
- Equity option IV is one market snapshot; USDINR volatility is realised.
- The portfolio result is one historical sample, not a guaranteed edge.
"""
        )


def render_scenario_lab(m: dict) -> None:
    st.subheader("Capital-budgeting scenario lab")
    st.caption(
        "Change operating and market assumptions. The published base case remains locked."
    )

    base_capex_m = C.PROJECT_CAPEX_USD / 1e6
    a, b, c, d = st.columns(4)
    with a:
        capex_m = st.number_input(
            "Initial capex (USD m)",
            min_value=float(base_capex_m * 0.5),
            max_value=float(base_capex_m * 2.0),
            value=float(base_capex_m),
            step=5.0,
        )
    with b:
        fcf_change_pct = st.slider("Annual FCF change", -50, 50, 0, 5)
    with c:
        wacc_pct = st.number_input(
            "Discount rate",
            min_value=1.0,
            max_value=40.0,
            value=float(100.0 * m["wacc"]),
            step=0.25,
            format="%.2f",
        )
    with d:
        fx_change_pct = st.slider("USDINR path shock", -15, 15, 0, 1)

    path_name = st.radio(
        "FX conversion path",
        ["Unhedged constant FX", "IRP forward hedge"],
        horizontal=True,
    )
    use_forwards = path_name == "IRP forward hedge"
    cashflows, fx_path, fcf, scenario_npv, scenario_irr = project_scenario(
        m,
        capex_m * 1e6,
        fcf_change_pct / 100.0,
        wacc_pct / 100.0,
        fx_change_pct / 100.0,
        use_forwards,
    )
    base_npv = float(m["npv_hedged"] if use_forwards else m["npv_unhedged"])

    kpis = st.columns(4)
    kpis[0].metric("Scenario NPV", bn(scenario_npv), bn(scenario_npv - base_npv))
    kpis[1].metric("Scenario IRR", pct(scenario_irr), f"{100 * (scenario_irr - m['irr_unhedged']):+.1f} pp")
    kpis[2].metric("Discount rate", pct(wacc_pct / 100.0))
    kpis[3].metric("Decision", "PASS" if scenario_npv > 0 else "REVIEW")

    if scenario_npv > 0:
        st.success("Scenario clears the hurdle: NPV remains positive.")
    else:
        st.error("Scenario fails the hurdle: NPV is negative.")

    periods = list(range(1 + C.PROJECT_HORIZON_YEARS))
    usd_flows = [-capex_m * 1e6, *fcf]
    cashflow_table = pd.DataFrame(
        {
            "Period": periods,
            "USD cash flow (m)": np.array(usd_flows) / 1e6,
            "USDINR conversion": fx_path,
            "INR cash flow (bn)": np.array(cashflows) / 1e9,
        }
    ).set_index("Period")
    st.dataframe(
        cashflow_table.style.format(
            {
                "USD cash flow (m)": "{:,.1f}",
                "USDINR conversion": "{:,.2f}",
                "INR cash flow (bn)": "{:+,.2f}",
            }
        ),
        width="stretch",
    )

    st.markdown("#### Two-way NPV sensitivity (INR bn)")
    wacc_grid = np.linspace(max(0.01, wacc_pct / 100.0 - 0.02), wacc_pct / 100.0 + 0.02, 5)
    fcf_grid = np.linspace(fcf_change_pct / 100.0 - 0.20, fcf_change_pct / 100.0 + 0.20, 5)
    matrix = []
    for wacc_value in wacc_grid:
        row = []
        for fcf_change in fcf_grid:
            scenario = project_scenario(
                m,
                capex_m * 1e6,
                fcf_change,
                float(wacc_value),
                fx_change_pct / 100.0,
                use_forwards,
            )
            row.append(scenario[3] / 1e9)
        matrix.append(row)
    sensitivity = pd.DataFrame(
        matrix,
        index=[f"WACC {value:.1%}" for value in wacc_grid],
        columns=[f"FCF {value:+.0%}" for value in fcf_grid],
    )
    st.dataframe(
        sensitivity.style.format("{:+.2f}").background_gradient(
            cmap="RdYlGn", axis=None
        ),
        width="stretch",
    )


def render_portfolio(m: dict) -> None:
    st.subheader("Portfolio construction and model challenge")
    st.caption(
        "The selected rule is historical mean-variance. Ridge and gradient boosting are challengers."
    )
    metrics = load_csv("ml_backtest.csv")
    weights = load_csv("ml_last_weights.csv")

    if not metrics.empty:
        order = ["hist_mv", "gb_mv", "inv_vol", "equal", "nifty"]
        available = [name for name in order if name in metrics.index]
        view = metrics.loc[
            available,
            [
                "sharpe",
                "ann_mean",
                "ann_vol",
                "max_drawdown",
                "annual_turnover",
                "beta",
                "jensen",
                "tracking_error",
                "info_ratio",
            ],
        ].copy()
        view.index = [
            {
                "hist_mv": "Selected historical MV",
                "gb_mv": "ML-MV challenger",
                "inv_vol": "Inverse volatility",
                "equal": "Equal weight",
                "nifty": "Nifty",
            }[name]
            for name in available
        ]
        st.dataframe(
            view.style.format(
                {
                    "sharpe": "{:.2f}",
                    "ann_mean": "{:.1%}",
                    "ann_vol": "{:.1%}",
                    "max_drawdown": "{:.1%}",
                    "annual_turnover": "{:.2f}x",
                    "beta": "{:.2f}",
                    "jensen": "{:.1%}",
                    "tracking_error": "{:.1%}",
                    "info_ratio": "{:.2f}",
                }
            ),
            width="stretch",
        )

    left, right = st.columns([1, 1.5])
    with left:
        st.markdown("#### Selected-rule weights")
        if not weights.empty:
            display_weights = weights.rename(
                columns={"last": "Latest", "average": "OOS average"}
            )
            st.dataframe(
                display_weights.style.format("{:.1%}"), width="stretch"
            )
            if "average" in weights:
                st.bar_chart(weights[["average"]], horizontal=True)
    with right:
        nav = C.EXHIBIT_DIR / "08_ml_nav.png"
        if nav.exists():
            st.image(str(nav), caption="Walk-forward wealth paths", width="stretch")

    st.info(m.get("ml_verdict", ""))
    st.caption(
        f"Selected rule: {m.get('strategy_used', 'historical mean-variance')}. "
        f"Average weights: {m.get('avg_w_txt', '—')}."
    )


def render_pricing_lab(m: dict) -> None:
    st.subheader("Options pricing lab")
    st.caption("Inputs update Black–Scholes, CRR, Asian Monte Carlo, and Greeks.")

    a, b, c = st.columns(3)
    with a:
        spot = st.number_input(
            "Spot", min_value=0.01, value=float(m["spot_fx"]), step=0.10
        )
        strike = st.number_input(
            "Strike", min_value=0.01, value=float(m["put_k"]), step=0.10
        )
        tenor = st.slider(
            "Tenor (years)", 0.05, 2.0, float(m["tenor_h"]), 0.05
        )
    with b:
        domestic = st.number_input(
            "Domestic rate",
            0.0,
            0.30,
            float(m["rf_in"]),
            format="%.4f",
        )
        foreign = st.number_input(
            "Foreign rate / dividend yield",
            0.0,
            0.30,
            float(m["rf_us"]),
            format="%.4f",
        )
        volatility = st.slider(
            "Volatility", 0.01, 0.60, float(max(m["fx_vol"], 0.05)), 0.01
        )
    with c:
        kind = st.selectbox("Option type", ["put", "call"])
        steps = st.select_slider(
            "Binomial steps", options=[10, 20, 50, 100, 200], value=50
        )
        paths = st.select_slider(
            "Asian Monte Carlo paths",
            options=[2_000, 5_000, 10_000, 20_000],
            value=10_000,
        )

    try:
        bs = bs_price(spot, strike, tenor, domestic, volatility, kind, foreign)
        crr = crr_price(
            spot, strike, tenor, domestic, volatility, steps, kind, div=foreign
        )
        asian = asian_arithmetic(
            spot,
            strike,
            tenor,
            domestic,
            volatility,
            kind,
            n_steps=C.ASIAN_STEPS,
            n_paths=paths,
            seed=7,
            div=foreign,
        )
        greeks = bs_greeks(
            spot, strike, tenor, domestic, volatility, kind, foreign
        )
    except Exception as exc:
        st.error(f"Pricing failed: {exc}")
        return

    kpis = st.columns(5)
    kpis[0].metric("Black–Scholes", f"{bs:.4f}")
    kpis[1].metric(f"CRR ({steps})", f"{crr:.4f}", f"{crr - bs:+.4f}")
    kpis[2].metric("Asian MC", f"{asian:.4f}")
    kpis[3].metric("Delta", f"{greeks.delta:.3f}")
    kpis[4].metric("Gamma", f"{greeks.gamma:.4f}")

    spots = np.linspace(spot * 0.75, spot * 1.25, 60)
    prices = [
        bs_price(value, strike, tenor, domestic, volatility, kind, foreign)
        for value in spots
    ]
    st.line_chart(
        pd.DataFrame({"Spot": spots, "Option value": prices}).set_index("Spot")
    )
    st.caption(
        f"Vega {greeks.vega:.3f} · Theta {greeks.theta:.3f}. "
        "The Asian value is lower when averaging dampens volatility."
    )


def render_methodology(m: dict) -> None:
    st.subheader("Methodology and audit trail")
    st.markdown(
        """
1. Estimate required return with CAPM and a market-plus-FX factor model.
2. Use the cost of equity and bond yield in WACC; evaluate Gordon value and project NPV/IRR.
3. Price forwards, CRR/Black–Scholes options, Greeks, collars, and an Asian option.
4. Compare historical mean-variance with walk-forward Ridge and gradient boosting.
5. Select the simpler historical rule because ML does not improve the out-of-sample result.
"""
    )

    st.markdown("#### Base-case assumptions")
    assumptions = pd.DataFrame(
        {
            "Assumption": [
                "India ERP",
                "US ERP",
                "Tax rate",
                "Perpetual growth",
                "Position cap",
                "Rebalance frequency",
                "Transaction cost",
                "Project salvage",
            ],
            "Value": [
                pct(m["erp"]),
                pct(m["erp_us"]),
                pct(C.TAX_RATE),
                pct(C.GORDON_G),
                pct(C.MAX_WEIGHT, 0),
                f"{C.REBALANCE_WEEKS} weeks",
                f"{C.TRANSACTION_COST_BPS} bps",
                "Zero",
            ],
        }
    )
    st.dataframe(assumptions, hide_index=True, width="stretch")

    st.markdown("#### Download outputs")
    downloads = [
        ("IC note (Markdown)", C.MEMO_DIR / "ic_note.md", "text/markdown"),
        ("Base-case summary (JSON)", SUMMARY, "application/json"),
        ("Portfolio metrics (CSV)", C.EXHIBIT_DIR / "ml_backtest.csv", "text/csv"),
        ("Portfolio weights (CSV)", C.EXHIBIT_DIR / "ml_last_weights.csv", "text/csv"),
    ]
    columns = st.columns(2)
    for i, (label, path, mime) in enumerate(downloads):
        if path.exists():
            columns[i % 2].download_button(
                label,
                data=path.read_bytes(),
                file_name=path.name,
                mime=mime,
                width="stretch",
            )

    st.markdown("#### Scope")
    st.write(
        "Illustrative capital-budgeting case using public data. "
        "The cash flows are labelled assumptions, not company guidance or investment advice."
    )
    st.caption(m.get("notes", ""))


def main() -> None:
    st.set_page_config(
        page_title="Asset Pricing & Hedging · IC Desk",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    m = load_summary()
    if not m:
        st.error("No base-case summary found. Run `python run_ic_pack.py` first.")
        st.stop()

    render_sidebar(m)
    st.title("Asset Pricing & Hedging")
    st.caption(
        f"Investment committee dashboard · {C.CLIENT_NAME} ({C.CLIENT}) · "
        f"{C.COMPARATOR_NAME} comparator · market data as of {m.get('asof', '—')}"
    )
    tabs = st.tabs(
        [
            "IC overview",
            "Scenario analysis",
            "Portfolio",
            "Options lab",
            "Methodology",
        ]
    )
    with tabs[0]:
        render_overview(m)
    with tabs[1]:
        render_scenario_lab(m)
    with tabs[2]:
        render_portfolio(m)
    with tabs[3]:
        render_pricing_lab(m)
    with tabs[4]:
        render_methodology(m)
