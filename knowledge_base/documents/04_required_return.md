# Risk, required return, WACC and share valuation

## What does expected return mean and where does it come from?

“Return” can mean different things. A historical return is measured from past
prices. A forecast is an estimate of a later return. A required return is the
compensation investors demand for waiting and taking risk. In the project's CAPM
calculation, the model-implied required equity return is used as a hurdle input;
it is not a guarantee that shareholders or the expansion will earn that amount.
The portfolio's historical/ML expected-return estimates are different inputs.

## What are market risk and beta? Why use the stock here?

Market risk comes from broad events that can affect many investments together,
such as economy-wide shocks. Beta estimates how a stock's returns co-move with a
market benchmark. It does not measure every business risk or guarantee an exact
move next week. Infosys stock versus Nifty provides a reference estimate for the
return equity investors require; it does not mean investors buy stock to provide
each future project cash flow. The expansion rate relies on a similar-risk proxy
assumption, not an independently estimated project beta.

## How does CAPM combine the risk-free rate and equity risk premium?

CAPM required equity return = risk-free rate + beta × equity risk premium.
The risk-free rate is a starting government-bond proxy; the premium is assumed
extra compensation for stock-market risk. They are not two versions of the same
rate. The original project uses a labelled 6.50% India fallback and a 5.50% assumed
equity risk premium. Its estimated beta is about 0.81, producing about 10.96%.
The exact figures are in the original-version facts. The fallback is not today's
live government-bond yield and the premium is not estimated by subtracting 5.50
from 6.50. A short-sample market premium is reported separately.

## What is WACC and why is it close to the equity return?

Weighted average cost of capital combines the equity required return with the
after-tax borrowing cost: WACC = equity_weight × cost_of_equity + debt_weight ×
cost_of_debt × (1 − tax). The original saved market-value equity weight is almost
100%, so debt has very little influence. WACC is approximately, not exactly, the
cost of equity. The weights do not say what the company has in its bank account.
The project uses a frozen capital-mix input, not a new expansion loan or a target
financing plan reconstructed from company filings.

## Why use bond yield instead of coupon as the cost of debt?

A coupon is the contracted interest payment relative to face value. Yield to
maturity depends on the price paid and the bond's future payments; it is a better
illustration of the borrowing return required at that price. The project's bond
is a labelled comparable-method example, not a verified Infosys expansion bond.
Duration approximates small price sensitivity to yield changes; convexity adds
curvature. The tax rate is a modelling assumption, not personalised tax advice.

## What does the market-plus-FX factor model add?

The cross-check regresses Infosys excess returns on market excess returns and
USDINR returns. The market premium is overridden with the labelled assumption;
the FX contribution uses a historical premium. It is an alternative required-
return estimate, not a causal explanation of every stock move or a proven rule
that adding FX always improves WACC. The base expansion uses CAPM-based WACC.
Mastercard versus the S&P 500 is a separate US comparison, not an Indian holding.

## What does Gordon dividend valuation estimate?

The Gordon model values a share from assumed dividends growing forever:
share_value = next_dividend / (required_equity_return − perpetual_growth).
Growth must be below the required return. The original illustration grows its
saved trailing dividend by an assumed 5%; this is not verified future guidance.
The resulting value is not a cash dividend or the value of the expansion. A
market price above the model can reflect different growth, payout or risk
expectations; it does not prove the stock is overpriced.

## What does the reported implied growth mean?

The implementation holds the already-computed next dividend fixed, then calculates
required_return − next_dividend/market_price. That is the reported implied-growth
cross-check. It does not jointly re-estimate next dividend as growth changes, so
do not confuse it with solving price = trailing_dividend × (1+g)/(required_return−g)
for g. The exact recorded estimate belongs to the selected version and assumptions.
