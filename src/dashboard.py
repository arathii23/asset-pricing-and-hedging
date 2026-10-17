"""A guided walkthrough of the saved case and interactive finance calculations."""

from __future__ import annotations

import json
from datetime import date
from html import escape

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from . import config as C
from .dashboard_content import ASSET_NAMES, GLOSSARY, PAGE_FILES, PAGE_SLUGS, PAGES, STRATEGY_NAMES, STYLES, section_styles
from .fx_forward import price_forward
from .greeks import bs_greeks
from .hedge import hedge_table
from .options import asian_arithmetic, bs_price, crr_price
from .wacc import irr, npv, usd_project_inr_cashflows

SUMMARY = C.EXHIBIT_DIR / "summary.json"
CRORE = 10_000_000.0
COLORS = ["#245ca6", "#14786e", "#a06419", "#7050a0", "#b35252"]


def pct(value: float, digits: int = 2) -> str:
    return f"{float(value):.{digits}%}"


def rupees(value: float, signed: bool = False, digits: int = 1) -> str:
    sign = "−" if value < 0 else "+" if signed and value > 0 else ""
    return f"{sign}₹{abs(float(value)) / CRORE:,.{digits}f} crore"


def date_label(value: str) -> str:
    return date.fromisoformat(value).strftime("%d %b %Y")


@st.cache_data
def load_summary() -> dict:
    return json.loads(SUMMARY.read_text()) if SUMMARY.exists() else {}


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = C.EXHIBIT_DIR / name
    return pd.read_csv(path, index_col=0) if path.exists() else pd.DataFrame()


def navigate(page: str) -> None:
    st.session_state["pending_section"] = page


def eyebrow(text: str) -> None:
    st.markdown(f'<div class="eyebrow">{escape(text)}</div>', unsafe_allow_html=True)


def intro(title: str, description: str, step: str) -> None:
    with st.container(key="page_intro"):
        eyebrow(step)
        st.title(title)
        st.markdown(f'<p class="intro">{escape(description)}</p>', unsafe_allow_html=True)


def chart_image(filename: str, caption: str) -> None:
    path = C.EXHIBIT_DIR / filename
    if path.exists():
        st.image(str(path), caption=caption, width="stretch")
    else:
        st.info("This saved chart is unavailable. The calculations and tables are shown above.")


def next_section(page: str, label: str) -> None:
    st.divider()
    st.button(label, on_click=navigate, args=(page,), key=f"next_{page}")


def forward_path(m: dict, spot: float) -> list[float]:
    asof = date.fromisoformat(m["asof"])
    return [spot] + [
        price_forward(
            asof, spot, float(m["rf_us"]), float(m["rf_in"]), float(year),
            C.SPOT_LAG_BUSINESS_DAYS, C.USD_DAYCOUNT, C.INR_DAYCOUNT,
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
    """Change future conversion rates, keeping today's spending at saved spot."""
    spot = float(m["spot_fx"])
    original = forward_path(m, spot) if use_forwards else [spot] * (1 + C.PROJECT_HORIZON_YEARS)
    fx_path = [spot] + [rate * (1 + fx_change) for rate in original[1:]]
    fcf = tuple(value * (1 + fcf_change) for value in C.PROJECT_FCF_USD)
    flows = usd_project_inr_cashflows(capex_usd, fcf, fx_path, C.PROJECT_SALVAGE_USD)
    return flows, fx_path, fcf, npv(wacc, flows), irr(flows)


def render_sidebar(m: dict, pages: dict) -> None:
    with st.sidebar:
        eyebrow("ECO423 · IIT Kanpur")
        st.markdown("### Asset Pricing and Hedging")
        st.caption("Investment analysis and risk management")
        st.divider()
        for title, page in pages.items():
            st.page_link(page, label=title, width="stretch")
        st.divider()
        st.caption(f"Market data: {date_label(m['asof'])}")
        st.caption("Saved historical snapshot. Scenario inputs are hypothetical.")
        st.caption("Rupee totals: ₹ crore\n\nDollar totals: USD million\n\n₹1 crore = ₹10 million")


def render_home(m: dict) -> None:
    intro(
        "Asset Pricing and Hedging",
        "An investment analysis of a three-year USD expansion, currency protection for dollar receipts, and a separate comparison of portfolio allocation methods.",
        "Research overview",
    )
    st.caption(
        f"Reference company: Infosys  ·  Market snapshot: {date_label(m['asof'])}  ·  Base currency: INR"
    )
    st.button("Ask a question about this project", on_click=navigate, args=(PAGES[6],), key="open_assistant")
    st.markdown(
        '<div class="case-note"><strong>Scope.</strong> The expansion and its cash flows '
        'are illustrative assumptions. Public Infosys data provides a reference for risk '
        'and valuation; the case is not a company forecast or an announced investment.</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Investment case")
    st.write(
        "The company spends USD 80 million today. The expanded business is assumed to "
        "generate USD 32m, 36m and 40m of annual free cash flow after costs. "
        "The analysis converts those payments into rupees and values them today "
        "to assess whether the investment is worthwhile."
    )
    case = pd.DataFrame({
        "Period": ["Today", "Year 1", "Year 2", "Year 3"],
        "Cash flow (USD million)": [-C.PROJECT_CAPEX_USD / 1e6, *[v / 1e6 for v in C.PROJECT_FCF_USD]],
        "Purpose": ["Initial investment", "Cash after costs", "Cash after costs", "Cash after costs; zero salvage"],
    })
    st.dataframe(
        case.style.format({"Cash flow (USD million)": "{:+.0f}"}),
        hide_index=True,
        width="stretch",
    )
    st.button("Open expansion analysis", type="primary", on_click=navigate, args=(PAGES[1],))

    st.divider()
    st.subheader("Findings and available analysis")
    rows = [
        (
            "Capital budgeting",
            f"NPV {rupees(m['npv_unhedged'], True)}",
            f"The base case clears {pct(m['wacc'])} WACC, the minimum required return. "
            "An approximately 8% fall in annual cash flow removes the positive NPV.",
            PAGES[1],
            "Expansion & valuation",
        ),
        (
            "Currency protection",
            "25-delta collar selected",
            "Compare a fixed forward rate, a protective put, and a collar. "
            "The collar creates a floor while retaining some benefit from a stronger dollar.",
            PAGES[2],
            "Currency hedging",
        ),
        (
            "Portfolio comparison",
            f"Sharpe {m['sh_hist']:.2f} vs Nifty {m['sh_nifty']:.2f}",
            "Historical allocation modestly outperformed the ML challenger on the reported "
            "risk-adjusted measure. Inspect returns, drawdown, weights, and the test procedure.",
            PAGES[3],
            "Portfolio analysis",
        ),
    ]
    for index, (title, finding, description, page, button) in enumerate(rows):
        with st.container(key=f"finding_{index}"):
            left, right = st.columns([3, 1], gap="large")
            with left:
                st.markdown(f"**{title} · {finding}**")
                st.write(description)
            with right:
                st.button(button, on_click=navigate, args=(page,), key=f"card_{page}", width="stretch")
    st.caption(
        "The five-investment portfolio is an independent experiment. "
        "It does not fund or determine the company's expansion."
    )
    with st.expander("Definitions used in this overview"):
        for term in ("Free cash flow (FCF)", "Present value & discounting", "Net present value (NPV)", "Collar"):
            st.markdown(f"**{term}** — {GLOSSARY[term]}")
    with st.expander("How to use the dashboard"):
        st.write(
            "1. Start with Expansion & valuation to review cash flows and the required return.\n"
            "2. Select a scenario or adjust an assumption; inspect the NPV and explanation.\n"
            "3. Use Currency hedging to compare proceeds at different future exchange rates.\n"
            "4. Use Portfolio analysis to compare allocation methods.\n"
            "5. Open Methods & data for definitions, assumptions, and downloads."
        )


def scenario_defaults(m: dict) -> dict:
    return {"capex": float(C.PROJECT_CAPEX_USD / 1e6), "fcf": 0, "wacc": float(m["wacc"] * 100), "fx": 0, "path": "Keep today's FX rate"}


def set_scenario(m: dict, preset: str) -> None:
    values = scenario_defaults(m)
    if preset == "cash":
        values["fcf"] = -10
    elif preset == "fx":
        values["fx"] = -5
    elif preset == "rate":
        values["wacc"] += 2
    st.session_state["scenario_values"] = values
    for key, value in values.items():
        st.session_state[f"scenario_{key}"] = value


def remember_scenario() -> None:
    st.session_state["scenario_values"] = {
        key: st.session_state[f"scenario_{key}"]
        for key in ("capex", "fcf", "wacc", "fx", "path")
    }


def render_expansion(m: dict) -> None:
    intro("Expansion analysis", "Evaluate the illustrative investment by changing cash flows, the required return, and future exchange rates. Supporting tabs explain the cost of capital and the separate share valuation.", "Capital budgeting and valuation")
    st.caption("Illustrative company cash flows · Rupee totals in ₹ crore · Future payments translated to today's money")
    decision, required, share = st.tabs(["Investment case", "Cost of capital", "Share valuation"])
    with decision:
        render_scenario_lab(m)
    with required:
        render_required_return(m)
    with share:
        render_share_value(m)
    next_section(PAGES[2], "Continue to currency hedging")


def render_scenario_lab(m: dict) -> None:
    st.subheader("Base-case cash flows")
    schedule = pd.DataFrame(
        [[-C.PROJECT_CAPEX_USD / 1e6, *[v / 1e6 for v in C.PROJECT_FCF_USD]]],
        columns=["Initial investment", "Year 1", "Year 2", "Year 3"],
        index=["USD million"],
    )
    st.table(schedule.style.format("{:+.0f}"))
    st.write("The future amounts are **free cash flow**: cash after the operating and investment costs included in the case. These are assumptions, not customer revenue or payments from shareholders.")
    st.subheader("Scenario assumptions")
    st.caption("Choose a preset or edit the inputs. Each preset starts from the base case.")
    actions = [("Reset base case", "base"), ("Cash flows −10%", "cash"), ("USDINR −5%", "fx"), ("WACC +2pp", "rate")]
    for column, (label, preset) in zip(st.columns(4), actions):
        column.button(label, key=f"preset_{preset}", on_click=set_scenario, args=(m, preset), width="stretch")
    saved = st.session_state.get("scenario_values", scenario_defaults(m))
    for key, value in saved.items():
        st.session_state.setdefault(f"scenario_{key}", value)
    a, b = st.columns(2)
    with a:
        capex = st.number_input("Initial investment (USD million)", min_value=40.0, max_value=160.0, step=5.0, key="scenario_capex", on_change=remember_scenario, help="The one-time expansion cost. The original case spends USD 80 million.")
        cash_pct = st.slider("Annual free cash flow change (%)", -50, 50, step=1, key="scenario_fcf", on_change=remember_scenario, help="−10 reduces USD 32m / 36m / 40m to USD 28.8m / 32.4m / 36m.")
    with b:
        rate_pct = st.number_input("Required return / WACC (%)", min_value=1.0, max_value=40.0, step=0.25, format="%.2f", key="scenario_wacc", on_change=remember_scenario, help="Also called discount rate or WACC. It converts future cash into a value today. See the next tab for its calculation.")
        fx_pct = st.slider("Future USDINR change (%)", -15, 15, step=1, key="scenario_fx", on_change=remember_scenario, help="A negative number means a stronger rupee: future dollars buy fewer rupees. Spending today stays at the original spot rate.")
    path = st.radio("FX conversion assumption", ["Keep today's FX rate", "Use the forward-rate path"], horizontal=True, key="scenario_path", on_change=remember_scenario)
    forwards = path == "Use the forward-rate path"
    if forwards:
        st.caption("Uses rates calculated from the two currencies' interest rates. The FX slider models different rates agreed at the outset; an existing forward's locked rate would stay fixed. This is a forward-path comparison, not the selected collar's NPV.")
    else:
        st.caption("The unhedged illustration assumes a constant future exchange rate. The FX slider changes future receipts only; today's spending stays at the original spot rate.")
    flows, fx_path, fcf, value, project_irr = project_scenario(m, capex * 1e6, cash_pct / 100, rate_pct / 100, fx_pct / 100, forwards)
    base = project_scenario(m, C.PROJECT_CAPEX_USD, 0, m["wacc"], 0, forwards)
    rate = rate_pct / 100
    today_values = [cash / (1 + rate) ** year for year, cash in enumerate(flows)]
    st.subheader("Scenario results")
    a, b, c = st.columns(3)
    a.metric("Net present value (NPV)", rupees(value, True), delta=rupees(value - base[3], True), help="Future cash valued today minus spending today. Change is versus the original case with the same FX-path choice.")
    b.metric("Project return (IRR)", pct(project_irr), delta=f"{100 * (project_irr - base[4]):+.2f} percentage points", help="The rate that makes NPV zero, calculated from assumed cash flows. It is not a guaranteed realised return.")
    c.metric("Required return (WACC)", pct(rate), help="The hurdle used to value the future cash.")
    if abs(value) < 1:
        st.warning("At break-even: future cash is worth about the same as spending today.")
    elif value > 0:
        st.success(f"This scenario clears the hurdle. Future cash is worth {rupees(sum(today_values[1:]))} today, compared with {rupees(-flows[0])} spent today.")
    else:
        st.error(f"This scenario does not clear the hurdle. Future cash is worth {rupees(sum(today_values[1:]))} today, below the {rupees(-flows[0])} spent today.")
    changes = []
    if abs(capex * 1e6 - C.PROJECT_CAPEX_USD) > 1:
        changes.append(f"spending is USD {capex:.0f}m")
    if cash_pct:
        changes.append(f"each annual cash flow is {abs(cash_pct)}% {'lower' if cash_pct < 0 else 'higher'}")
    if abs(rate - m["wacc"]) > 1e-10:
        changes.append(f"the required return is {pct(rate)}")
    if fx_pct:
        changes.append(f"future dollars convert into {abs(fx_pct)}% {'fewer' if fx_pct < 0 else 'more'} rupees")
    if changes:
        st.write("**Why it changed:** " + "; ".join(changes) + ". See the cash-flow calculation below.")
    else:
        st.write("**Base-case interpretation:** discounted future cash exceeds the initial cost. About an 8% fall in each annual cash flow removes the positive unhedged NPV.")
    with st.expander("Cash-flow calculation", expanded=True):
        st.write("Money arriving later is translated into an equivalent value today. Divide each payment by (1 + required return) once for every year of waiting.")
        labels = ["Today", *[f"End of year {year}" for year in range(1, len(flows))]]
        calculation = pd.DataFrame({
            "When": labels, "Cash (USD million)": np.array([-capex * 1e6, *fcf]) / 1e6,
            "Rupees per USD": fx_path, "Cash (₹ crore)": np.array(flows) / CRORE,
            "Value today (₹ crore)": np.array(today_values) / CRORE,
        })
        formats = {"Cash (USD million)": "{:+,.1f}", "Rupees per USD": "{:,.2f}", "Cash (₹ crore)": "{:+,.2f}", "Value today (₹ crore)": "{:+,.2f}"}
        st.dataframe(calculation.style.format(formats), hide_index=True, width="stretch")
        st.write(f"**Future cash valued today {rupees(sum(today_values[1:]))} − spending today {rupees(-flows[0])} = {rupees(value, True)} NPV.**")
        st.caption("₹1 crore = ₹10 million. Year 3 includes zero salvage; there is no additional terminal value.")
        plot = pd.DataFrame({"When": labels, "Value today (₹ crore)": np.array(today_values) / CRORE})
        chart = alt.Chart(plot).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("When:N", sort=labels, title=None), y="Value today (₹ crore):Q",
            color=alt.condition(alt.datum["Value today (₹ crore)"] < 0, alt.value("#b35252"), alt.value(COLORS[1])),
            tooltip=["When", alt.Tooltip("Value today (₹ crore):Q", format=",.2f")],
        ).properties(height=250)
        st.altair_chart(chart, width="stretch")
    with st.expander("More detail: compare required returns and cash-flow changes"):
        st.caption("Each cell is NPV in ₹ crore. Columns vary annual cash flows; rows vary the required return. Other selected assumptions stay the same.")
        rates = np.linspace(max(.01, rate - .02), rate + .02, 5)
        shocks = np.linspace(cash_pct / 100 - .2, cash_pct / 100 + .2, 5)
        grid = [[project_scenario(m, capex * 1e6, float(s), float(r), fx_pct / 100, forwards)[3] / CRORE for s in shocks] for r in rates]
        table = pd.DataFrame(grid, index=[f"Required {r:.1%}" for r in rates], columns=[f"Cash {s:+.0%}" for s in shocks])
        extent = max(float(np.abs(grid).max()), 1)
        st.dataframe(table.style.format("{:+.1f}").background_gradient(cmap="RdYlGn", axis=None, vmin=-extent, vmax=extent), width="stretch")


def render_required_return(m: dict) -> None:
    st.subheader("Required return on equity")
    st.write("Owners could use their money elsewhere. They require compensation for waiting and taking business risk. First estimate what shareholders require, then combine that with any borrowing cost.")
    stages = [
        ("Government-bond benchmark", pct(m["rf_in"]), "India government-bond benchmark. A labelled fallback because the live rate did not load."),
        ("Estimated market beta", f"{m['beta']:.2f} beta", "Estimated from weekly Infosys and Nifty returns. Below 1 means lower market sensitivity on this sample."),
        ("Assumed equity risk premium", pct(m["erp"]), "An assumed extra return for stock-market risk above the starting benchmark: the equity risk premium."),
    ]
    st.dataframe(
        pd.DataFrame(stages, columns=["Component", "Value", "Meaning and source"]),
        hide_index=True,
        width="stretch",
    )
    st.markdown(f"**CAPM: {pct(m['rf_in'])} + {m['beta']:.2f} × {pct(m['erp'])} ≈ {pct(m['ke_capm'])}.**")
    st.write("This is a required return, rather than a promise about the stock's future performance. CAPM uses broad market sensitivity; company-specific events can still move Infosys differently.")
    st.subheader("From shareholders' return to WACC")
    st.write(f"WACC combines the required return on ownership and the after-tax borrowing cost. The saved company mix is {m['we']:.3%} equity and {1 - m['we']:.3%} debt. Its average is therefore almost the shareholders' {pct(m['ke_capm'])}: **{pct(m['wacc'])} WACC**.")
    st.caption("These proportions use market-value equity and reported debt. They do not describe the cash balance or a new loan for the USD 80m expansion.")
    with st.expander("Show formulas, the bond example, and the FX cross-check"):
        st.latex(r"k_e = r_f + \beta\, ERP")
        st.latex(r"WACC = w_E k_e + (1-w_E)k_D(1-\mathrm{tax})")
        st.write(f"The comparable bond has a {C.BOND_COUPON:.2%} coupon and a {C.BOND_YTM:.2%} yield. Yield represents borrowing cost; coupon is the contracted payment. This is a method example, not a documented expansion loan.")
        st.write(f"A second regression adds USDINR returns to Nifty excess returns and gives a {pct(m['ke_fx'])} cost of equity. It is a cross-check; the expansion uses CAPM-based WACC.")
        st.write(f"The sample market premium was {pct(m['erp_sample'])}; required return uses the labelled {pct(m['erp'])} assumption.")
        chart_image("03_factor_ke.png", "Saved market and FX contributions to the estimated required return.")
        chart_image("02_sml.png", "Course illustration of beta and required return.")


def render_share_value(m: dict) -> None:
    st.subheader("Gordon dividend valuation")
    st.write("The company may pay its owners cash called a dividend. Gordon valuation adds the value today of future dividends, assuming constant growth forever. This is separate from the expansion decision.")
    dividend = m["dps"] * (1 + C.GORDON_G)
    first_pv = dividend / (1 + m["ke_capm"])
    st.markdown(f"**Start with ₹{m['dps']:.2f} per share** paid over the past year. Assume {C.GORDON_G:.0%} growth: next year's dividend becomes **₹{dividend:.2f}**.")
    st.write(f"Shareholders require {pct(m['ke_capm'])} for taking risk. At that rate, next year's ₹{dividend:.2f} is worth about **₹{first_pv:.2f} today**. Repeat this for all future growing dividends and add their present values.")
    a, b = st.columns(2)
    a.metric("Dividend-model value per share", f"₹{m['gordon']:,.2f}", help="An estimate using assumed 5% perpetual dividend growth; not a cash payment.")
    b.metric("Observed market price per share", f"₹{m['px']:,.2f}", help=f"Saved Infosys price as of {date_label(m['asof'])}.")
    st.info("The market price is above this simple model's estimate. That does not prove mispricing: the estimate depends strongly on assumed dividend growth.")
    with st.expander("Show the Gordon calculation"):
        st.latex(r"P_0 = \frac{D_1}{k_e-g}")
        st.write(f"₹{dividend:.2f} next dividend ÷ ({pct(m['ke_capm'])} required return − {pct(C.GORDON_G)} growth) ≈ ₹{m['gordon']:,.2f} per share. Calculations use the full-precision rate.")
        st.write(f"Growth must be below required return. The market price implies about {pct(m['impl_g'])} growth with this same next-dividend input. A one-stage model cannot capture changing growth or payout policies.")


def set_hedge_rate(value: float) -> None:
    st.session_state["hedge_future_rate"] = value
    st.session_state["saved_hedge_rate"] = value


def remember_hedge_rate() -> None:
    st.session_state["saved_hedge_rate"] = st.session_state["hedge_future_rate"]


def render_hedging(m: dict) -> None:
    intro("Currency hedging", "Assess the rupee proceeds from a future dollar receipt under four protection strategies. A stronger rupee reduces the conversion value of each dollar; the controls make that exposure visible.", "Treasury analysis")
    st.info(f"This separate Treasury illustration uses **USD {m['notional'] / 1e6:.0f} million of receipts** in one year. This is a hedge notional; expansion year-one free cash flow is USD {C.PROJECT_FCF_USD[0] / 1e6:.0f}m. Receipts and cash after all costs are different quantities.")
    st.write(f"Today, **USD 1 = ₹{m['spot_fx']:.2f}**. A fall to ₹{m['spot_fx'] * .9:.2f} buys fewer rupees per dollar. A higher USDINR rate means more rupees per dollar.")
    st.subheader("Exchange-rate scenario")
    presets = [("USDINR −10%", m["spot_fx"] * .9), ("Reset to spot", m["spot_fx"]), ("USDINR +10%", m["spot_fx"] * 1.1)]
    for column, (label, value) in zip(st.columns(3), presets):
        column.button(label, on_click=set_hedge_rate, args=(float(value),), key=f"hedge_{label}", width="stretch")
    st.session_state.setdefault("hedge_future_rate", st.session_state.get("saved_hedge_rate", float(m["spot_fx"])))
    terminal = st.slider("Future rupees for USD 1", min_value=float(m["spot_fx"] * .85), max_value=float(m["spot_fx"] * 1.15), step=.1, format="₹%.2f", key="hedge_future_rate", on_change=remember_hedge_rate, help="A hypothetical one-year receipt-date rate, not a prediction. Hedge strikes and premiums stay at the saved snapshot.")
    results = hedge_table(np.array([terminal]), m["fwd"], m["put_k"], m["call_k"], m["put_prem"], m["collar_net"], m["notional"])
    names = {"unhedged_inr_m": "Keep the FX risk", "forward_inr_m": "Sell dollars forward", "put_inr_m": "Buy a USD put", "collar_inr_m": "Use a collar · selected"}
    amounts = [float(results.iloc[0][key]) / 10 for key in names]
    table = pd.DataFrame({"Approach": list(names.values()), "Rupees received (₹ crore)": amounts, "Change vs unhedged (₹ crore)": np.array(amounts) - amounts[0]})
    st.subheader("Comparative receipt values")
    st.dataframe(table.style.format({"Rupees received (₹ crore)": "{:,.2f}", "Change vs unhedged (₹ crore)": "{:+,.2f}"}), hide_index=True, width="stretch")
    st.caption("Put and collar amounts subtract saved premiums using the project's simplified convention. Premium financing, dealer spreads, and default risk are not modelled.")
    st.write(f"**At ₹{terminal:.2f} per dollar:** the collar produces {rupees(amounts[3] * CRORE)} versus {rupees(amounts[0] * CRORE)} without protection. A forward produces {rupees(amounts[1] * CRORE)} regardless of the terminal rate in this illustration.")
    with st.expander("Strategy definitions and trade-offs", expanded=True):
        policies = [
            ("Keep the FX risk", "No premium, no floor. Receive whatever the future rate gives."),
            ("Sell dollars forward", f"Lock ₹{m['fwd']:.2f} per dollar. Most certainty, with no benefit from a stronger dollar."),
            ("Buy a USD put", f"A right to sell at ₹{m['put_k']:.2f}. The floor costs ₹{m['put_prem']:.3f} per dollar; you keep the upside."),
            ("Use a collar", f"Buy the put and sell a call. The band is ₹{m['put_k']:.2f} to ₹{m['call_k']:.2f}, before the ₹{m['collar_net']:.3f} net premium per dollar."),
        ]
        for title, description in policies:
            st.markdown(f"**{title}.** {description}")
    st.markdown("**Policy interpretation.** The case selects the collar: downside protection at a small net premium with some benefit if the dollar rises. This reflects a preference for partial upside; a forward gives greater certainty.")
    st.subheader("Receipt profiles across exchange rates")
    panel = hedge_table(np.linspace(m["spot_fx"] * .85, m["spot_fx"] * 1.15, 61), m["fwd"], m["put_k"], m["call_k"], m["put_prem"], m["collar_net"], m["notional"])
    panel = panel.rename(columns={"usd_inr": "Future rupees per USD", **names})
    for name in names.values():
        panel[name] /= 10
    long = panel.melt(id_vars="Future rupees per USD", var_name="Approach", value_name="Receipts (₹ crore)")
    chart = alt.Chart(long).mark_line(strokeWidth=2.5).encode(
        x=alt.X("Future rupees per USD:Q", scale=alt.Scale(zero=False)),
        y=alt.Y("Receipts (₹ crore):Q", scale=alt.Scale(zero=False)),
        color=alt.Color("Approach:N", scale=alt.Scale(domain=list(names.values()), range=COLORS[:4]), legend=alt.Legend(orient="bottom", columns=2)),
        tooltip=["Approach", alt.Tooltip("Future rupees per USD:Q", format=".2f"), alt.Tooltip("Receipts (₹ crore):Q", format=",.2f")],
    ).properties(height=320)
    st.altair_chart(chart, width="stretch")
    st.caption("Left to right: stronger rupee to weaker rupee. The forward line locks proceeds; the collar line is flat below its floor and above its cap.")
    with st.expander("More detail: how the saved hedge was priced"):
        reduction = 1 - m["collar_vol"] / m["unhedged_vol"]
        st.write(f"Strikes give approximately −0.25 put delta and +0.25 call delta. Pricing uses INR and USD interest rates and {pct(m['fx_vol'])} realised FX volatility.")
        st.write(f"The saved scenario-dispersion reduction is {reduction:.0%}: a standard-deviation comparison across 61 equally spaced rates from −15% to +15%, not a probability-weighted risk forecast.")
        st.write("Forwards use interest-rate parity, T+2 spot settlement, USD actual/360 and INR actual/365. The calendar skips weekends but not holidays. Both expansion NPV paths use the same INR WACC.")
    with st.expander("What is an average-rate (Asian) option?"):
        st.write("Its payoff depends on average monthly fixings instead of one final rate. Averaging changes the exposure and usually dampens volatility. It suits receipts genuinely converted on averaging dates.")
        st.write(f"The saved pricing example compares an at-the-money Asian **call** at ₹{m['asian']:.3f} per dollar with a vanilla call at ₹{m['vanilla_call']:.3f}. This compares prices, not identical protection to a collar. A floor for dollar receipts uses a put payoff.")
        st.button("Open option pricing", on_click=navigate, args=(PAGES[4],), key="hedge_to_options")
    next_section(PAGES[3], "Continue to portfolio analysis")


def strategy_table(metrics: pd.DataFrame, detailed: bool = False) -> pd.DataFrame:
    columns = {"sharpe": "Sharpe ratio", "ann_mean": "Average annual return", "ann_vol": "Annual volatility", "max_drawdown": "Largest decline"}
    if detailed:
        columns.update({"annual_turnover": "Annual turnover", "beta": "Market beta", "jensen": "Jensen alpha", "tracking_error": "Tracking error", "info_ratio": "Information ratio"})
    order = [key for key in STRATEGY_NAMES if key in metrics.index]
    return metrics.loc[order, list(columns)].rename(columns=columns, index=STRATEGY_NAMES).rename_axis("Strategy").reset_index()


def render_portfolio(m: dict) -> None:
    intro("Portfolio performance", "Compare historical and machine-learning allocation across five investments. Results use subsequent returns that were unavailable when each forecast was made, with the stated trading assumptions.", "Allocation and model evaluation")
    st.caption("Historical backtest after modelled costs · These holdings are separate from the company's expansion")
    st.write("**Five investments:** Infosys, HDFC Bank, Reliance, Hindustan Unilever, and a gold ETF. They represent different business and asset exposures.")
    metrics, weights = load_csv("ml_backtest.csv"), load_csv("ml_last_weights.csv")
    if metrics.empty:
        st.info("Saved strategy metrics are unavailable. The written note is available in Methods & data.")
        return
    descriptions = {
        "hist_mv": "Uses trailing historical average returns and a stabilised estimate of how assets move together. Selected on the reported comparison.",
        "gb_mv": "Blends 80% expanding historical mean with 20% gradient-boosting forecasts, then uses the same allocation procedure as the historical rule.",
        "nifty": "The broad Indian stock-index return series, used as the market benchmark.",
        "inv_vol": "Gives more weight to assets with lower estimated volatility, with the same position cap.",
        "equal": "Uses a 20% weight for each investment as a simple comparator.",
    }
    choice = st.selectbox("Strategy detail", list(STRATEGY_NAMES), format_func=STRATEGY_NAMES.get, key="portfolio_choice")
    st.write(descriptions[choice])
    row = metrics.loc[choice]
    a, b, c = st.columns(3)
    a.metric("Sharpe ratio", f"{row['sharpe']:.2f}", help="Return above the risk-free rate divided by volatility. 0.30 does not mean 30% return.")
    b.metric("Average annual return", pct(row["ann_mean"], 1), help="Weekly arithmetic mean × 52; not a compounded annual growth rate.")
    c.metric("Maximum drawdown", pct(row["max_drawdown"], 1), help="The largest recorded decline from an earlier high.")
    st.subheader("Strategy comparison")
    formats = {"Sharpe ratio": "{:.2f}", "Average annual return": "{:.1%}", "Annual volatility": "{:.1%}", "Largest decline": "{:.1%}", "Annual turnover": "{:.2f}×", "Market beta": "{:.2f}", "Jensen alpha": "{:.2%}", "Tracking error": "{:.1%}", "Information ratio": "{:.2f}"}
    simple_formats = {key: value for key, value in formats.items() if key in strategy_table(metrics).columns}
    st.dataframe(strategy_table(metrics).style.format(simple_formats), hide_index=True, width="stretch")
    st.caption("Sharpe: higher is better on this sample. Volatility: how much returns vary. Largest decline: closer to zero means a smaller loss from a peak.")
    st.markdown(f"**Model selection.** Historical allocation led at {m['sh_hist']:.2f} Sharpe, ahead of ML at {m['sh_gb']:.2f} and Nifty at {m['sh_nifty']:.2f}. The historical rule was selected.")
    st.write(f"The advantage is modest. Its market beta was {m['beta_hist']:.2f}, so lower market exposure contributed. Its information ratio versus Nifty was only {m['ir_hist']:.2f}; one test does not establish a lasting edge.")
    with st.expander("See the portfolio value through time"):
        chart_image("08_ml_nav.png", "Saved walk-forward wealth paths compound recorded weekly returns. This is not a future projection.")
    st.subheader("Selected portfolio allocation")
    st.caption("Average weights describe the whole test. The latest rebalance can look different.")
    if not weights.empty:
        names = weights.rename(index=ASSET_NAMES)
        a, b = st.columns([1.15, 1])
        with a:
            plot = names[["average"]].rename(columns={"average": "Average allocation"}).rename_axis("Investment").reset_index()
            chart = alt.Chart(plot).mark_bar(color=COLORS[0], cornerRadiusEnd=4).encode(
                y=alt.Y("Investment:N", sort="-x", title=None),
                x=alt.X("Average allocation:Q", axis=alt.Axis(format="%"), title="Share of portfolio"),
                tooltip=["Investment", alt.Tooltip("Average allocation:Q", format=".1%")],
            ).properties(height=230)
            st.altair_chart(chart, width="stretch")
        with b:
            shown = names.rename(columns={"average": "Whole-test average", "last": "Latest rebalance"})[["Whole-test average", "Latest rebalance"]]
            st.dataframe(shown.style.format("{:.1%}"), width="stretch")
    with st.expander("Machine-learning evaluation procedure"):
        st.markdown(
            "1. Use at least 104 weeks of history before forecasting.\n"
            "2. Build inputs from past returns, Nifty, USDINR, and eight-week volatility.\n"
            "3. Fit on earlier observations and predict the next week; refit every four weeks.\n"
            "4. Blend gradient boosting with the historical mean for allocation. Ridge is a forecast comparator; it does not drive the ML portfolio.\n"
            "5. Compare later realised portfolio returns with the historical rule and benchmarks."
        )
        st.write(f"Infosys forecast error (weekly RMSE): gradient boosting {m['rmse_gb']:.4f}, Ridge {m['rmse_ridge']:.4f}, historical mean {m['rmse_hist']:.4f}. Lower is better. Gradient boosting did not improve the forecast; its sign hit rate was {pct(m['hit_gb'], 1)}.")
    with st.expander("Allocation, trading assumptions, and full statistics"):
        st.write(f"The rules use Ledoit–Wolf covariance on a trailing 52-week window, rebalance every {C.REBALANCE_WEEKS} weeks, allow no shorts, and cap each name at {C.MAX_WEIGHT:.0%}. Starting from tangency weights, the code removes negative weights and applies the cap; this approximates a constrained optimiser.")
        st.write(f"Costs are {C.TRANSACTION_COST_BPS} basis points (0.10%) per unit of one-way turnover. The equal-weight comparator has fixed weights with no charged turnover; Nifty is an index series. Holdings do not drift between rebalances in this simplified backtest.")
        st.dataframe(strategy_table(metrics, detailed=True).style.format(formats), hide_index=True, width="stretch")
        st.write(GLOSSARY["Jensen alpha, tracking error & information ratio"])
        chart_image("01_frontier_cml.png", "The course frontier allows shorts. It differs from the held, long-only capped portfolio.")
    next_section(PAGES[4], "Continue to option pricing")


def set_option_inputs(m: dict, extra_vol: bool = False) -> None:
    values = {
        "spot": float(m["spot_fx"]), "strike": float(m["put_k"]), "months": 12,
        "vol": float(m["fx_vol"] * 100 + (2 if extra_vol else 0)),
        "domestic": float(m["rf_in"] * 100), "foreign": float(m["rf_us"] * 100),
        "kind": "Put · right to sell USD", "steps": 50, "paths": 10000,
    }
    st.session_state["option_values"] = values
    for key, value in values.items():
        st.session_state[f"option_{key}"] = value


def remember_options() -> None:
    st.session_state["option_values"] = {key: st.session_state[f"option_{key}"] for key in ("spot", "strike", "months", "vol", "domestic", "foreign", "kind", "steps", "paths")}


def render_options(m: dict) -> None:
    intro("Option pricing", "Price a USD put or call using a closed-form formula, a binomial tree, and an average-rate simulation. Input explanations and price sensitivities are available alongside the results.", "FX derivatives")
    st.caption("Interactive FX example · European exercise · Separate from the saved listed Infosys ADR call")
    a, b = st.columns(2)
    a.button("Reset inputs", on_click=set_option_inputs, args=(m,), width="stretch")
    b.button("Volatility +2pp", on_click=set_option_inputs, args=(m, True), width="stretch", help="The saved example with annual volatility two percentage points higher.")
    if "option_values" not in st.session_state:
        set_option_inputs(m)
    for key, value in st.session_state["option_values"].items():
        st.session_state.setdefault(f"option_{key}", value)
    kind_name = st.radio("Option type", ["Put · right to sell USD", "Call · right to buy USD"], key="option_kind", horizontal=True, on_change=remember_options)
    kind = "put" if kind_name.startswith("Put") else "call"
    a, b = st.columns(2)
    with a:
        spot = st.number_input("Rupees per dollar today", min_value=.01, step=.1, key="option_spot", on_change=remember_options, help="The starting USDINR exchange rate, also called spot.")
        strike = st.number_input("Agreed exercise rate · strike (₹ per USD)", min_value=.01, step=.1, key="option_strike", on_change=remember_options, help="The rate at which the buyer can sell dollars (put) or buy dollars (call).")
    with b:
        months = st.slider("Time until expiry (months)", 1, 24, key="option_months", on_change=remember_options)
        vol_pct = st.number_input("Annual FX volatility (%)", min_value=.1, max_value=60.0, step=.5, format="%.2f", key="option_vol", on_change=remember_options, help="Exchange-rate variability. The original example uses realised volatility, not a market option-implied quote.")
    with st.expander("Model settings: rates and numerical accuracy"):
        a, b = st.columns(2)
        domestic = a.number_input("India interest rate (%)", min_value=0.0, max_value=30.0, step=.25, format="%.2f", key="option_domestic", on_change=remember_options)
        foreign = b.number_input("US interest rate (%)", min_value=0.0, max_value=30.0, step=.25, format="%.2f", key="option_foreign", on_change=remember_options)
        steps = a.select_slider("Binomial tree steps", [10, 20, 50, 100, 200], key="option_steps", on_change=remember_options)
        paths = b.select_slider("Simulated average-rate paths", [2000, 5000, 10000, 20000, 40000], key="option_paths", on_change=remember_options)
        st.caption("The average uses 12 equally spaced fixings. A fixed random seed makes simulation repeatable; more paths reduce sampling noise.")
    tenor, rate, div, vol = months / 12, domestic / 100, foreign / 100, vol_pct / 100
    bs = bs_price(spot, strike, tenor, rate, vol, kind, div)
    dt = tenor / steps
    up = np.exp(vol * np.sqrt(dt))
    probability = (np.exp((rate - div) * dt) - 1 / up) / (up - 1 / up)
    valid = 0 < probability < 1
    tree = crr_price(spot, strike, tenor, rate, vol, steps, kind, div=div) if valid else None
    asian = asian_arithmetic(spot, strike, tenor, rate, vol, kind, n_steps=C.ASIAN_STEPS, n_paths=paths, seed=7, div=div)
    greeks = bs_greeks(spot, strike, tenor, rate, vol, kind, div)
    st.subheader("Model prices · ₹ per USD 1")
    a, b, c = st.columns(3)
    a.metric("Black–Scholes FX", f"₹{bs:.4f}", help="Includes the USD foreign interest rate, often called Garman–Kohlhagen pricing.")
    b.metric(f"Binomial tree · {steps} steps", f"₹{tree:.4f}" if tree is not None else "Adjust settings", help="A numerical approximation for the same European terminal payoff.")
    c.metric("Average-rate option · simulation", f"₹{asian:.4f}", help="A different payoff based on average fixings, rather than a convergence check against the other two.")
    if not valid:
        st.warning("These inputs give an invalid tree probability. Increase tree steps or reduce the rate gap before comparing the binomial price.")
    if kind == "put":
        st.write(f"**What you are buying:** the right to sell USD 1 at ₹{strike:.2f} after {months} months. The model premium is ₹{bs:.4f} per dollar. The put can protect receipts when the rupee strengthens.")
    else:
        st.write(f"**What you are buying:** the right to buy USD 1 at ₹{strike:.2f} after {months} months. The model premium is ₹{bs:.4f} per dollar. A long call can protect dollar payments; the exporter collar sells a call to help pay for its put.")
    st.write("The formula and tree price the same terminal payoff. The Asian payoff depends on an average, so its price can differ. More uncertainty generally raises vanilla option value; try the example above.")
    grid = np.linspace(spot * .75, spot * 1.25, 60)
    plot = pd.DataFrame({"Starting rupees per USD": grid, "Option price (₹ per USD)": [bs_price(float(s), strike, tenor, rate, vol, kind, div) for s in grid]})
    st.line_chart(plot.set_index("Starting rupees per USD"), color=COLORS[0], x_label="Starting exchange rate (₹ per USD)", y_label="Option price (₹ per USD)")
    st.caption("The curve varies today's starting exchange rate with other inputs fixed. It shows option prices, not terminal cash proceeds.")
    with st.expander("Explain the sensitivities · Greeks"):
        st.write("Each Greek changes one input while holding others fixed. These approximate small changes.")
        rows = [
            ("Delta", f"{greeks.delta:.4f}", "Price change (₹ per USD) when spot rises by ₹1 per USD."),
            ("Gamma", f"{greeks.gamma:.4f}", "Change in delta when spot rises by ₹1 per USD."),
            ("Vega · +1 percentage point", f"₹{greeks.vega / 100:.4f}", "Price change if volatility rises, for example, from 5% to 6%."),
            ("Theta · one day passes", f"₹{greeks.theta / 365:.4f}", "Price change for one calendar day passing, using 365 days."),
        ]
        st.dataframe(pd.DataFrame(rows, columns=["Sensitivity", "Value", "Meaning"]), hide_index=True, width="stretch")
    with st.expander("Saved market example: the listed Infosys ADR call"):
        st.write(f"The separate saved US-listed {m['opt_ticker']} ADR example has strike USD {m['opt_k']:.2f} and expiry {m['opt_exp']}, from the {date_label(m['asof'])} snapshot. It differs from the USDINR calculator above.")
        st.write(f"Mid USD {m['opt_mid']:.3f} → backed-out IV {pct(m['opt_iv'], 1)} → formula price USD {m['opt_bs']:.3f}. Equality is by construction. The numerical check is the 50-step tree at USD {m['opt_crr']:.3f} versus the formula.")
        chart_image("05_crr_vs_bs.png", "Saved binomial convergence against the closed-form value.")
        chart_image("06_greeks.png", "Saved delta and gamma across underlying ADR prices.")
    next_section(PAGES[5], "Continue to methods and data")


def render_methods(m: dict) -> None:
    intro("Methods and data", "Review definitions, distinguish assumptions from observed inputs, and download the saved analysis. Each source and modelling choice is identified below.", "Documentation")
    glossary, sources, downloads = st.tabs(["Look up a term", "Assumptions & sources", "Download the results"])
    with glossary:
        search = st.text_input("Search definitions", placeholder="Try: share, 10.96, cash flow, collar, Sharpe…", key="glossary_search")
        matches = [(term, text) for term, text in GLOSSARY.items() if not search.strip() or search.casefold().strip() in f"{term} {text}".casefold()]
        st.caption(f"{len(matches)} matching definitions")
        if not matches:
            st.info("No match. Try a shorter term such as ‘return’, ‘share’, ‘cash’, or ‘risk’.")
        for term, text in matches:
            with st.expander(term, expanded=bool(search.strip())):
                st.write(text)
    with sources:
        st.subheader("What is data, and what is an assumption?")
        rows = [
            ("Observed market data", "Price / FX snapshot", f"{date_label(m['asof'])} · public Yahoo Finance series"),
            ("Observed market data", "USDINR spot", f"₹{m['spot_fx']:.2f} per dollar"),
            ("Calculated from data", "Infosys beta", f"{m['beta']:.2f} · weekly Infosys vs Nifty returns from 2019"),
            ("Labelled fallback", "India government-bond benchmark", f"{pct(m['rf_in'])} · live FRED pull failed"),
            ("Modelling assumption", "India equity risk premium", pct(m["erp"])),
            ("Calculated output", "CAPM required return / WACC", f"{pct(m['ke_capm'])} / {pct(m['wacc'])}"),
            ("Modelling assumption", "Spending / annual free cash", "USD 80m today / USD 32m, 36m, 40m"),
            ("Modelling assumption", "Project end value", "Zero at year 3; no terminal value"),
            ("Separate hedge assumption", "One-year dollar receipts", f"USD {m['notional'] / 1e6:.0f}m · separate from year-one FCF"),
            ("Modelling assumption", "Perpetual dividend growth", pct(C.GORDON_G)),
            ("Method illustration", "Comparable bond yield / tax", f"{pct(C.BOND_YTM)} / {pct(C.TAX_RATE)}"),
            ("Calculated from data", "FX volatility", f"{pct(m['fx_vol'])} realised, not option-implied"),
            ("Backtest assumption", "Position limit / rebalance", f"{C.MAX_WEIGHT:.0%} per asset / every {C.REBALANCE_WEEKS} weeks"),
            ("Backtest assumption", "One-way transaction cost", f"{C.TRANSACTION_COST_BPS} basis points = 0.10%"),
        ]
        st.dataframe(pd.DataFrame(rows, columns=["Type", "Input or result", "Value / source"]), hide_index=True, width="stretch")
        st.caption(f"Saved market pull: {m['pulled']}. Opening the dashboard does not download prices or retrain the models.")
        st.subheader("How the pieces fit together")
        st.markdown("1. **Estimate risk:** weekly returns → CAPM and the market-plus-FX cross-check.\n2. **Value cash:** required return → Gordon share value and a separate expansion NPV.\n3. **Shape FX exposure:** compare forwards and options for dollar receipts.\n4. **Compare allocation:** earlier observations → forecast → next-week returns → portfolio statistics.")
        st.write("Mastercard versus the S&P 500 is a comparator in the written note, not a holding in the Indian portfolio or the rate used for the expansion.")
        st.link_button("Open the project repository", "https://github.com/arathii23/asset-pricing-and-hedging")
    with downloads:
        st.write("Download the recommendation or inspect the exact data behind the results.")
        files = [
            ("Written investment note", C.MEMO_DIR / "ic_note.md", "text/markdown"),
            ("Base-case numbers · JSON", SUMMARY, "application/json"),
            ("Strategy statistics · CSV", C.EXHIBIT_DIR / "ml_backtest.csv", "text/csv"),
            ("Average and latest weights · CSV", C.EXHIBIT_DIR / "ml_last_weights.csv", "text/csv"),
            ("Saved hedge scenarios · CSV", C.EXHIBIT_DIR / "hedge_scenarios.csv", "text/csv"),
            ("Static report · HTML", C.MEMO_DIR / "ic_pack.html", "text/html"),
        ]
        columns = st.columns(2)
        for i, (label, path, mime) in enumerate(files):
            if path.exists():
                columns[i % 2].download_button(label, path.read_bytes(), file_name=path.name, mime=mime, width="stretch")
    next_section(PAGES[0], "Return to overview")


def main() -> None:
    st.set_page_config(page_title="Asset Pricing and Hedging", layout="wide", initial_sidebar_state="auto")
    m = load_summary()
    if not m:
        st.error("The saved project results are unavailable. Please try again later.")
        st.stop()
    pages = {
        title: st.Page(C.ROOT / "views" / f"{filename}.py", title=title, url_path=slug, default=i == 0)
        for i, (title, filename, slug) in enumerate(zip(PAGES, PAGE_FILES, PAGE_SLUGS))
    }
    current = st.navigation(list(pages.values()), position="hidden")
    requested = st.session_state.pop("pending_section", None)
    if requested in pages and requested != current.title:
        st.switch_page(pages[requested])
    st.markdown(STYLES + section_styles(current.title), unsafe_allow_html=True)
    render_sidebar(m, pages)
    current.run()
    st.markdown(f'<div class="app-footer">Asset Pricing &amp; Hedging · ECO423, IIT Kanpur · Saved snapshot {escape(date_label(m["asof"]))} · Illustrative educational analysis</div>', unsafe_allow_html=True)
