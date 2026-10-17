# Protecting dollar receipts

## What is USDINR and why does a dollar recipient face currency risk?

USDINR means rupees for one US dollar. At 90 INR/USD, receiving USD 1m gives
₹90m. At 85 it gives ₹85m. These are toy rates, not the project snapshot.
When USDINR falls, the rupee strengthens and a fixed dollar receipt buys fewer
rupees. When it rises, the dollar strengthens and the recipient benefits.
The operating business can perform as planned while currency conversion still
changes its rupee cash receipts.

## What does a currency hedge do? What does it not do?

A hedge changes how an identified exposure responds to exchange rates. It can
reduce uncertainty, but may cost money or give up upside. It does not create
customer sales, remove operating risk or guarantee that the expansion succeeds.
Hedge only the confirmed exposure: if receipts fail to arrive, a forward or a
sold call can leave obligations without the expected dollars to cover them.

## How does a forward work and where does its rate come from?

A forward agrees today on the rate for exchanging currencies on a future date.
For a fully covered fixed dollar receipt, the rupee amount is notional × forward
rate, before real-world costs and credit effects. Certainty means giving up both
unfavourable and favourable future spot movements.

The project's covered-interest-parity illustration uses spot, INR and USD rates,
tenor, a two-business-day spot lag and ACT/365 INR versus ACT/360 USD conventions.
The simple intuition is F ≈ S × (1 + INR interest)/(1 + USD interest).
The implementation uses the actual tenor/day-count conventions rather than that
rough one-year shorthand. A forward rate is a no-arbitrage pricing relationship,
not a forecast of where spot will actually end up. The versioned result record
contains its saved value.

## How does a put protect a dollar receipt?

A USD put gives the buyer the right to sell dollars at an agreed strike K.
Combined with a final-fixing dollar receipt, the gross effective rate is
max(final USDINR, K). The buyer pays a premium, so the net floor is lower.
The recipient keeps favourable dollar appreciation. A premium quoted INR/USD
must be multiplied by the USD notional to obtain a total rupee cost.

## What is a collar and why is it not free protection?

For this dollar recipient, buy a USD put at a lower strike and sell a USD call at
a higher strike. The call premium helps pay for the put. Gross proceeds per USD
are bounded between the two strikes: min(max(final rate, put strike), call strike).
Subtract the net premium on a consistent settlement-date basis for net proceeds.

The floor protects against a weaker dollar, but the sold call caps the benefit
of a stronger dollar. Even a zero-upfront-premium collar gives up upside and
creates a sold-option obligation. The recorded collar has a small positive model
premium, not exactly zero. It is not universally better than a forward or put.

## What does 25-delta mean? Is it a 25% hedge?

Delta is an option-price sensitivity. A 25-delta put has delta near −0.25 under
the chosen pricing convention; a 25-delta call has delta near +0.25. The code
solves for strikes with those model sensitivities. It does not mean that only
25% of the dollar notional is hedged, or that an option has a guaranteed 25%
probability of exercise. Hedge ratio is a separate choice about notional coverage.

## Why must average-rate protection match the receipt contract?

A final-fixing receipt converts at one end-date rate. An average-indexed receipt
converts using the arithmetic average of agreed fixings. These are different
exposures even if the final rate is identical. An average-rate put pays
max(K − average rate, 0); a terminal put pays max(K − final rate, 0).
Matching notional alone does not fix this basis risk.

The original version priced an Asian CALL as an option illustration, not a
matched average-rate downside hedge for dollar receipts. Only the later local
review adds a matched average-rate PUT comparison. In that later example all
receipts settle at year-end; it does not model twelve actual monthly collections.
Use the version-specific evidence before describing what was implemented.

## Is the displayed hedge dispersion a forecast of risk?

No. The original table takes 61 equally spaced exchange-rate outcomes from
15% below to 15% above the saved spot and calculates the standard deviation of
their proceeds. Those outcomes are scenarios, not probability-weighted forecasts.
Its dispersion reduction is not a VaR estimate, an observed realised saving or
an assertion that currency risk has fallen by that amount in the real world.
It excludes dealer spreads, counterparty default, collateral, basis and hedge
accounting. Model volatility is historical, not a dealer-implied FX quote.

## Does hedging automatically increase NPV or reduce WACC?

No. In this project the flat-spot and forward-path DCF use the same WACC.
Only the assumed future FX conversion path changes; today’s investment remains
at today's spot. A higher forward-path NPV here is scenario arithmetic, not free
value creation or a proof that the business risk disappeared. A rigorous
cross-currency valuation needs consistent cash-flow, discount-rate and risk
assumptions; this is a labelled teaching approximation.
