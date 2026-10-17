# Present value, project value and units

## Why is future money discounted?

Money available now can be used now, while a future receipt involves waiting and
risk. Discounting translates a future payment into an equivalent value today
under a chosen required return. In a toy example, at 10% per year, ₹110 arriving
in one year has a present value of ₹110 / 1.10 = ₹100. A year-two receipt is divided
by 1.10 twice. This toy 10% rate is not the project's recorded WACC.

## What is DCF and how does NPV differ?

Discounted cash flow (DCF) is the method of valuing assumed future cash today.
Net present value (NPV) adds the discounted future inflows and subtracts the
investment paid today. With an outflow at time zero, NPV = cash_0 + cash_1/(1+r)
+ cash_2/(1+r)^2 + cash_3/(1+r)^3. A positive result clears the chosen hurdle under
the assumptions; it is not a realised profit, a bank balance or a guaranteed return.

## Why does the WACC percentage appear in the cash-flow calculation?

There are two different questions: how much cash might arrive, and what return is
required to justify waiting and taking risk? The cash-flow assumptions answer the
first; WACC supplies the required-return proxy for the second. WACC is the `r` in
the discounting formula. It is not an extra annual cash receipt and is not added
to the cash flows. In this teaching case, the company rate is used as a proxy for
a project assumed to have similar risk; a real expansion may need a different rate.

## What does IRR mean? Is it the same as WACC?

The internal rate of return (IRR) is the discount rate that would make a cash-flow
stream's NPV zero. For this case's single initial outflow followed by positive
inflows, it can be compared with WACC. IRR is calculated from the assumed cash;
WACC is the externally chosen hurdle proxy. An IRR above WACC is consistent with
positive NPV here. IRR is not a promised stock return, and unusual cash-flow sign
patterns can make IRR ambiguous or unsuitable.

## What is sensitivity analysis and a break-even cash-flow haircut?

Sensitivity analysis changes an assumption and observes how the result changes.
A cash-flow haircut reduces each future payment by the same fraction. The
break-even haircut is the reduction that brings NPV to zero. It is a cushion under
the stated assumptions, not a probability of loss. FX shocks on future receipts
should not change a cost already paid today; an original batch tornado changed
both, which is a documented limitation distinct from the later future-only test.

## How do crore, million and billion relate?

₹1 crore = ₹10 million. ₹1 billion = ₹100 crore. ₹1 million = ₹0.1 crore.
USD million and INR million are different currencies: multiply a dollar amount
by rupees per dollar before expressing it in rupees. A rate per USD, a per-share
price and a total project value must not be mixed.

For the original project's full rupee calculation, use its versioned cash-flow
table. Its approximately ₹8.37 **billion** present value is approximately ₹837
crore, not ₹8.37 million. The original NPV is the smaller amount after subtracting
the upfront investment—not the entire present value of future inflows.

## Is there a terminal value or salvage payment after year three?

The recorded teaching expansion ends after three years with zero salvage. It does
not include a continuing business terminal value. Gordon equity valuation, which
assumes dividends continuing forever, is a separate calculation. Never add that
share value to this project's final cash flow or describe the expansion as a full
company enterprise-value DCF.
