# Options, pricing models and sensitivities

## What are a call, put, strike, premium and expiry?

A call gives its buyer the right to buy an underlying at an agreed strike. A put
gives the right to sell. The premium is paid for that right, and expiry limits
when the contract can be exercised. The seller takes the matching obligation.
Buying a put is therefore not the same as shorting a call: their obligations and
upside differ. Exercise style, currency, notional and settlement terms matter.

## What does the binomial or CRR model calculate?

The Cox–Ross–Rubinstein tree lets the underlying move up or down in each small
time step. Start with each final option payoff, then work backwards by taking a
risk-neutral weighted payoff and discounting it. Risk-neutral probabilities are
pricing weights, not estimated real-world frequencies. A valid tree requires
probabilities between zero and one. More steps usually improve approximation
but finite-step prices can oscillate. The later review raises on invalid tree
probabilities; the original routine clipped them, which is a limitation.

## What is Black–Scholes and how does the FX version differ?

Black–Scholes prices a European option under assumptions such as lognormal
underlying dynamics, constant volatility and rates, and idealised trading.
Dividend yield adjusts an equity implementation. For FX, the foreign interest
rate plays the corresponding yield role: INR is domestic and USD foreign when
the underlying is quoted INR per USD. This is the Garman–Kohlhagen adjustment.
The models are approximations, not a promise of a dealer's executable price.

## What are delta, gamma, vega and theta?

Delta estimates the price change for a small underlying-price increase. Gamma
describes how delta changes. Vega describes sensitivity to volatility; theta
describes sensitivity to the passage of time with other inputs held fixed.
They are local model sensitivities, not guaranteed profits or exact large-move
predictions. The archived ADR vega is per unit volatility (a 1.00 absolute change),
not per one percentage point: multiply it by 0.01 for that convention. Its theta
is per year, not per day. Delta hedge quantities also depend on contract size.

## Did matching the option mid independently validate Black–Scholes?

No. In the original ADR example the code solved for implied volatility from the
same saved mid-price, then plugged that volatility back into Black–Scholes.
Matching that mid is calibration by construction. Comparing the CRR tree using
the same inputs checks numerical agreement between models; it is not independent
market validation. The saved contract is a USD-denominated INFY ADR call, separate
from the INR-listed share and from the FX hedging options.

The original raw bid/ask and simultaneous underlying spot are not frozen with
the record. A listed ADR option may also have exercise-style features that a
European model does not capture. Do not claim dealer accuracy or a fully
reconstructable market quote from this archive.

## What is an Asian arithmetic-average option and Monte Carlo pricing?

An Asian payoff uses an average over specified observation dates. The code
simulates 40,000 risk-neutral exchange-rate paths with 12 future monthly fixings
and seed 7, computes each payoff, averages the payoffs and discounts to today.
Fixing dates exclude an initial spot fixing in this setup. A fixed seed supports
reproducibility, not accuracy certification. Sampling error and model assumptions
remain. These are pricing paths, not actual forecasts of the exchange rate.

The original illustration compared an at-the-money Asian CALL with a vanilla
CALL; their different payoffs mean a lower price is not proof of an equally
effective cheaper hedge. A dollar recipient needs downside protection, for which
the later matched example uses a PUT. Do not describe that later feature as part
of the original calculation.

## What does a useful numerical check establish?

Tree convergence, put-call parity and finite-difference checks of formula Greeks
can catch implementation errors under the same assumptions. The later review
contains such formula/numerical comparisons. Passing checks does not validate
future prices, market liquidity, exercise-style suitability or the truth of the
input assumptions. Keep calibration, numerical verification and real-world
validation separate.
