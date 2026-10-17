"""Build/check a provider-neutral knowledge base from explicit frozen sources.

Only --capture-sources reads the pinned Git revision/local review. Normal builds
use the frozen snapshots and never execute captured code, call models or download.
All generated files are confined to knowledge_base/. Source edits use apply_patch.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.knowledge import DEFAULT_ROOT, KnowledgeBase, digest, evaluate_retrieval, make_chunks, read_json, safe_path

PINNED = "395858d928c65da39b17c92d9f3b135a46471082"
ORIGINAL_PATHS = (
    "exhibits/summary.json", "exhibits/ml_backtest.csv", "exhibits/ml_infy_oos.csv",
    "src/config.py", "src/ml.py", "src/portfolio.py", "src/options.py",
    "src/returns.py", "src/factors.py", "run_ic_pack.py",
)
REVIEW_PATHS = (
    "exhibits/summary.json", "exhibits/ml_backtest.csv", "exhibits/option_validation.csv",
    "src/config.py", "src/ml.py", "src/portfolio.py", "src/options.py",
    "src/hedge.py", "src/review.py", "data/reference/inputs.json",
)


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def write_generated(relative: str, data: bytes, root: Path = DEFAULT_ROOT) -> None:
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def capture_sources(root: Path = DEFAULT_ROOT) -> None:
    destination = root / "sources"
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Frozen sources already exist. Refusing overwrite; use a new research version.")
    pending, records = {}, []
    # Explicit small allowlist of public project code/outputs. Never walk the folder.
    for version, paths in (("resume_v1", ORIGINAL_PATHS), ("review_v2", REVIEW_PATHS)):
        for relative in paths:
            if version == "resume_v1":
                result = subprocess.run(["git", "show", f"{PINNED}:{relative}"], cwd=ROOT,
                                        check=True, capture_output=True)
                data = result.stdout
                origin = {"kind": "git", "revision": PINNED, "repository_path": relative}
            else:
                data = safe_path(ROOT, relative).read_bytes()
                origin = {"kind": "local_review", "repository_path": relative,
                          "note": "Local snapshot, not verification of public deployment"}
            output = f"sources/{version}/{relative}"
            pending[output] = data
            records.append({"path": output, "version": version, "sha256": digest(data), "origin": origin})
    # Read/validate everything before writing any source snapshot.
    reviewed = json.loads(pending["sources/review_v2/exhibits/summary.json"])
    if reviewed.get("audit_version") != 2 or reviewed.get("reviewed_at") != "2026-10-17":
        raise ValueError("Unexpected reviewed source; choose a new explicit version instead")
    for path, data in pending.items():
        write_generated(path, data, root)
    write_generated("sources/provenance.json", json_bytes({
        "schema_version": 1, "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "Freeze once. No private files, API keys, recursive ingestion or raw source-code execution.",
        "files": records,
    }), root)


def verify_sources(root: Path = DEFAULT_ROOT) -> list[dict]:
    provenance = read_json(root / "sources/provenance.json")
    seen = set()
    for entry in provenance["files"]:
        version, path = entry["version"], entry["path"]
        prefix = f"sources/{version}/"
        allowed = ORIGINAL_PATHS if version == "resume_v1" else REVIEW_PATHS if version == "review_v2" else ()
        if not path.startswith(prefix) or path[len(prefix):] not in allowed or path in seen:
            raise ValueError("Snapshot outside source allowlist or duplicate")
        seen.add(path)
        if version == "resume_v1" and entry["origin"].get("revision") != PINNED:
            raise ValueError("Original source revision mismatch")
        if digest(safe_path(root, path).read_bytes()) != entry["sha256"]:
            raise ValueError(f"Frozen source hash mismatch: {path}")
    expected = {f"sources/{v}/{p}" for v, paths in (("resume_v1", ORIGINAL_PATHS), ("review_v2", REVIEW_PATHS)) for p in paths}
    if seen != expected:
        raise ValueError("Missing frozen source entries")
    return provenance["files"]


def literal_config(source: str) -> dict:
    """Extract constants from AST without importing/executing captured Python."""
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    # Later config expresses the teaching bridge as a comprehension: derive only
    # this explicitly known relationship, rather than evaluating arbitrary code.
    if "PROJECT_FCF_USD" not in values:
        values["PROJECT_FCF_USD"] = tuple(a - b - c for a, b, c in zip(
            values["PROJECT_COLLECTIONS_USD"], values["PROJECT_CASH_COSTS_USD"], values["PROJECT_REINVESTMENT_USD"]))
    return values


SUMMARY_FIELDS = {
    "rf_in": ("India risk-free proxy (labelled fallback)", "annual_fraction"),
    "rf_us": ("Saved USD rate input", "annual_fraction"),
    "erp": ("Assumed India equity risk premium", "annual_fraction"),
    "beta": ("Infosys versus Nifty beta", "dimensionless"),
    "ke_capm": ("CAPM required equity return", "annual_fraction"),
    "ke_fx": ("Market-plus-FX required equity return", "annual_fraction"),
    "wacc": ("CAPM-based WACC", "annual_fraction"),
    "wacc_fx": ("Factor-model WACC cross-check", "annual_fraction"),
    "we": ("Market-value equity funding weight", "fraction"),
    "spot_fx": ("Saved USDINR spot", "INR_per_USD"),
    "npv_unhedged": ("Expansion NPV, flat saved spot", "INR"),
    "npv_hedged": ("Expansion NPV, forward conversion path", "INR"),
    "irr_unhedged": ("Expansion flat-spot IRR", "annual_fraction"),
    "fcf_haircut": ("Uniform annual FCF haircut that sets flat-spot NPV to zero", "fraction"),
    "fwd": ("Model one-year USDINR forward", "INR_per_USD"),
    "notional": ("Separate Treasury dollar receipt contract", "USD"),
    "put_k": ("USD put strike", "INR_per_USD"),
    "call_k": ("USD call strike", "INR_per_USD"),
    "put_prem": ("Upfront vanilla put premium", "INR_per_USD"),
    "collar_net": ("Upfront net collar premium", "INR_per_USD"),
    "fx_vol": ("Annualised historical FX volatility", "annualised_volatility_fraction"),
    "asian": ("ATM arithmetic-average Asian CALL premium", "INR_per_USD"),
    "vanilla_call": ("ATM vanilla FX CALL premium", "INR_per_USD"),
    "collar_vol": ("Collar equally spaced scenario proceeds standard deviation", "INR_million"),
    "unhedged_vol": ("Unhedged equally spaced scenario proceeds standard deviation", "INR_million"),
    "dps": ("Saved trailing dividend per INR-listed share", "INR_per_share"),
    "gordon": ("Gordon dividend model share value", "INR_per_share"),
    "px": ("Saved INR-listed share price", "INR_per_share"),
    "impl_g": ("Implied growth with next dividend held fixed", "annual_fraction"),
    "opt_mid": ("Archived INFY ADR call mid", "USD_per_ADR"),
    "opt_k": ("INFY ADR call strike", "USD_per_ADR"),
    "opt_bs": ("ADR Black-Scholes price calibrated to same mid", "USD_per_ADR"),
    "opt_crr": ("ADR 50-step CRR price", "USD_per_ADR"),
    "opt_iv": ("Implied volatility calibrated from the ADR mid", "annualised_volatility_fraction"),
    "opt_delta": ("ADR call delta", "dimensionless"),
    "opt_gamma": ("ADR call gamma", "per_USD"),
    "opt_vega": ("ADR call vega per unit volatility", "USD_per_unit_volatility"),
    "opt_theta": ("ADR call theta per year", "USD_per_year"),
    "rmse_gb": ("INFY gradient-boosting next-week forecast RMSE", "weekly_return_fraction"),
    "rmse_ridge": ("INFY Ridge next-week forecast RMSE", "weekly_return_fraction"),
    "rmse_hist": ("INFY historical-mean next-week forecast RMSE", "weekly_return_fraction"),
    "hit_gb": ("INFY gradient-boosting direction hit rate", "fraction"),
    "sh_hist": ("Trailing historical-allocation Sharpe", "dimensionless"),
    "sh_gb": ("Gradient-boosting allocation Sharpe", "dimensionless"),
    "sh_nifty": ("Nifty PRICE reference Sharpe", "dimensionless"),
    "sh_inv": ("Inverse-volatility allocation Sharpe", "dimensionless"),
    "sh_eq": ("Equal-weight allocation Sharpe", "dimensionless"),
}
CONFIG_FIELDS = {
    "PROJECT_CAPEX_USD": ("Initial expansion spending today", "USD"),
    "PROJECT_FCF_USD": ("Illustrative unlevered FCF, years 1/2/3", "USD"),
    "PROJECT_SALVAGE_USD": ("Salvage at project end", "USD"),
    "PROJECT_HORIZON_YEARS": ("Expansion horizon", "years"),
    "GORDON_G": ("Assumed perpetual dividend growth", "annual_fraction"),
    "TAX_RATE": ("Assumed corporate tax rate", "fraction"),
    "BOND_YTM": ("Teaching bond yield to maturity", "annual_fraction"),
    "BOND_COUPON": ("Teaching bond coupon", "annual_fraction"),
    "BOOK": ("Fixed historical portfolio universe", "ticker_list"),
    "ML_MIN_TRAIN": ("Minimum eligible training observations", "weeks"),
    "ML_REFIT_EVERY": ("Forecast refit interval", "weeks"),
    "ML_COV_LOOKBACK": ("Allocation covariance lookback", "weeks"),
    "ML_BLEND": ("Model forecast share in blended return estimate", "fraction"),
    "MAX_WEIGHT": ("Position target cap at rebalance", "fraction"),
    "REBALANCE_WEEKS": ("Active allocation rebalance interval", "weeks"),
    "TRANSACTION_COST_BPS": ("Cost per unit of half-L1 one-way turnover", "basis_points"),
    "ASIAN_STEPS": ("Future monthly fixings per simulated path", "count"),
    "ASIAN_PATHS": ("Monte Carlo pricing paths", "count"),
}


def make_facts(version: str, root: Path = DEFAULT_ROOT) -> dict:
    prefix = f"sources/{version}/"
    m = read_json(root / prefix / "exhibits/summary.json")
    config = literal_config((root / prefix / "src/config.py").read_text(encoding="utf-8"))
    facts = {}
    def record(name, value, label, unit, source_file, source_field):
        facts[name] = {"value": value, "label": label, "unit": unit, "version": version,
                       "source": {"path": prefix + source_file, "field": source_field}}
    for name, (label, unit) in SUMMARY_FIELDS.items():
        record(name, m[name], label, unit, "exhibits/summary.json", name)
    for name, (label, unit) in CONFIG_FIELDS.items():
        record(name, config[name], label, unit, "src/config.py", name)
    if version == "review_v2":
        for name, label in (("sh_ridge", "Later Ridge allocation Sharpe"), ("sh_expanding", "Later expanding-mean matched baseline Sharpe")):
            record(name, m[name], label, "dimensionless", "exhibits/summary.json", name)
        record("asian_put", m["asian_put"], "Matched arithmetic-average USD PUT premium", "INR_per_USD", "exhibits/summary.json", "asian_put")
    debt_weight = 1 - m["we"]
    pv_rows = []
    for year, usd in enumerate(config["PROJECT_FCF_USD"], 1):
        inr = usd * m["spot_fx"]
        pv_rows.append({"year": year, "fcf_usd": usd, "conversion_inr_per_usd": m["spot_fx"],
                        "fcf_inr": inr, "discount_factor": (1 + m["wacc"]) ** year,
                        "present_value_inr": inr / (1 + m["wacc"]) ** year})
    capex_inr = config["PROJECT_CAPEX_USD"] * m["spot_fx"]
    total_pv = sum(row["present_value_inr"] for row in pv_rows)
    if abs(total_pv - capex_inr - m["npv_unhedged"]) > .001:
        raise ValueError(f"DCF does not reconcile: {version}")
    metrics = list(csv.DictReader(io.StringIO((root / prefix / "exhibits/ml_backtest.csv").read_text())))
    metrics = {row[""]: {key: float(value) for key, value in row.items() if key} for row in metrics}
    for strategy, field in (("hist_mv", "sh_hist"), ("gb_mv", "sh_gb"), ("nifty", "sh_nifty")):
        if abs(metrics[strategy]["sharpe"] - m[field]) > 1e-12:
            raise ValueError("Summary/metrics mismatch")
    return {"schema_version": 1, "version": version, "market_asof": m["asof"],
            "units": {"INR_per_crore": 10000000, "INR_per_million": 1000000, "INR_per_billion": 1000000000,
                      "rate_convention": "fractions, not percent values; 0.065 means 6.5%"},
            "facts": facts,
            "derived": {"debt_weight": debt_weight, "flat_spot_dcf": {"rows": pv_rows,
                        "initial_cost_inr": capex_inr, "pv_inflows_inr": total_pv,
                        "npv_inr": total_pv - capex_inr,
                        "source_fields": ["PROJECT_CAPEX_USD", "PROJECT_FCF_USD", "spot_fx", "wacc"],
                        "formula": "sum(FCF_USD[t] * spot / (1 + wacc)**t) - capex_USD * spot"}},
            "portfolio_metrics": metrics}


ORIGINAL_METHOD = """The original mean-variance allocation is an unconstrained tangency solution
normalised, negative weights clipped and weights capped at 35%. This is a
heuristic, not a solved constrained optimum. Active weights remain fixed between
four-week rebalances rather than drifting. Initial positions are assumed already
equal-weighted; active trading costs are 10bp per half-L1 turnover. The equal-weight
reference resets weights weekly without costs. Historical means use 52 weeks;
GB blends 80% expanding mean and 20% forecast. Ridge is tested for forecasts only,
without scaling, and has no separate allocation track. Shrinkage covariance is
Ledoit–Wolf. Models start after 104 eligible weeks and refit every four weeks.
These rules, the fixed asset universe and strategy selection are retrospective;
there is no untouched strategy-selection holdout."""
REVIEW_METHOD = """The later local method searches fully invested, long-only weights in
5-percentage-point steps with a 35% target cap at rebalances. It is the best
estimated-Sharpe point on that grid, not a continuous optimum. Weights drift
between trades. Initial entry and four-week equal-weight rebalancing are costed;
starting NAV is included in drawdown. Ridge is scaled using past training data
only, has its own blended allocation, and is compared with an expanding-mean
allocation using the same history window. Completed weeks exclude the original
partial-week endpoint. These changes materially alter results; the grid was not
chosen to reproduce the submitted score. There is still no untouched
strategy-selection holdout or dividend-inclusive Nifty benchmark."""


def render_results(bundle: dict, manifest: dict) -> str:
    version, facts = bundle["version"], bundle["facts"]
    value = lambda key: facts[key]["value"]
    original = version == "resume_v1"
    label = manifest["versions"][version]["label"]
    dcf = bundle["derived"]["flat_spot_dcf"]
    lines = [f"# {label} [{version}]", "", "Generated from frozen, explicitly captured sources. Do not edit numerical values here.", "",
        "## Dates, scope and provenance", "",
        f"Market snapshot: {bundle['market_asof']}. Evaluation labels: {manifest['versions'][version]['evaluation_label_start']} to {manifest['versions'][version]['evaluation_label_end']}.",
        manifest["versions"][version]["period_note"],
        (f"Original source revision: {PINNED}. This is the submitted-resume context, not a guarantee of realistic execution." if original else "Separate local extension reviewed 17 October 2026; not evidence that these changes existed in 2025, at submission, or on the live website."), "",
        "## CAPM, WACC and equity valuation numbers", "",
        f"CAPM = {value('rf_in'):.2%} + {value('beta'):.9f} × {value('erp'):.2%} = {value('ke_capm'):.8%} required equity return.",
        f"Equity weight {value('we'):.8%}; debt weight {bundle['derived']['debt_weight']:.8%}. Borrowing yield {value('BOND_YTM'):.2%}; tax assumption {value('TAX_RATE'):.0%}.",
        f"WACC = equity_weight × equity_return + debt_weight × borrowing_yield × (1 − tax) = {value('wacc'):.8%}, approximately but not exactly the equity return.",
        f"Market-plus-FX required equity return {value('ke_fx'):.8%}; its WACC cross-check {value('wacc_fx'):.8%}.",
        f"Saved trailing DPS ₹{value('dps'):.2f}; assumed dividend growth {value('GORDON_G'):.0%}; next dividend ₹{value('dps')*(1+value('GORDON_G')):.2f}. Gordon value ₹{value('gordon'):.2f} per share versus saved price ₹{value('px'):.2f}. Fixed-next-dividend implied growth {value('impl_g'):.4%}.",
        "India's 6.50% is a labelled rate fallback and 5.50% ERP an assumption. Frozen capital mix/DPS are inherited derived inputs, not newly verified raw filings. The Gordon comparison is not proof of mispricing.", "",
        "## Expansion NPV calculation and the 8.37 billion rupee total", "",
        f"Illustrative spending today: USD {value('PROJECT_CAPEX_USD')/1e6:.0f}m. FCF in years 1/2/3: USD 32m/36m/40m. Spot is {value('spot_fx'):.9f} INR/USD. All future cash uses that same spot for this scenario. Zero salvage after year three.",
        "", "| Year | USD FCF (million) | INR FCF (crore) | Divide by (1 + WACC)^year | Present value (crore) |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in dcf["rows"]:
        lines.append(f"| {row['year']} | {row['fcf_usd']/1e6:.0f} | {row['fcf_inr']/1e7:.6f} | {row['discount_factor']:.9f} | {row['present_value_inr']/1e7:.6f} |")
    lines += ["", f"Present value of inflows = ₹{dcf['pv_inflows_inr']:,.2f} = ₹{dcf['pv_inflows_inr']/1e7:.6f} crore ≈ ₹{dcf['pv_inflows_inr']/1e9:.2f} billion. This is NOT ₹8.37 million.",
        f"Spending today = USD 80m × {value('spot_fx'):.9f} = ₹{dcf['initial_cost_inr']/1e7:.6f} crore.",
        f"NPV = inflow PV − today's spending = ₹{value('npv_unhedged'):,.2f} = ₹{value('npv_unhedged')/1e7:.6f} crore, not the full inflow PV.",
        f"Forward-path NPV = ₹{value('npv_hedged')/1e7:.6f} crore at the same WACC. Flat-spot IRR {value('irr_unhedged'):.4%}; a uniform FCF reduction of {value('fcf_haircut'):.4%} removes the base NPV margin.",
        "Cash flows are assumptions, not Infosys management forecasts. Company WACC is a similar-risk teaching proxy. The later customer-collection/cost bridge was not present in the original version.", "",
        "## Currency hedge and option numbers", "",
        f"Separate Treasury receipt USD {value('notional')/1e6:.0f}m, not the expansion's USD 32m first-year FCF. One-year model forward {value('fwd'):.6f} INR/USD; historical FX volatility {value('fx_vol'):.4%}.",
        f"Put strike {value('put_k'):.6f}, call strike {value('call_k'):.6f} INR/USD. Upfront put premium {value('put_prem'):.8f}, net collar premium {value('collar_net'):.8f} INR/USD. Collar caps upside; a forward fixes the rate.",
        f"Equally spaced scenario proceeds standard deviation: unhedged ₹{value('unhedged_vol'):.6f} million, collar ₹{value('collar_vol'):.6f} million. This is scenario dispersion, not forecast volatility or VaR.",
        f"ATM Asian CALL {value('asian'):.8f} versus vanilla CALL {value('vanilla_call'):.8f} INR/USD: different payoffs, not equivalent protection. Monte Carlo uses 12 future fixings, 40,000 risk-neutral paths and seed 7.",
        ("Original Asian illustration is a CALL, not a matched average-rate receipt hedge. Original payoff tables subtract upfront premiums without financing them to the receipt date." if original else f"Later matched average-rate PUT premium {value('asian_put'):.8f} INR/USD. Compare terminal collar and average put against the same receipt contract and same paths; all cash settles year-end, premiums financed to settlement. This does not model monthly cash collections."),
        f"Archived INFY ADR USD call: strike {value('opt_k'):.2f}, expiry 20 November 2026, mid {value('opt_mid'):.2f}, implied vol {value('opt_iv'):.6%}, BS {value('opt_bs'):.8f}, 50-step CRR {value('opt_crr'):.8f} USD/ADR.",
        f"ADR delta {value('opt_delta'):.8f}, gamma {value('opt_gamma'):.8f} per USD, vega {value('opt_vega'):.8f} per unit volatility, theta {value('opt_theta'):.8f} USD/year. BS is calibrated to the same mid; raw spot/bid/ask snapshot is missing, not independent market validation.", "",
        "## Allocation method and what existed in this version", "", ORIGINAL_METHOD if original else REVIEW_METHOD, "",
        "## Recorded portfolio Sharpe results and interpretation", "",
        "| Allocation/reference | Annualised sample Sharpe |", "|---|---:|",
    ]
    names = {"hist_mv": "Trailing historical allocation", "expanding_mv": "Expanding-mean matched baseline", "ridge_mv": "Ridge allocation", "gb_mv": "Gradient-boosting allocation", "inv_vol": "Inverse-volatility allocation", "equal": "Equal weighting", "nifty": "Nifty PRICE index reference"}
    for key, label in names.items():
        if key in bundle["portfolio_metrics"]:
            lines.append(f"| {label} | {bundle['portfolio_metrics'][key]['sharpe']:.9f} |")
    if original:
        hist = bundle["portfolio_metrics"]["hist_mv"]
        lines += ["", f"Original historical Sharpe = ({hist['ann_mean']:.9f} − 0.065) / {hist['ann_vol']:.9f} = {value('sh_hist'):.9f}, rounded 0.30. Nifty {value('sh_nifty'):.9f} rounds 0.22. These are ratios, not 30% and 22% returns.",
                  "The historical rule leads the tested GB rule in this original sample. That does not show a durable trading edge or validate the later corrected implementation."]
    else:
        lines += ["", "Ridge's sample advantage over the expanding-mean matched baseline is small; it is not proof of a statistically reliable or durable ML edge. The negative trailing-historical result belongs to this changed implementation, not the original method."]
    lines += [f"INFY forecast RMSE: GB {value('rmse_gb'):.9f}, Ridge {value('rmse_ridge'):.9f}, historical mean {value('rmse_hist'):.9f}; GB sign hit {value('hit_gb'):.4%}.",
        "Nifty is a price-only index while adjusted equities include dividend adjustments: no dividend-matched market-outperformance claim. Universe/rules are retrospectively selected. A modest sample Sharpe is not investment advice.", "",
        "## How can these numbers be traced?", "",
        f"Typed values and units: facts/{version}.json. Raw saved summary/metrics/config/code: sources/{version}/. File hashes and origins: sources/provenance.json. Source labels support traceability, not independent audit certification.", ""]
    return "\n".join(lines)


def build(check: bool = False, root: Path = DEFAULT_ROOT) -> dict:
    sources = verify_sources(root)
    manifest = read_json(root / "manifest.json")
    if manifest["versions"]["resume_v1"]["git_revision"] != PINNED:
        raise ValueError("Manifest original revision changed")
    expected = {}
    for version, filename in (("resume_v1", "08_resume_v1.md"), ("review_v2", "09_review_v2.md")):
        bundle = make_facts(version, root)
        expected[f"facts/{version}.json"] = json_bytes(bundle)
        expected[f"documents/{filename}"] = render_results(bundle, manifest).encode()
    for path, data in expected.items():
        if check:
            if not safe_path(root, path).exists() or safe_path(root, path).read_bytes() != data:
                raise ValueError(f"Generated file stale: {path}")
        else:
            write_generated(path, data, root)
    kb = KnowledgeBase(root)
    chunks = make_chunks(root)
    expected["build/chunks.jsonl"] = "".join(json.dumps(c, ensure_ascii=False, allow_nan=False) + "\n" for c in chunks).encode()
    report = {"schema_version": 1, "document_count": len(manifest["documents"]),
              "passage_count": len(chunks), "frozen_source_files_verified": len(sources),
              "default_version": manifest["default_version"], "network_calls": 0,
              "retrieval": evaluate_retrieval(kb)}
    expected["build/validation.json"] = json_bytes(report)
    for path, data in expected.items():
        if check:
            if not safe_path(root, path).exists() or safe_path(root, path).read_bytes() != data:
                raise ValueError(f"Generated file stale: {path}")
        else:
            write_generated(path, data, root)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-sources", action="store_true", help="Explicit first-time source capture; refuses overwrite")
    parser.add_argument("--check", action="store_true", help="Verify generated artifacts without writing")
    args = parser.parse_args()
    if args.capture_sources and args.check:
        parser.error("--capture-sources and --check are separate operations")
    if args.capture_sources:
        capture_sources()
    try:
        report = build(check=args.check)
    except FileNotFoundError as error:
        raise SystemExit(f"Missing KB input ({error.filename}). Initial capture: --capture-sources; no silent refresh.") from error
    retrieval = report["retrieval"]
    print(f"{'Checked' if args.check else 'Built'} {report['document_count']} documents, {report['passage_count']} passages; "
          f"{retrieval['evidence_hits']}/{retrieval['graded_retrieval_cases']} lexical evidence hits@4. "
          "No Gemini calls or LLM accuracy claim.")


if __name__ == "__main__":
    main()
