# Original submitted-resume experiment [resume_v1]

Generated from frozen, explicitly captured sources. Do not edit numerical values here.

## Dates, scope and provenance

Market snapshot: 2026-09-22. Evaluation labels: 2021-03-05 to 2026-09-25.
Final label is a partial week; actual daily observations stop 22 September. Dates follow original resampling/next-period allocation, not a 25 September observation.
Original source revision: 395858d928c65da39b17c92d9f3b135a46471082. This is the submitted-resume context, not a guarantee of realistic execution.

## CAPM, WACC and equity valuation numbers

CAPM = 6.50% + 0.810512530 × 5.50% = 10.95781892% required equity return.
Equity weight 99.97806144%; debt weight 0.02193856%. Borrowing yield 7.80%; tax assumption 25%.
WACC = equity_weight × equity_return + debt_weight × borrowing_yield × (1 − tax) = 10.95669834%, approximately but not exactly the equity return.
Market-plus-FX required equity return 10.26852110%; its WACC cross-check 10.26755174%.
Saved trailing DPS ₹48.00; assumed dividend growth 5%; next dividend ₹50.40. Gordon value ₹845.95 per share versus saved price ₹1051.40. Fixed-next-dividend implied growth 6.1642%.
India's 6.50% is a labelled rate fallback and 5.50% ERP an assumption. Frozen capital mix/DPS are inherited derived inputs, not newly verified raw filings. The Gordon comparison is not proof of mispricing.

## Expansion NPV calculation and the 8.37 billion rupee total

Illustrative spending today: USD 80m. FCF in years 1/2/3: USD 32m/36m/40m. Spot is 95.805000305 INR/USD. All future cash uses that same spot for this scenario. Zero salvage after year three.

| Year | USD FCF (million) | INR FCF (crore) | Divide by (1 + WACC)^year | Present value (crore) |
|---|---:|---:|---:|---:|
| 1 | 32 | 306.576001 | 1.109566983 | 276.302382 |
| 2 | 36 | 344.898001 | 1.231138891 | 280.145485 |
| 3 | 40 | 383.220001 | 1.366031065 | 280.535349 |

Present value of inflows = ₹8,369,832,158.11 = ₹836.983216 crore ≈ ₹8.37 billion. This is NOT ₹8.37 million.
Spending today = USD 80m × 95.805000305 = ₹766.440002 crore.
NPV = inflow PV − today's spending = ₹705,432,133.70 = ₹70.543213 crore, not the full inflow PV.
Forward-path NPV = ₹92.613391 crore at the same WACC. Flat-spot IRR 15.9753%; a uniform FCF reduction of 8.4283% removes the base NPV margin.
Cash flows are assumptions, not Infosys management forecasts. Company WACC is a similar-risk teaching proxy. The later customer-collection/cost bridge was not present in the original version.

## Currency hedge and option numbers

Separate Treasury receipt USD 36m, not the expansion's USD 32m first-year FCF. One-year model forward 97.144101 INR/USD; historical FX volatility 4.7946%.
Put strike 94.480121, call strike 100.411739 INR/USD. Upfront put premium 0.71353093, net collar premium 0.03387713 INR/USD. Collar caps upside; a forward fixes the rate.
Equally spaced scenario proceeds standard deviation: unhedged ₹306.147573 million, collar ₹99.360055 million. This is scenario dispersion, not forecast volatility or VaR.
ATM Asian CALL 1.47472527 versus vanilla CALL 2.51373007 INR/USD: different payoffs, not equivalent protection. Monte Carlo uses 12 future fixings, 40,000 risk-neutral paths and seed 7.
Original Asian illustration is a CALL, not a matched average-rate receipt hedge. Original payoff tables subtract upfront premiums without financing them to the receipt date.
Archived INFY ADR USD call: strike 11.00, expiry 20 November 2026, mid 0.60, implied vol 37.043063%, BS 0.60000000, 50-step CRR 0.60287064 USD/ADR.
ADR delta 0.50700081, gamma 0.24753093 per USD, vega 1.73520189 per unit volatility, theta -2.23071493 USD/year. BS is calibrated to the same mid; raw spot/bid/ask snapshot is missing, not independent market validation.

## Allocation method and what existed in this version

The original mean-variance allocation is an unconstrained tangency solution
normalised, negative weights clipped and weights capped at 35%. This is a
heuristic, not a solved constrained optimum. Active weights remain fixed between
four-week rebalances rather than drifting. Initial positions are assumed already
equal-weighted; active trading costs are 10bp per half-L1 turnover. The equal-weight
reference resets weights weekly without costs. Historical means use 52 weeks;
GB blends 80% expanding mean and 20% forecast. Ridge is tested for forecasts only,
without scaling, and has no separate allocation track. Shrinkage covariance is
Ledoit–Wolf. Models start after 104 eligible weeks and refit every four weeks.
These rules, the fixed asset universe and strategy selection are retrospective;
there is no untouched strategy-selection holdout.

## Recorded portfolio Sharpe results and interpretation

| Allocation/reference | Annualised sample Sharpe |
|---|---:|
| Trailing historical allocation | 0.295923458 |
| Gradient-boosting allocation | 0.250901504 |
| Inverse-volatility allocation | 0.091314600 |
| Equal weighting | 0.053586929 |
| Nifty PRICE index reference | 0.217875105 |

Original historical Sharpe = (0.101740622 − 0.065) / 0.124155828 = 0.295923458, rounded 0.30. Nifty 0.217875105 rounds 0.22. These are ratios, not 30% and 22% returns.
The historical rule leads the tested GB rule in this original sample. That does not show a durable trading edge or validate the later corrected implementation.
INFY forecast RMSE: GB 0.037478273, Ridge 0.034926013, historical mean 0.034921002; GB sign hit 49.1409%.
Nifty is a price-only index while adjusted equities include dividend adjustments: no dividend-matched market-outperformance claim. Universe/rules are retrospectively selected. A modest sample Sharpe is not investment advice.

## How can these numbers be traced?

Typed values and units: facts/resume_v1.json. Raw saved summary/metrics/config/code: sources/resume_v1/. File hashes and origins: sources/provenance.json. Source labels support traceability, not independent audit certification.
