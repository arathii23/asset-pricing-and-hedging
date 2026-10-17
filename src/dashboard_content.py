"""Plain-language reference material for the interactive project walkthrough."""

PAGES = ("Overview", "Expansion & valuation", "Currency hedging", "Portfolio analysis", "Option pricing", "Methods & data")

PAGE_FILES = ("overview", "expansion", "hedging", "portfolio", "options", "methods")

ASSET_NAMES = {
    "INFY.NS": "Infosys · IT services",
    "HDFCBANK.NS": "HDFC Bank · Banking",
    "RELIANCE.NS": "Reliance · Diversified business",
    "HINDUNILVR.NS": "Hindustan Unilever · Consumer goods",
    "GOLDBEES.NS": "Gold ETF · Gold",
}

STRATEGY_NAMES = {
    "hist_mv": "Historical allocation · selected",
    "gb_mv": "ML allocation · challenger",
    "nifty": "Nifty · market benchmark",
    "inv_vol": "Lower-volatility weighting",
    "equal": "Equal weighting",
}

GLOSSARY = {
    "Share & shareholder": "A share is a small unit of ownership in a company. A shareholder owns one or more of those units. Buying an existing share usually pays its previous owner, rather than sending fresh money to the company.",
    "Dividend": "Cash a company chooses to pay its shareholders. A dividend per share is the payment for each share owned. Payments can change and are not guaranteed.",
    "Free cash flow (FCF)": "Cash left after the operating and investment costs included in the case. It differs from customer sales, accounting profit, and dividends. The expansion's annual cash flows are assumptions, not an Infosys forecast.",
    "Present value & discounting": "A future payment is translated into an equivalent value today. Divide a year-one payment by (1 + required return); use the square for year two and the cube for year three.",
    "Net present value (NPV)": "The value today of future project cash flows, minus spending today. A positive result means the investment clears the chosen required return under the stated assumptions.",
    "Internal rate of return (IRR)": "The discount rate at which the project's NPV becomes zero. For this case, with one initial outflow followed by inflows, it can be compared with the required return.",
    "Risk-free rate": "A government-bond rate used as a starting benchmark for required returns. The India rate is a labelled 6.50% fallback because the live data pull failed.",
    "Market risk & beta": "Economy-wide events can affect many businesses together. Beta measures how sensitive a share's returns have been to market returns. Beta 0.81 is an estimated average sensitivity, not a promise about any particular week's movement.",
    "Equity risk premium (ERP)": "The extra annual return assumed for stock-market risk above the government-bond benchmark. The India assumption is 5.50%; it is separate from the 6.50% starting rate.",
    "CAPM & required return": "CAPM estimates the return shareholders require: risk-free rate + beta × equity risk premium. Here that is approximately 6.50% + 0.81 × 5.50% = 10.96%. It is a hurdle, not a guaranteed return.",
    "WACC & cost of capital": "Weighted average cost of capital combines shareholders' required return and the after-tax cost of borrowing. This uses company market-value equity and reported debt; it does not describe a new loan for the expansion. Debt is very small here, so WACC is almost the shareholders' required return.",
    "Gordon dividend valuation": "An estimate of one share's value from future dividends assumed to grow at a constant rate forever. Value = next dividend ÷ (shareholders' required return − growth). Growth must be below the required return.",
    "USDINR & spot rate": "Rupees paid for one US dollar today. If USDINR falls, each dollar received converts into fewer rupees: the rupee has strengthened.",
    "Forward & interest-rate parity": "An agreement to exchange currencies later at a rate fixed at the outset. The illustration estimates that rate from today's exchange rate and the two interest rates. It is not a forecast of the future spot rate.",
    "Put & call options": "A put gives its buyer the right to sell at a specified rate; a call gives its buyer the right to buy. For USD receipts, a USD put can create a floor on rupee proceeds. The price paid for the option is its premium.",
    "Collar": "For the dollar recipient here, buy a USD put and sell a USD call. The put creates a floor, while selling the call helps pay for it and caps the benefit of a stronger dollar.",
    "Strike, premium & delta": "Strike is an option's agreed exercise rate. Premium is its price. Delta estimates the option price's response to a small change in the underlying rate. A 25-delta put has delta approximately −0.25; it is not a 25% hedge ratio.",
    "Asian / average-rate option": "An option whose payoff depends on the average of several exchange-rate fixings. It suits exposures based on averaging dates. Its protection differs from an option on a single terminal fixing.",
    "Black–Scholes, CRR & Greeks": "Black–Scholes is a pricing formula; the Cox–Ross–Rubinstein (CRR) tree prices through a sequence of up/down steps. For FX, both currency interest rates are used. Greeks describe changes in price with inputs such as the exchange rate, volatility, and time.",
    "Portfolio & weights": "A portfolio is a collection of investments. A 20% weight means one fifth of the money goes to that investment. The five-asset portfolio is a separate experiment from the company's expansion.",
    "Mean-variance & shrinkage": "Allocation uses estimated average returns and how investments move together. Shrinkage stabilises the covariance estimate. This implementation removes negative tangency weights and caps the remaining weights; it approximates a fully constrained optimiser.",
    "Sharpe ratio": "Average return above the risk-free rate divided by return volatility. Higher indicates more excess return per unit of volatility on this sample. A Sharpe of 0.30 is modest; it is neither 30% return nor a forecast.",
    "Volatility & drawdown": "Volatility measures how much returns vary. Maximum drawdown is the largest peak-to-trough decline in recorded portfolio value. Both describe the historical sample.",
    "Walk-forward & out-of-sample": "Fit using earlier observations, predict a later return, and move forward through time. Out-of-sample returns were unavailable when the corresponding forecasts were made. Results can still be affected by model-selection choices.",
    "Ridge & gradient boosting": "Ridge is linear regression with a penalty limiting large coefficients. Gradient boosting combines small decision trees to learn nonlinear patterns. Both forecast next-week returns; the ML allocation uses a blend containing gradient boosting.",
    "Turnover & transaction cost": "Turnover measures trading needed to change holdings. The allocation rules charge 10 basis points (0.10%) per unit of one-way turnover. Benchmark series have simplified trading assumptions.",
    "Jensen alpha, tracking error & information ratio": "Jensen alpha compares return with a CAPM benchmark. Tracking error measures variability of returns relative to Nifty. Information ratio divides average return above Nifty by tracking error; Sharpe instead uses the risk-free rate.",
    "Crore, million & billion": "₹1 crore = ₹10 million = ₹0.01 billion. Rupee totals use crore; dollar totals use USD million. A price per share or per dollar is labelled separately.",
}

STYLES = """
<style>
.block-container { max-width: 1240px; padding-top: 2.5rem; padding-bottom: 3rem; }
[data-testid="stMain"] { overflow-anchor: none; }
[data-testid="stSidebar"] { background: #f3f5f7; border-right: 1px solid #e3e7ec; }
[data-testid="stMetricValue"] { font-size: clamp(1.35rem, 2vw, 1.8rem); font-variant-numeric: tabular-nums; font-weight: 550; }
[data-testid="stMetricLabel"] { white-space: normal; color: #536274; }
h1 { font-size: 2rem !important; font-weight: 600 !important; letter-spacing: -.025em; }
h2 { font-size: 1.4rem !important; font-weight: 600 !important; letter-spacing: -.015em; }
h3 { font-size: 1.15rem !important; font-weight: 600 !important; letter-spacing: -.01em; }
h4 { font-size: 1rem !important; font-weight: 600 !important; }
[data-testid="stButton"] button { border-radius: 4px; }
.eyebrow { color: #687788; font-weight: 500; font-size: .8rem; letter-spacing: .02em; margin: .35rem 0 .6rem; }
.intro { max-width: 850px; color: #536274; font-size: 1rem; line-height: 1.65; }
.case-note { border-left: 2px solid #8999ab; padding: .6rem .9rem; background: #f5f7f9; color: #536274; margin: 1rem 0; font-size: .88rem; line-height: 1.6; }
.app-footer { color: #738091; font-size: .78rem; margin-top: 1.2rem; border-top: 1px solid #e3e7ec; padding-top: .85rem; }
@media (max-width: 640px) {
  .block-container { padding-top: 1.2rem; padding-left: 1rem; padding-right: 1rem; }
  h1 { font-size: 1.6rem !important; }
  .intro { font-size: 1rem; }
  [data-testid="stMetricValue"] { font-size: 1.4rem; }
}
</style>
"""
