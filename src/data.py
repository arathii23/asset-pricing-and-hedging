"""Public-data pulls with a local parquet cache. No proprietary GT files."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
import ssl
import urllib.request

import numpy as np
import pandas as pd

from . import config as C
from .config import Universe

try:
    import yfinance as yf
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install dependencies: pip install -r requirements.txt") from exc


@dataclass
class Fundamentals:
    ticker: str
    price: float
    market_cap: float | None
    total_debt: float | None
    dps_ltm: float
    div_yield: float
    roe: float | None
    payout: float | None
    shares: float | None


@dataclass
class ListedOption:
    ticker: str
    expiry: date
    kind: str
    strike: float
    spot: float
    bid: float
    ask: float
    last: float
    mid: float
    tenor: float
    volume: float


@dataclass
class MarketData:
    prices: pd.DataFrame
    india_10y: pd.Series
    fundamentals: dict[str, Fundamentals]
    listed_option: ListedOption | None
    pulled_at: str
    notes: list[str] = field(default_factory=list)


def _naive_index(idx) -> pd.DatetimeIndex:
    idx = pd.to_datetime(idx)
    if getattr(idx, "tz", None) is not None:
        return idx.tz_convert("UTC").tz_localize(None)
    return idx


def _extract_close(raw: pd.DataFrame, tickers: tuple[str, ...]) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = list(raw.columns.get_level_values(0))
        lvl1 = list(raw.columns.get_level_values(1))
        if "Close" in lvl0:
            out = raw["Close"].copy()
        elif "Adj Close" in lvl0:
            out = raw["Adj Close"].copy()
        elif "Close" in lvl1:
            parts = {}
            for t in tickers:
                try:
                    parts[t] = raw[t]["Close"]
                except KeyError:
                    continue
            out = pd.DataFrame(parts)
        else:
            out = raw.xs(lvl0[0], axis=1, level=0).copy()
    else:
        col = "Close" if "Close" in raw.columns else raw.columns[0]
        out = raw[[col]].copy()
        if len(tickers) == 1:
            out.columns = [tickers[0]]
    out.index = _naive_index(out.index)
    keep = [t for t in tickers if t in getattr(out, "columns", [])]
    if keep:
        out = out[keep]
    return out.sort_index()


def _cache_path() -> Path:
    C.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return C.CACHE_DIR / "prices.csv"


def download_prices(universe: Universe, start: str = C.START, force: bool = False) -> pd.DataFrame:
    path = _cache_path()
    if path.exists() and not force:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    raw = yf.download(
        list(universe.all_tickers),
        start=start,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    px = _extract_close(raw, universe.all_tickers)
    px = px.dropna(how="all").ffill(limit=3)
    px.to_csv(path)
    return px


def _read_csv_url(url: str, timeout: int = 6) -> pd.DataFrame:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return pd.read_csv(StringIO(resp.read().decode()))


def fetch_india_10y(force: bool = False) -> pd.Series:
    path = C.CACHE_DIR / "india_10y.csv"
    C.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        s = pd.read_csv(path, parse_dates=["DATE"], index_col="DATE")["yield"]
        s.index = pd.to_datetime(s.index)
        return s.sort_index()
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRLTLT01INM156N"
    try:
        csv = _read_csv_url(url)
        csv = csv.rename(columns={csv.columns[0]: "DATE", csv.columns[1]: "yield"})
        csv["DATE"] = pd.to_datetime(csv["DATE"], errors="coerce")
        csv["yield"] = pd.to_numeric(csv["yield"], errors="coerce") / 100.0
        csv = csv.dropna()
        csv.to_csv(path, index=False)
        s = csv.set_index("DATE")["yield"]
        s.index = pd.to_datetime(s.index)
        return s.sort_index()
    except Exception:
        return pd.Series(dtype=float, name="yield")


def _dps_ltm(ticker: str, fallback_price: float) -> tuple[float, float]:
    t = yf.Ticker(ticker)
    try:
        div = t.dividends
    except Exception:
        div = pd.Series(dtype=float)
    if div is not None and len(div) > 0:
        idx = pd.to_datetime(div.index)
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert("UTC").tz_localize(None)
        div = div.copy()
        div.index = idx
        cutoff = div.index.max() - pd.Timedelta(days=365)
        dps = float(div[div.index >= cutoff].sum())
        if dps > 0:
            return dps, dps / fallback_price
    info = {}
    try:
        info = t.info or {}
    except Exception:
        info = {}
    dps = float(info.get("trailingAnnualDividendRate") or info.get("dividendRate") or 0.0)
    yld = float(info.get("dividendYield") or 0.0)
    if yld > 1:  # sometimes percent
        yld = yld / 100.0
    if dps == 0 and yld and fallback_price:
        dps = yld * fallback_price
    return dps, (dps / fallback_price if fallback_price else yld)


def fetch_fundamentals(ticker: str, last_price: float) -> Fundamentals:
    info: dict = {}
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}
    dps, yld = _dps_ltm(ticker, last_price)
    price = float(info.get("currentPrice") or info.get("previousClose") or last_price)
    mcap = info.get("marketCap")
    debt = info.get("totalDebt")
    roe = info.get("returnOnEquity")
    payout = info.get("payoutRatio")
    shares = info.get("sharesOutstanding")
    return Fundamentals(
        ticker=ticker,
        price=price,
        market_cap=float(mcap) if mcap else None,
        total_debt=float(debt) if debt else None,
        dps_ltm=dps,
        div_yield=yld,
        roe=float(roe) if roe else None,
        payout=float(payout) if payout else None,
        shares=float(shares) if shares else None,
    )


def _num(x, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return default if not np.isfinite(v) else v


def _mid(bid: float, ask: float, last: float) -> float:
    if bid > 0 and ask > bid:
        return 0.5 * (bid + ask)
    if bid > 0 and ask == bid:
        return bid
    return last


def fetch_listed_option(ticker: str, asof: pd.Timestamp) -> ListedOption | None:
    t = yf.Ticker(ticker)
    try:
        spot = float(t.history(period="5d")["Close"].dropna().iloc[-1])
    except Exception:
        return None
    try:
        expiries = list(t.options)
    except Exception:
        return None
    if not expiries:
        return None
    asof_ts = pd.Timestamp(asof).tz_localize(None)
    target = asof_ts + pd.Timedelta(days=45)
    best_exp = min(expiries, key=lambda e: abs((pd.Timestamp(e) - target).days))
    try:
        chain = t.option_chain(best_exp)
    except Exception:
        return None
    calls = chain.calls.copy()
    for col in ("bid", "ask", "lastPrice", "strike", "volume", "openInterest"):
        if col in calls.columns:
            calls[col] = pd.to_numeric(calls[col], errors="coerce")
    liquid = calls[(calls["bid"] > 0) & (calls["ask"] > calls["bid"])]
    if liquid.empty:
        liquid = calls[(calls["volume"].fillna(0) > 0) | (calls["openInterest"].fillna(0) > 0)]
    if liquid.empty:
        liquid = calls
    target_k = spot * 1.05
    liquid = liquid.copy()
    liquid["dist"] = (liquid["strike"] - target_k).abs()
    row = liquid.sort_values(["dist", "volume"], ascending=[True, False]).iloc[0]
    expiry = datetime.strptime(best_exp, "%Y-%m-%d").date()
    asof_d = asof_ts.date()
    tenor = max((expiry - asof_d).days / 365.0, 1.0 / 365.0)
    last = _num(row.get("lastPrice"))
    bid = _num(row.get("bid"))
    ask = _num(row.get("ask"))
    mid = _mid(bid, ask, last)
    if mid <= 0:
        return None
    return ListedOption(
        ticker=ticker,
        expiry=expiry,
        kind="call",
        strike=float(row["strike"]),
        spot=spot,
        bid=bid,
        ask=ask,
        last=last,
        mid=mid,
        tenor=tenor,
        volume=float(row.get("volume") or 0.0),
    )


def load_market(universe: Universe | None = None, force: bool = False) -> MarketData:
    universe = universe or Universe()
    notes: list[str] = []
    prices = download_prices(universe, force=force)
    india_10y = fetch_india_10y(force=force)
    if india_10y.empty:
        notes.append(f"India 10Y FRED pull failed; using labelled fallback {C.RF_FALLBACK_IN:.2%}.")
    last = prices.dropna(how="all").index.max()
    fund = {}
    for tkr in (universe.client, universe.comparator):
        last_px = float(prices[tkr].dropna().iloc[-1]) if tkr in prices else np.nan
        try:
            fund[tkr] = fetch_fundamentals(tkr, last_px)
        except Exception as exc:
            notes.append(f"Fundamentals for {tkr} incomplete ({exc}).")
            fund[tkr] = Fundamentals(
                ticker=tkr,
                price=last_px,
                market_cap=None,
                total_debt=None,
                dps_ltm=0.0,
                div_yield=0.0,
                roe=None,
                payout=None,
                shares=None,
            )
    listed = fetch_listed_option(universe.option_underlying, last)
    if listed is None:
        notes.append(f"No listed chain on {universe.option_underlying}; trying {universe.comparator}.")
        listed = fetch_listed_option(universe.comparator, last)
        if listed is None:
            notes.append("No listed option snapshot; BS vs market exhibit uses a synthetic 5% OTM call at 22% vol.")
    pulled = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return MarketData(
        prices=prices,
        india_10y=india_10y,
        fundamentals=fund,
        listed_option=listed,
        pulled_at=pulled,
        notes=notes,
    )


def last_rf_india(data: MarketData) -> float:
    if data.india_10y.empty:
        return C.RF_FALLBACK_IN
    return float(data.india_10y.dropna().iloc[-1])


def last_rf_us(prices: pd.DataFrame, ticker: str = C.US_10Y) -> float:
    if ticker not in prices.columns:
        return C.RF_FALLBACK_US
    y = prices[ticker].dropna()
    if y.empty:
        return C.RF_FALLBACK_US
    val = float(y.iloc[-1])
    return val / 100.0 if val > 1 else val
