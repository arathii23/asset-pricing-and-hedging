"""Named assumptions. Nothing silent: every WACC/NPV input is labelled."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
EXHIBIT_DIR = ROOT / "exhibits"
MEMO_DIR = ROOT / "memo"

# --- Coverage universe -------------------------------------------------------
CLIENT = "INFY.NS"  # INR listing vs Nifty (cost of equity for an India WACC)
CLIENT_NAME = "Infosys"
# Frontier and ML book: one name per risk, not four IT stocks.
BOOK = ("INFY.NS", "HDFCBANK.NS", "RELIANCE.NS", "HINDUNILVR.NS", "GOLDBEES.NS")
COMPARATOR = "MA"  # Mastercard — global payments / Treasury comparator
COMPARATOR_NAME = "Mastercard"
MARKET_IN = "^NSEI"
MARKET_US = "^GSPC"
FX = "USDINR=X"  # INR per USD
US_10Y = "^TNX"  # percent yield
OPTION_UNDERLYING = "INFY"  # NYSE ADR; liquid listed options for BS vs market

START = "2019-01-01"
RF_FALLBACK_IN = 0.065  # India 10Y if the live series is missing
RF_FALLBACK_US = 0.042
ERP_OVERRIDE = None  # if set, replaces the labelled ERP below for ke
ERP_LABELLED_IN = 0.055  # used in WACC; sample ERP is still reported
ERP_LABELLED_US = 0.050
TAX_RATE = 0.25  # Indian corporate tax, labelled
TARGET_D_TO_V = None  # None = use latest reported book/market mix

# Stylised USD expansion (capital budgeting). Figures are illustrative.
# The project ends after the horizon: salvage is zero, so there is no terminal value.
PROJECT_CAPEX_USD = 80_000_000.0
PROJECT_FCF_USD = (32_000_000.0, 36_000_000.0, 40_000_000.0)
PROJECT_HORIZON_YEARS = 3
PROJECT_SALVAGE_USD = 0.0
USD_RECEIPT_NOTIONAL = 36_000_000.0  # annual USD to hedge (year-1 FCF proxy)

# Valuation
GORDON_G = 0.05  # perpetual dividend growth, below ke. 8% made the stock look falsely cheap.
BOND_FACE = 100.0
BOND_COUPON = 0.072
BOND_YTM = 0.078
BOND_YEARS = 7
BOND_FREQ = 2

# Options / hedge
HEDGE_HORIZON_YEARS = 1.0
COLLAR_PUT_DELTA = 0.25
COLLAR_CALL_DELTA = 0.25
ASIAN_STEPS = 12  # monthly averaging over the hedge year
ASIAN_PATHS = 40_000
BINOMIAL_STEPS_REPORT = 50
BINOMIAL_STEPS_CONVERGE = (5, 10, 20, 50, 100, 200)

# FX conventions (Grant Thornton overlay — implemented here, not imported)
USD_DAYCOUNT = "act360"
INR_DAYCOUNT = "act365"
SPOT_LAG_BUSINESS_DAYS = 2

# Walk-forward ML overlay (easy–medium). Finance stays the IC; ML replaces
# historical μ in mean-variance and sizes the FX hedge. No LSTM.
ML_MIN_TRAIN = 104  # weeks (~2y) before the first OOS prediction
ML_REFIT_EVERY = 4  # re-estimate monthly on weekly data
ML_COV_LOOKBACK = 52
ML_BLEND = 0.2  # conservative tilt: 20% model μ + 80% expanding mean
MAX_WEIGHT = 0.35  # no single name above 35% in the held book
REBALANCE_WEEKS = 4  # monthly rebalance on weekly data
TRANSACTION_COST_BPS = 10  # one-way cost per unit of turnover


@dataclass(frozen=True)
class Universe:
    client: str = CLIENT
    comparator: str = COMPARATOR
    market_in: str = MARKET_IN
    market_us: str = MARKET_US
    fx: str = FX
    us_10y: str = US_10Y
    option_underlying: str = OPTION_UNDERLYING

    @property
    def equity_tickers(self) -> tuple[str, ...]:
        return (self.client, self.comparator)

    @property
    def book(self) -> tuple[str, ...]:
        return BOOK

    @property
    def all_tickers(self) -> tuple[str, ...]:
        seen: list[str] = []
        for t in (*self.book, *self.equity_tickers, self.market_in, self.market_us, self.fx, self.us_10y):
            if t not in seen:
                seen.append(t)
        return tuple(seen)
