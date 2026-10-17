# Asset Pricing and Hedging

An investment-committee style project for a dollar-earning firm. It answers two questions with public market data:

1. Should the firm fund a 3-year expansion?
2. How should it protect the dollars it expects to receive if the rupee–dollar rate moves?

The finance methods follow a standard financial-economics course: portfolios, CAPM, factor models, cost of capital, stock and bond valuation, forwards, binomial and Black–Scholes pricing, Greeks, and hedge design. A small walk-forward machine-learning step sits on top. It does not override the finance decision.

**Stack:** Python, pandas, NumPy, scikit-learn, Streamlit  
**Data:** public Yahoo prices (Infosys, HDFC Bank, Reliance, Hindustan Unilever, a gold ETF, Nifty, Mastercard, USDINR, US 10-year)

## What you see

| Piece | Where |
|---|---|
| Guided dashboard (project story, expansion, dollar protection, portfolio, options, glossary) | `app.py` |
| Static coverage note | `memo/ic_pack.html` |
| Written IC note | `memo/ic_note.md` |
| Charts and tables | `exhibits/` |
| Pricing and portfolio engines | `src/` |

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints (usually `http://localhost:8501`).

## Explore the dashboard

The app opens with an **Overview** of the case, its cash flows, and the main findings.
Definitions are available alongside the analysis. Use the sidebar to move between sections:

1. **Expansion & valuation:** review future cash flows, try a cash-flow reduction or a stronger rupee, and inspect the calculation. Separate tabs explain the required return and Gordon share valuation.
2. **Currency hedging:** compare unhedged receipts, a forward, a put, and a collar at a chosen future exchange rate. The USD 36m hedge notional is separate from the expansion's USD 32m year-one free cash flow.
3. **Portfolio analysis:** compare five allocation rules, understand their risk and return, and inspect average versus latest holdings.
4. **Option pricing:** vary FX option inputs, see prices per dollar, and open explanations of Greeks and the separate saved Infosys ADR example.
5. **Methods & data:** search a plain-language glossary, distinguish assumptions from observed data, and download the report and exact results.

Rupee totals use **₹ crore** (₹1 crore = ₹10 million); dollar totals use **USD million**.
Rates are entered as percentages. Detailed formulas and statistics sit behind expanders.

Scenario and pricing controls calculate in memory and never overwrite the published
base case. In the expansion scenario, an FX change affects **future receipts only**;
today's capex stays converted at the saved spot rate. In a forward-path scenario,
the slider represents different rates agreed at the outset, not repricing an existing
locked forward. The project NPV comparison is not a collar-valued NPV.

The saved exhibits supply the published portfolio statistics and weights. Only the
selected sidebar section renders, so opening the home page does not run option simulations.
The app makes no live data requests or model-training calls when a visitor opens it.
Each section has a direct URL and uses native page navigation. Page entry files are in `views/`;
presentation and shared reference material are in `src/dashboard.py` and `src/dashboard_content.py`.

The dashboard uses the saved results in `exhibits/`. To recompute everything from current market data:

```bash
python run_ic_pack.py
```

Add `--force` to ignore the price cache and download again. `run_ic_pack.py --no-open` skips opening the HTML note.

## Put it on the web

1. Sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub.
2. Create a new app from this repository.
3. Branch: `main`. Main file: `app.py`.
4. Deploy and use the `*.streamlit.app` link.

## How the pack is built

1. **Prices.** Weekly returns for the coverage universe.
2. **Portfolios.** Mean-variance frontier and the two-fund line (cash plus the tangency portfolio).
3. **Required return.** CAPM beta versus Nifty, then a market-plus-FX factor model. Cost of equity becomes WACC. The cost of debt is a bond yield, not the coupon.
4. **Valuation.** Gordon dividend model versus the market price. A comparable coupon bond is marked with yield, duration, and convexity.
5. **The project.** A labelled USD expansion is converted to rupees and discounted. NPV and IRR are shown unhedged and on a forward FX path.
6. **Hedges.** Covered-interest FX forward (spot lag and day-count), binomial tree versus Black–Scholes, Greeks, a collar, and an average-rate option.
7. **Machine learning.** Walk-forward Ridge and gradient boosting are a robustness check.
   The rule that is kept is the simpler one: monthly, long-only mean-variance on trailing
   historical returns, with Ledoit–Wolf covariance, a 35% position cap, and 10 bps
   turnover costs. It is compared out of sample with the boosted book, inverse volatility,
   equal weight, and Nifty. ML is a challenger, not a rule that overrides WACC or the collar.

Identity checks (put-call parity, binomial versus Black–Scholes, bond yield round-trip, forward direction, OLS beta) run in `src/checks.py` before any download.

## Layout

```
app.py              Streamlit dashboard
run_ic_pack.py      Rebuild numbers, charts, and the memo
src/config.py       Tickers, tax rate, growth, and project size
src/                  CAPM, factors, WACC, valuation, FX, options, hedges, ML
memo/                 IC note (Markdown and HTML)
exhibits/             Charts and tables from the last run
```

Assumptions you may want to change (project size, growth, tax, equity risk premium) are named in `src/config.py`.

## Verify the dashboard

The offline checks cover all pages, scenario presets and reset, input persistence,
forward-path comparisons, FX direction, option sensitivity, glossary search, and
preservation of the saved outputs:

```bash
python -m unittest discover -s tests -v
```

## Scope

Illustrative capital-budgeting case on public tickers. Not investment advice, and not a production pricing system.
