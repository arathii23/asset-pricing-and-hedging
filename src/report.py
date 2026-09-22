"""Coverage-note HTML for the IC pack. Open memo/ic_pack.html in a browser."""

from __future__ import annotations

import html
import json
from pathlib import Path

from . import config as C


def _pct(x: float, digits: int = 2) -> str:
    return f"{100.0 * float(x):.{digits}f}%"


def _bn(x: float) -> str:
    return f"{float(x) / 1e9:+.2f}bn"


def _n(x: float, digits: int = 2) -> str:
    return f"{float(x):,.{digits}f}"


def write_html(ctx: dict | None = None) -> Path:
    C.MEMO_DIR.mkdir(parents=True, exist_ok=True)
    if ctx is None:
        ctx = json.loads((C.EXHIBIT_DIR / "summary.json").read_text())
    m = ctx
    reco = html.escape(str(m.get("reco_headline", "")))
    hedge = html.escape(str(m.get("hedge_call", "")))
    notes = html.escape(str(m.get("notes", "")))
    ml_verdict = html.escape(str(m.get("ml_verdict", "")))
    we_src = html.escape(str(m.get("we_src", "")))

    figures = [
        ("01_frontier_cml.png", "Diversified book: mean-variance frontier and two-fund CML"),
        ("02_sml.png", "Security market line vs realised average return"),
        ("03_factor_ke.png", "INFY factor contribution to cost of equity"),
        ("04_npv_tornado.png", "USD expansion NPV: WACC and FX sensitivity"),
        ("05_crr_vs_bs.png", "Binomial CRR converges to Black–Scholes"),
        ("06_greeks.png", "Listed call: delta and gamma vs spot"),
        ("07_hedge_pnl.png", "Year-1 USD receipts: hedge P&L in INR"),
        ("08_ml_nav.png", "Walk-forward allocation: ML μ vs historical μ vs Nifty"),
    ]
    fig_html = []
    for name, caption in figures:
        src = C.EXHIBIT_DIR / name
        if src.exists():
            fig_html.append(
                f"""<figure>
  <img src="../exhibits/{name}" alt="{html.escape(caption)}">
  <figcaption>{html.escape(caption)}</figcaption>
</figure>"""
            )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IC Pack · FX-Hedged Expansion Desk · Infosys</title>
  <style>
    :root {{
      --ink: #122033;
      --muted: #5c6b7a;
      --line: #d7dde3;
      --paper: #f7f5f0;
      --white: #ffffff;
      --navy: #0e2a43;
      --gold: #8a6d3b;
      --ok: #1f6b4a;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: var(--paper); color: var(--ink);
      font: 15px/1.5 "Source Sans 3", "Segoe UI", Helvetica, Arial, sans-serif; }}
    .bar {{ background: var(--navy); color: #e8eef4; padding: 10px 28px; font-size: 11px;
      letter-spacing: 0.14em; text-transform: uppercase; display: flex; justify-content: space-between; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 28px 24px 64px; }}
    .kicker {{ color: var(--gold); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; }}
    h1 {{ font-family: "Source Serif 4", Georgia, serif; font-size: 28px; font-weight: 600;
      line-height: 1.2; margin: 6px 0 8px; }}
    .sub {{ color: var(--muted); margin: 0 0 22px; }}
    .reco {{ background: var(--white); border-left: 4px solid var(--ok); padding: 16px 18px; margin: 0 0 22px; }}
    .reco strong {{ display: block; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
      color: var(--ok); margin-bottom: 6px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 0 0 28px; }}
    .kpi {{ background: var(--white); padding: 12px 14px; border: 1px solid var(--line); }}
    .kpi b {{ display: block; font-size: 20px; font-variant-numeric: tabular-nums; }}
    .kpi span {{ color: var(--muted); font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; }}
    h2 {{ font-family: "Source Serif 4", Georgia, serif; font-size: 18px; margin: 28px 0 10px;
      border-bottom: 1px solid var(--line); padding-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--white); font-variant-numeric: tabular-nums; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); font-size: 13.5px; }}
    th {{ font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
    td.num, th.num {{ text-align: right; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    figure {{ margin: 0 0 16px; background: var(--white); border: 1px solid var(--line); padding: 10px 10px 8px; }}
    figure img {{ width: 100%; height: auto; display: block; }}
    figcaption {{ color: var(--muted); font-size: 12px; padding: 8px 4px 2px; }}
    .note {{ color: var(--muted); font-size: 12.5px; margin-top: 28px; }}
    footer {{ max-width: 980px; margin: 0 auto; padding: 0 24px 40px; color: var(--muted); font-size: 11px; }}
    @media (max-width: 800px) {{
      .kpis, .grid {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media print {{
      .bar {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      figure {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="bar">
    <span>Confidential · Investment committee pack</span>
    <span>ECO423 · Financial economics · {html.escape(str(m.get("asof", "")))}</span>
  </div>
  <main>
    <div class="kicker">Coverage · Infosys (INFY.NS) · Comparator Mastercard (MA)</div>
    <h1>FX-Hedged Expansion Desk</h1>
    <p class="sub">Should the firm fund a USD {_n(m["capex_usd"]/1e6, 0)}m, 3-year expansion, and how should Treasury hedge year-1 USD receipts? Prices as of {html.escape(str(m.get("asof", "")))} · pull {html.escape(str(m.get("pulled", "")))}.</p>

    <div class="reco">
      <strong>Recommendation</strong>
      {reco}
    </div>

    <div class="kpis">
      <div class="kpi"><b>{_pct(m["wacc"])}</b><span>CAPM WACC</span></div>
      <div class="kpi"><b>{_pct(m["ke_capm"])}</b><span>Cost of equity · β { _n(m["beta"], 2)}</span></div>
      <div class="kpi"><b>{_bn(m["npv_unhedged"])}</b><span>NPV unhedged (INR)</span></div>
      <div class="kpi"><b>{_n(m["spot_fx"])} / {_n(m["fwd"])}</b><span>USDINR spot / 1y IRP fwd</span></div>
    </div>

    <h2>Required return and valuation</h2>
    <table>
      <thead>
        <tr><th></th><th class="num">INFY vs Nifty</th><th class="num">MA vs S&amp;P</th></tr>
      </thead>
      <tbody>
        <tr><td>Beta</td><td class="num">{_n(m["beta"])}</td><td class="num">{_n(m["beta_ma"])}</td></tr>
        <tr><td>Jensen α (ann.)</td><td class="num">{_pct(m["jensen"])}</td><td class="num">{_pct(m["jensen_ma"])}</td></tr>
        <tr><td>R²</td><td class="num">{_n(m["r2"])}</td><td class="num">{_n(m["r2_ma"])}</td></tr>
        <tr><td>Cost of equity</td><td class="num">{_pct(m["ke_capm"])}</td><td class="num">{_pct(m["ke_ma"])}</td></tr>
        <tr><td>Risk-free</td><td class="num">{_pct(m["rf_in"])}</td><td class="num">{_pct(m["rf_us"])}</td></tr>
        <tr><td>Labelled ERP (in ke)</td><td class="num">{_pct(m["erp"])}</td><td class="num">{_pct(m["erp_us"])}</td></tr>
        <tr><td>Sample ERP</td><td class="num">{_pct(m["erp_sample"])}</td><td class="num">{_pct(m["erp_us_sample"])}</td></tr>
      </tbody>
    </table>
    <p class="note">Equity weight { _pct(m["we"], 1) } ({we_src}). {html.escape(str(m.get("debt_line", "")))} Factor ke { _pct(m["ke_fx"]) }. Gordon {_n(m["gordon"], 1)} vs screen {_n(m["px"], 1)} ({_pct(m["premium"], 1)} to model). Implied g {_pct(m["impl_g"])}. Bond YTM used as kd; modified duration {_n(m["mod_dur"])}.</p>

    <h2>Project NPV and Treasury hedge</h2>
    <table>
      <tbody>
        <tr><td>NPV unhedged / IRP forward path</td><td class="num">{_bn(m["npv_unhedged"])} / {_bn(m["npv_hedged"])} INR</td></tr>
        <tr><td>Project IRR (unhedged INR CFs)</td><td class="num">{_pct(m["irr_unhedged"])}</td></tr>
        <tr><td>Salvage at year 3</td><td class="num">zero</td></tr>
        <tr><td>FCF cut that sets unhedged NPV to zero</td><td class="num">{_pct(m.get("fcf_haircut", 0), 0)}</td></tr>
        <tr><td>Year-1 USD notional</td><td class="num">USD {_n(m["notional"]/1e6, 0)}m</td></tr>
        <tr><td>25Δ put / collar net premium</td><td class="num">{_n(m["put_prem"], 3)} / {_n(m["collar_net"], 3)} INR per USD</td></tr>
        <tr><td>Asian vs vanilla 1y ATM call</td><td class="num">{_n(m["asian"], 3)} vs {_n(m["vanilla_call"], 3)}</td></tr>
        <tr><td>Listed {html.escape(str(m["opt_kind"]))} {html.escape(str(m["opt_ticker"]))} K={_n(m["opt_k"])} {html.escape(str(m["opt_exp"]))}</td>
            <td class="num">mid {_n(m["opt_mid"], 3)} · BS {_n(m["opt_bs"], 3)} · IV {_pct(m["opt_iv"], 1)}</td></tr>
        <tr><td>Greeks Δ / Γ / ν / Θ</td><td class="num">{_n(m["opt_delta"], 3)} / {_n(m["opt_gamma"], 4)} / {_n(m["opt_vega"], 3)} / {_n(m["opt_theta"], 3)}</td></tr>
      </tbody>
    </table>
    <p class="note">{hedge}</p>

    <h2>Walk-forward ML challenger</h2>
    <table>
      <thead>
        <tr><th></th><th class="num">ML-MV</th><th class="num">Selected hist-MV</th><th class="num">Inverse vol</th><th class="num">1/N</th><th class="num">Nifty</th></tr>
      </thead>
      <tbody>
        <tr><td>OOS excess-return Sharpe</td><td class="num">{_n(m["sh_gb"])}</td><td class="num">{_n(m["sh_hist"])}</td>
            <td class="num">{_n(m.get("sh_inv", 0))}</td><td class="num">{_n(m["sh_eq"])}</td><td class="num">{_n(m["sh_nifty"])}</td></tr>
        <tr><td>Beta vs Nifty</td><td class="num">{_n(m.get("beta_gb", 0))}</td><td class="num">{_n(m.get("beta_hist", 0))}</td>
            <td class="num">—</td><td class="num">—</td><td class="num">1.00</td></tr>
        <tr><td>Jensen α (ann.)</td><td class="num">{_pct(m.get("jensen_gb", 0))}</td><td class="num">{_pct(m.get("jensen_hist", 0))}</td>
            <td class="num">—</td><td class="num">—</td><td class="num">—</td></tr>
        <tr><td>Tracking error vs Nifty</td><td class="num">{_pct(m.get("te_gb", 0), 1)}</td><td class="num">{_pct(m.get("te_hist", 0), 1)}</td>
            <td class="num">—</td><td class="num">—</td><td class="num">—</td></tr>
        <tr><td>Information ratio</td><td class="num">{_n(m.get("ir_gb", 0))}</td><td class="num">{_n(m.get("ir_hist", 0))}</td>
            <td class="num">—</td><td class="num">—</td><td class="num">—</td></tr>
      </tbody>
    </table>
    <p class="note"><strong>Selected rule:</strong> {html.escape(str(m.get("strategy_used", "historical mean-variance")))}. Average OOS weights: {html.escape(str(m.get("avg_w_txt", "")))}. INFY RMSE GB {_n(m["rmse_gb"], 4)} · Ridge {_n(m["rmse_ridge"], 4)} · expanding mean {_n(m["rmse_hist"], 4)}. {ml_verdict}</p>

    <h2>Exhibits</h2>
    <div class="grid">
      {"".join(fig_html)}
    </div>
  </main>
  <footer>
    ECO423 engines: OLS CAPM, market+USDINR factor, two-fund CML, WACC/NPV, Gordon, IRP FX forward, CRR/Black–Scholes, Greeks, Asian MC, walk-forward Ridge/GB.
    Illustrative capex and labelled ERP. {notes}
    Not a solicitation. Public data only.
  </footer>
</body>
</html>
"""
    path = C.MEMO_DIR / "ic_pack.html"
    path.write_text(page)
    return path


if __name__ == "__main__":
    p = write_html()
    print(p)
