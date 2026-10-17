# Portfolio allocation and the ML experiment

## What is a portfolio weight and what is this portfolio investing in?

A portfolio is a collection of investments. A 20% weight puts one fifth of its
value into an asset; weights sum to 100% for a fully invested book. The experiment
uses Infosys, HDFC Bank, Reliance, Hindustan Unilever and GoldBeES. GoldBeES is a
gold ETF, not a fifth operating company. These are historical allocation tests,
not an actual company investment account or a live trading service.
Mastercard is a separate global comparator and is not held in this five-asset book.

## What does mean-variance allocation use?

It uses estimated returns (means), how much each asset varies (variance), and how
assets move together (covariance). Diversification is about their combined risk,
not merely owning many names. Ledoit–Wolf shrinkage stabilises a noisy covariance
estimate; it cannot make expected returns reliable or guarantee diversification
in a crisis. The particular allocation algorithm differs by project version.
The original uses a clipped tangency-weight heuristic; the later review searches
a constrained 5-percentage-point weight grid. Do not call either a proof of the
globally optimal real-world portfolio.

## What do Ridge and gradient boosting predict?

They predict each asset's next-week return from earlier return patterns: own
return lags, Nifty returns, USDINR returns and rolling volatility. Ridge is linear
regression with a penalty that discourages large coefficients. Histogram gradient
boosting combines small decision trees for nonlinear patterns. Neither understands
company accounts or reads financial news here. The model does not set CAPM, WACC
or the FX hedge; the ML branch is a separate portfolio allocation experiment.

## What does walk-forward mean and why not use a random split?

Train on earlier observations, predict the next period, then move forward.
The setup starts after 104 eligible training weeks and refits every four weeks.
The features at information date t predict the return labelled t+1. Actual
trading would also need a feasible execution time after those inputs are known;
this weekly study does not prove a zero-delay executable strategy.

A random split can let later market conditions inform earlier predictions. In a
proper walk-forward pipeline even preprocessing learns only from training data.
The original Ridge did not scale its features; training-only StandardScaler was
added in the later review. Chronological forecasts do not eliminate retrospective
universe selection, strategy-selection bias or the need for an untouched holdout.

## How are forecasts turned into weights? Was Ridge allocated originally?

The gradient-boosting allocation blends 20% model forecast with 80% expanding
historical mean before allocation. This is a cautious forecast tilt, not an
80% cash holding or 20% portfolio allocation to a model. Historical allocation
instead uses trailing 52-week means. Both covariance and rebalance rules matter.

The original tests Ridge forecast error but has no separate Ridge allocation
track. The later review adds one and also an expanding-mean allocation baseline
sharing the ML lookback. It is not accurate to say both models independently
produced the original portfolio score.

## What do 0.30 Sharpe and 0.22 Nifty mean?

Sharpe = (annualised average return − annual risk-free rate) / annualised return
volatility. The code annualises weekly arithmetic mean with 52 and standard
deviation with sqrt(52), using sample standard deviation. Sharpe is dimensionless:
0.30 is not 30% return, 30% accuracy or a forecast. It describes excess return per
unit of variability in the tested sample.

For the original résumé version, historical allocation rounds to 0.30 and the
Nifty price reference to 0.22. That is a modest sample comparison, not proof of a
durable edge. Exact values, method and dates belong to the version-specific
result document. Do not attach those original scores to the later algorithm.

## Why is the Nifty comparison limited?

The price reference is Yahoo's ^NSEI, not Nifty TRI. Adjusted equity returns
include dividend adjustments, while a price index excludes dividends. Thus the
comparison is not a dividend-matched test of market outperformance. A future
matched study could use Nifty TRI or a dividend-adjusted investable ETF and
appropriate costs. This change has not been silently substituted in the record.

NSE explains that a total-return index includes both price movements and dividend
reinvestment: [NSE Indices — Total Return Index](https://www.niftyindices.com/resources/index-concepts/total-return-index).

## What are transaction costs, turnover, drawdown and forecast error?

Turnover measures how much holdings change; costs reduce returns when trading.
The study uses 10 basis points (0.10%) per unit of half-L1 one-way turnover.
Real costs also depend on spread, impact and instrument. Original active weights
stay fixed between rebalances, initial entry is not fully charged and equal
weight has free weekly rebalancing. Later code adds weight drift, initial entry
and a costed four-week equal-weight comparator. These differences affect results.

Maximum drawdown is the worst fall from an earlier portfolio-value peak. The
later review includes starting NAV in that check. RMSE measures average squared
prediction error on the return scale; sign hit rate counts correct directions.
Good RMSE need not give good net portfolio returns. Always compare with a simple
historical forecast and a matched allocation baseline, not just a complicated model.

## What can I honestly say about the ML conclusion?

The original historical allocation beats its GB challenger on sample Sharpe;
the original INFY GB forecast also has worse RMSE than its historical baseline.
This is useful negative evidence, not an ML success story that needs hiding.
The later Ridge allocation has only a small sample advantage over its matched
expanding-mean baseline. There is no untouched strategy-selection holdout or
statistical proof of a durable tradable advantage in either version.
