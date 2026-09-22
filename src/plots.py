"""Exhibit figures for the IC pack."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from .portfolio import Frontier, cml_vol_grid


def _setup() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (8.2, 4.8),
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
        }
    )
    C.EXHIBIT_DIR.mkdir(parents=True, exist_ok=True)


def save(fig: plt.Figure, name: str) -> Path:
    path = C.EXHIBIT_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def plot_frontier(front: Frontier, asset_vol: np.ndarray, asset_ret: np.ndarray, names: list[str]) -> Path:
    _setup()
    fig, ax = plt.subplots()
    ax.plot(front.vol, front.targets, color="#1f4e79", label="Min-var frontier")
    grid = np.linspace(0, max(front.vol.max(), front.tangency_vol) * 1.15, 40)
    ax.plot(grid, cml_vol_grid(front.rf, front.tangency_ret, front.tangency_vol, grid), color="#c45911", label="CML (two-fund)")
    ax.scatter(asset_vol, asset_ret, color="#7f7f7f", zorder=3)
    for x, y, n in zip(asset_vol, asset_ret, names):
        ax.annotate(n.replace(".NS", ""), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.scatter([front.gmv_vol], [front.gmv_ret], color="#2e7d32", zorder=4, label="GMV")
    ax.scatter([front.tangency_vol], [front.tangency_ret], color="#c45911", zorder=4, label="Tangency")
    ax.set_xlabel("Annualised volatility")
    ax.set_ylabel("Annualised expected return")
    ax.set_title("Diversified book: mean-variance frontier and two-fund CML")
    ax.legend(frameon=False)
    return save(fig, "01_frontier_cml.png")


def plot_sml(rf: float, prem: float, points: list[tuple[float, float, str]]) -> Path:
    _setup()
    fig, ax = plt.subplots()
    betas = np.linspace(0, max(p[0] for p in points) * 1.15, 40)
    ax.plot(betas, rf + prem * betas, color="#1f4e79", label="SML")
    for b, r, name in points:
        ax.scatter([b], [r], zorder=3)
        ax.annotate(name, (b, r), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Beta")
    ax.set_ylabel("Annualised return (simple)")
    ax.set_title("Security market line vs realised average return")
    ax.legend(frameon=False)
    return save(fig, "02_sml.png")


def plot_factor_contrib(frame: pd.DataFrame, title: str, name: str) -> Path:
    _setup()
    fig, ax = plt.subplots()
    ax.bar(frame.index.astype(str), frame["contrib"], color="#1f4e79")
    ax.set_ylabel("Contribution to cost of equity")
    ax.set_title(title)
    return save(fig, name)


def plot_tornado(frame: pd.DataFrame) -> Path:
    _setup()
    fig, ax = plt.subplots()
    colors = ["#c45911" if d < 0 else "#2e7d32" for d in frame["delta"]]
    ax.barh(frame["case"], frame["npv"] / 1e9, color=colors)
    ax.set_xlabel("NPV (INR billions)")
    ax.set_title("USD expansion NPV: WACC and FX sensitivity")
    return save(fig, "04_npv_tornado.png")


def plot_crr_vs_bs(steps: list[int], crr: list[float], bs: float) -> Path:
    _setup()
    fig, ax = plt.subplots()
    ax.plot(steps, crr, marker="o", color="#1f4e79", label="CRR binomial")
    ax.axhline(bs, color="#c45911", linestyle="--", label="Black–Scholes")
    ax.set_xlabel("Tree steps")
    ax.set_ylabel("Call price")
    ax.set_title("Binomial CRR converges to Black–Scholes")
    ax.legend(frameon=False)
    return save(fig, "05_crr_vs_bs.png")


def plot_greeks(spots: np.ndarray, deltas: np.ndarray, gammas: np.ndarray) -> Path:
    _setup()
    fig, ax = plt.subplots()
    ax.plot(spots, deltas, color="#1f4e79", label="Delta")
    ax.set_xlabel("Spot")
    ax.set_ylabel("Delta")
    ax2 = ax.twinx()
    ax2.plot(spots, gammas, color="#c45911", label="Gamma")
    ax2.set_ylabel("Gamma")
    ax.set_title("Call delta and gamma vs spot")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, frameon=False)
    ax2.grid(False)
    return save(fig, "06_greeks.png")


def plot_hedge(table: pd.DataFrame) -> Path:
    _setup()
    fig, ax = plt.subplots()
    ax.plot(table["usd_inr"], table["unhedged_inr_m"], label="Unhedged", color="#7f7f7f")
    ax.plot(table["usd_inr"], table["forward_inr_m"], label="Sell USD forward", color="#1f4e79")
    ax.plot(table["usd_inr"], table["put_inr_m"], label="Buy USD put", color="#2e7d32")
    ax.plot(table["usd_inr"], table["collar_inr_m"], label="Collar", color="#c45911")
    ax.set_xlabel("USDINR at horizon")
    ax.set_ylabel("INR proceeds (millions)")
    ax.set_title("Year-1 USD receipts: hedge P&L in INR")
    ax.legend(frameon=False)
    return save(fig, "07_hedge_pnl.png")


def plot_ml_nav(wealth: pd.DataFrame) -> Path:
    _setup()
    fig, ax = plt.subplots()
    labels = {
        "gb_mv": "Long-only MV (boosted μ)",
        "hist_mv": "Long-only MV (historical μ)",
        "inv_vol": "Inverse volatility",
        "equal": "Equal weight IT book",
        "nifty": "Nifty",
    }
    colors = {
        "gb_mv": "#1f4e79",
        "hist_mv": "#7f7f7f",
        "inv_vol": "#9467bd",
        "equal": "#2e7d32",
        "nifty": "#c45911",
    }
    for col in wealth.columns:
        ax.plot(wealth.index, wealth[col], label=labels.get(col, col), color=colors.get(col))
    ax.set_ylabel("Growth of ₹1 (walk-forward)")
    ax.set_xlabel("Date")
    ax.set_title("OOS allocation: ML μ vs historical-μ mean-variance vs Nifty")
    ax.legend(frameon=False)
    return save(fig, "08_ml_nav.png")
