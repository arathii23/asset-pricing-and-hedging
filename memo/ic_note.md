# FX-Hedged Expansion Desk — IC note

**As of:** 2026-09-22 (prices); pull 2026-09-22 00:26 UTC
**Client:** Infosys (`INFY.NS`) · **Comparator:** Mastercard (`MA`)
**Question:** Fund a 3-year USD 80m expansion, and how should Treasury hedge year-1 USD receipts?

## Recommendation

On the labelled cash flows, the project clears a 10.96% CAPM WACC (NPV 0.71bn INR unhedged, 0.93bn on the forward path). The project ends after year 3 with zero salvage. Unhedged NPV reaches zero if every free cash flow is 8% lower. Those cash flows are a teaching case, not an Infosys forecast. Hedge year-1 receipts with a 25Δ collar, not a 100% forward, so a weaker rupee can still help. Both NPVs use the same WACC; the hedge changes the FX path only.

- **Cost of equity (CAPM, vs Nifty):** 10.96% (β = 0.81, α_ann = 1.92%, R² = 0.23).
- **Cost of equity (market + USDINR):** 10.27%. The FX factor cuts required return vs plain CAPM by 0.69%.
- **WACC (CAPM ke, comparable-bond kd):** 10.96% with equity weight 100.0% (market cap / (market cap + total debt)). Reported debt is negligible, so WACC equals the cost of equity. The bond shows YTM and duration; it does not change this NPV.
- **Gordon vs screen:** model 845.9 vs market 1051.4 (+24.3% to model) at labelled g = 5.00%. Implied perpetual g = 6.16%; retention×ROE g = 11.33% (above ke — fundamentals Gordon not defined).
- **USD project NPV (INR, CAPM WACC):** unhedged +0.71bn · forward-hedged +0.93bn. IRR unhedged 15.98%. Salvage at year 3 is zero. Unhedged NPV reaches zero if every free cash flow is 8% lower. Hedged and unhedged cases use this same WACC; only the FX path changes.
- **Treasury:** 1y USDINR IRP forward 97.14 vs spot 95.81. Collar residual vol 99.36 vs unhedged 306.15 (INR m). Asian 1.00y call on the average rate costs 1.475 vs vanilla 2.514 INR per USD.
- **ML challenger (walk-forward):** GB vs hist-mean RMSE on INFY 0.0375 vs 0.0349. Long-only MV with boosted μ Sharpe 0.25 vs historical-μ MV 0.30 vs Nifty 0.22. Selected book vs Nifty: β 0.69, Jensen α 1.72%, TE 9.5%, IR 0.09.

## 1. Universe and two-fund picture

Coverage book for the frontier: Infosys (IT), HDFC Bank, Reliance, Hindustan Unilever, and a gold ETF. Nifty, Mastercard, USDINR, India/US 10Y, and a listed call on `INFY` are the other inputs. Shorts are allowed on the frontier so the two-fund line is visible. The held book is long-only.

Tangency weights for that diversified book are in `exhibits/weights.csv`.

## 2. CAPM, factors, WACC

| | INFY vs Nifty | MA vs S&P |
|---|---:|---:|
| Beta | 0.81 | 1.05 |
| Jensen α (ann.) | 1.92% | 1.39% |
| R² | 0.23 | 0.53 |
| ke | 10.96% | 10.22% |
| Rf | 6.50% | 4.96% |
| Sample ERP | 4.86% | 11.16% |
| Labelled ERP (in ke) | 5.50% | 5.00% |

Factor ke uses historical premia on Nifty excess and USDINR. Exporting IT / payments names load on USDINR; that is the Mastercard Treasury analogue (cross-border receipts) and why CAPM-only WACC can mis-rank the project.

Cost of debt is **YTM, not coupon**, on a labelled 7-year 7.20% coupon priced at 7.80% YTM (mod duration 5.38, convexity 35.84). Tax shield at 25%. Reported debt is negligible, so WACC equals the cost of equity. The bond shows YTM and duration; it does not change this NPV.

## 3. Asset valuation

Gordon uses trailing DPS grown at labelled g = 5% and CAPM ke. That g is a cap, not a forecast: retention×ROE is above ke, so a fundamentals Gordon price is not defined. Implied perpetual g is 6.16%; retention×ROE g = 11.33% (above ke — fundamentals Gordon not defined). The market premium to this model is a growth assumption, not a trading signal.

## 4. Walk-forward ML challenger (easy–medium)

Ridge and histogram gradient boosting are compared with the expanding historical mean using an expanding window, **no look-ahead**, and refitting every 4 weeks after 104 weeks of history.

Ridge and gradient boosting forecast next-week returns from own lags, Nifty, USDINR (the factor already in ke), and rolling vol. Blended μ = 80% expanding mean + 20% GB feeds **long-only mean-variance**. The covariance is Ledoit–Wolf shrinkage; the book rebalances every 4 weeks, charges 10 bps per unit of one-way turnover, and caps each name at 35%. **Strategy used:** monthly, long-only shrinkage mean-variance using trailing historical returns, with a 35% position cap. OOS excess-return Sharpe: ML-MV 0.25 · hist-MV 0.30 · inverse-vol 0.09 · 1/N 0.05 · Nifty 0.22. Selected book vs Nifty: β 0.69, Jensen α 1.72%, tracking error 9.5%, information ratio 0.09. Max drawdown -14.2%, annual turnover 2.17×. Average weights (full OOS path, not the last week): INFY 21% · HDFCBANK 24% · RELIANCE 18% · HINDUNILVR 12% · GOLDBEES 25%. INFY RMSE GB 0.0375 / Ridge 0.0349 / hist 0.0349; sign hit GB 49.1%. ML-MV beat Nifty, but did not beat the simpler historical-MV rule; GB also failed to improve INFY forecast error (sign hit near 50%). The historical-MV rule is therefore selected, while ML stays as a documented challenger and robustness test.

No LSTM: weekly 2019–now is too short for a sequence model to beat lagged Ridge, and it is not in the ECO423 outline.

## 5. Forwards, listed options, Greeks

FX forward uses **T+2 spot lag**, USD act360, INR act365 — the same convention stack as an FS-risk pricing sheet, implemented here from scratch.

Listed `call` `INFY` (ADR, not the INR line) 11.00 exp 2026-11-20: mid 0.600, implied vol 37.0%. Black–Scholes at that implied vol is 0.600 by construction; the check is CRR(50) 0.603 against that closed form. Δ 0.507 (binomial bump 0.495), Γ 0.2475, ν 1.735, Θ -2.231.

## 6. Hedge policy

Year-1 notional USD 36m.

| Policy | What it does |
|---|---|
| Unhedged | Full USDINR risk on INR proceeds |
| Sell USD 1y forward | Locks 97.14; zero premium; zero upside |
| 25Δ USD put | Floor; premium 0.714 INR/USD |
| Collar (25Δ / 25Δ) | Band; net premium 0.034 INR/USD; scenario dispersion 99.4 vs unhedged 306.1 INR m |
| Asian (avg-rate) call | Unconventional; cheaper than vanilla for the same strike (1.475 vs 2.514) because averaging kills vol |

**Policy call:** Prefer the 25Δ collar over 100% forwards: residual vol drops versus unhedged while keeping participation if USDINR rises (exporter-friendly). Use the Asian only if the desk will actually average monthly fixings; otherwise the vanilla put leg is cleaner.

## 7. Risks (three)

1. **ERP and β window.** Sample Nifty excess is 4.86%; ke uses labelled ERP 5.50%. β is OLS on weekly data since 2019-01-01.
2. **Project ends, and the hedge does not change the hurdle.** Salvage is 0. USD cash flows are converted and then discounted at one INR WACC, hedged or not. A USD WACC (MA analogue 9.97%) would change the NPV level. It would not by itself rank the hedge.
3. **Vol and listed vs OTC.** Equity IV is from one Yahoo snapshot. USDINR vol is realised, not implied. No holiday calendar beyond weekends.

## Notes

India 10Y FRED pull failed; using labelled fallback 6.50%.

All engines (OLS, CRR, BS, IRP, YTM, MC Asian, walk-forward Ridge/GB) live under `src/` and were identity-checked in `src/checks.py`.
