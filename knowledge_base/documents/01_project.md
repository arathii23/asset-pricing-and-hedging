# The project and the website

## What is this project about?

Asset Pricing and Hedging is an educational finance project with three related
but separate questions. First, is an illustrative business expansion worth its
upfront cost? Second, how can a company protect dollar receipts from exchange-rate
changes? Third, do return forecasts from simple ML models improve a portfolio
allocation experiment? Python implements the calculations and Streamlit presents
the analysis interactively.

## How are the three parts connected—and not connected?

The expansion uses assumed future business cash and a required return. Currency
hedging changes the rupees received for dollars. The portfolio experiment compares
investment-allocation rules on a separate five-asset universe. The portfolio is
not the expansion's financing plan. Its weights do not determine WACC, and ML
does not set the company's hedge. A forward-path project NPV is not automatically
the NPV of the separately discussed collar strategy.

## Is this an actual Infosys expansion or investment recommendation?

No evidence in this project establishes an announced Infosys expansion or a real
investment mandate. Infosys is the public reference company for the Indian equity
risk/valuation exercise. Project cash flows are illustrative assumptions, not
management guidance, realised profits or customer sales forecasts. A positive
case NPV means the labelled assumptions clear the chosen hurdle, not that an
investor should buy Infosys or that management should actually spend the money.

## Who created it and what is the course connection?

The repository is maintained under the public account `arathii23`, and the project
is presented by Aaditya Rathi. The user-provided résumé credits Prof. Wasim Ahmed,
IIT Kanpur, ECO423 and gives a May–July 2025 period. These are attribution/context
records, not independent evidence of supervision, a grade, endorsement, or which
person wrote each component. The visible saved market snapshot is from 2026;
do not claim those figures existed in 2025 or invent the author's personal role.

## How do I use the website?

Start at Overview for the case and the main findings. Expansion & valuation
contains project cash flows, scenario inputs, cost of capital and Gordon share
valuation. Currency hedging compares protection of dollar receipts. Portfolio
analysis compares allocation rules and their risks. Option pricing lets visitors
change model inputs. Methods & data contains definitions, assumptions and
downloads. Changing a scenario is not the same as changing the recorded base case.

## What technology and data does it use?

The finance implementation uses Python, NumPy, pandas and scikit-learn, with
Streamlit for the interface and plotting tools for charts. Public Yahoo Finance
series are the recorded price inputs. The Indian government-bond rate failed to
load in the original pull, so a labelled fallback was used. The exact tickers,
sample dates, numerical results and implementation details must be taken from
the selected version rather than inferred from a general project description.

## What are the public project links?

Repository: https://github.com/arathii23/asset-pricing-and-hedging

Website: https://asset-pricing-and-hedging-desk.streamlit.app/

These identify the project, not a promise that a particular local extension is
already deployed. A chatbot should not claim it has opened or checked either link
unless the application has actually supplied a current verification result.
