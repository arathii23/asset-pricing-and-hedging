# Later local reviewed extension [review_v2]

Generated from frozen, explicitly captured sources. Do not edit numerical values here.

## Dates, scope and provenance

Market snapshot: 2026-09-22. Evaluation labels: 2021-03-05 to 2026-09-18.
Only completed weeks; separate later method and results.
Separate local extension reviewed 17 October 2026; not evidence that these changes existed in 2025, at submission, or on the live website.

## CAPM, WACC and equity valuation numbers

CAPM = 6.50% + 0.810505996 × 5.50% = 10.95778298% required equity return.
Equity weight 99.97806144%; debt weight 0.02193856%. Borrowing yield 7.80%; tax assumption 25%.
WACC = equity_weight × equity_return + debt_weight × borrowing_yield × (1 − tax) = 10.95666240%, approximately but not exactly the equity return.
Market-plus-FX required equity return 10.26686961%; its WACC cross-check 10.26590062%.
Saved trailing DPS ₹48.00; assumed dividend growth 5%; next dividend ₹50.40. Gordon value ₹845.95 per share versus saved price ₹1051.40. Fixed-next-dividend implied growth 6.1642%.
India's 6.50% is a labelled rate fallback and 5.50% ERP an assumption. Frozen capital mix/DPS are inherited derived inputs, not newly verified raw filings. The Gordon comparison is not proof of mispricing.

## Expansion NPV calculation and the 8.37 billion rupee total

Illustrative spending today: USD 80m. FCF in years 1/2/3: USD 32m/36m/40m. Spot is 95.805000305 INR/USD. All future cash uses that same spot for this scenario. Zero salvage after year three.

| Year | USD FCF (million) | INR FCF (crore) | Divide by (1 + WACC)^year | Present value (crore) |
|---|---:|---:|---:|---:|
| 1 | 32 | 306.576001 | 1.109566624 | 276.302472 |
| 2 | 36 | 344.898001 | 1.231138093 | 280.145666 |
| 3 | 40 | 383.220001 | 1.366029738 | 280.535621 |

Present value of inflows = ₹8,369,837,592.86 = ₹836.983759 crore ≈ ₹8.37 billion. This is NOT ₹8.37 million.
Spending today = USD 80m × 95.805000305 = ₹766.440002 crore.
NPV = inflow PV − today's spending = ₹705,437,568.44 = ₹70.543757 crore, not the full inflow PV.
Forward-path NPV = ₹92.613951 crore at the same WACC. Flat-spot IRR 15.9753%; a uniform FCF reduction of 8.4283% removes the base NPV margin.
Cash flows are assumptions, not Infosys management forecasts. Company WACC is a similar-risk teaching proxy. The later customer-collection/cost bridge was not present in the original version.

## Currency hedge and option numbers

Separate Treasury receipt USD 36m, not the expansion's USD 32m first-year FCF. One-year model forward 97.144101 INR/USD; historical FX volatility 4.8005%.
Put strike 94.476845, call strike 100.415790 INR/USD. Upfront put premium 0.71443178, net collar premium 0.03396069 INR/USD. Collar caps upside; a forward fixes the rate.
Equally spaced scenario proceeds standard deviation: unhedged ₹306.147573 million, collar ₹99.473562 million. This is scenario dispersion, not forecast volatility or VaR.
ATM Asian CALL 1.47597764 versus vanilla CALL 2.51575470 INR/USD: different payoffs, not equivalent protection. Monte Carlo uses 12 future fixings, 40,000 risk-neutral paths and seed 7.
Later matched average-rate PUT premium 0.33968319 INR/USD. Compare terminal collar and average put against the same receipt contract and same paths; all cash settles year-end, premiums financed to settlement. This does not model monthly cash collections.
Archived INFY ADR USD call: strike 11.00, expiry 20 November 2026, mid 0.60, implied vol 37.043063%, BS 0.60000000, 50-step CRR 0.60287064 USD/ADR.
ADR delta 0.50700081, gamma 0.24753093 per USD, vega 1.73520189 per unit volatility, theta -2.23071493 USD/year. BS is calibrated to the same mid; raw spot/bid/ask snapshot is missing, not independent market validation.

## Allocation method and what existed in this version

The later local method searches fully invested, long-only weights in
5-percentage-point steps with a 35% target cap at rebalances. It is the best
estimated-Sharpe point on that grid, not a continuous optimum. Weights drift
between trades. Initial entry and four-week equal-weight rebalancing are costed;
starting NAV is included in drawdown. Ridge is scaled using past training data
only, has its own blended allocation, and is compared with an expanding-mean
allocation using the same history window. Completed weeks exclude the original
partial-week endpoint. These changes materially alter results; the grid was not
chosen to reproduce the submitted score. There is still no untouched
strategy-selection holdout or dividend-inclusive Nifty benchmark.

## Recorded portfolio Sharpe results and interpretation

| Allocation/reference | Annualised sample Sharpe |
|---|---:|
| Trailing historical allocation | -0.140859189 |
| Expanding-mean matched baseline | 0.286435780 |
| Ridge allocation | 0.292951386 |
| Gradient-boosting allocation | 0.257480233 |
| Inverse-volatility allocation | 0.100298483 |
| Equal weighting | 0.061047988 |
| Nifty PRICE index reference | 0.219984265 |

Ridge's sample advantage over the expanding-mean matched baseline is small; it is not proof of a statistically reliable or durable ML edge. The negative trailing-historical result belongs to this changed implementation, not the original method.
INFY forecast RMSE: GB 0.037540080, Ridge 0.035736785, historical mean 0.034980939; GB sign hit 49.3103%.
Nifty is a price-only index while adjusted equities include dividend adjustments: no dividend-matched market-outperformance claim. Universe/rules are retrospectively selected. A modest sample Sharpe is not investment advice.

## How can these numbers be traced?

Typed values and units: facts/review_v2.json. Raw saved summary/metrics/config/code: sources/review_v2/. File hashes and origins: sources/provenance.json. Source labels support traceability, not independent audit certification.
