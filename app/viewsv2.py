"""
FINAL DECISION & STRATEGY ENGINE
═══════════════════════════════════════════════════════════════════════════════
Drop these functions into your existing views.py (or a new strategy_views.py).

This is the LAST STEP in your pipeline:
  upload → map columns → clean_save → run_analysis → [THIS FILE]

Adds three things:
  1. generate_final_report(dataset, run_id)
       - Called automatically at the end of run_analysis()
       - Reads every AnalysisResult for this run
       - Asks local Llama to write the full decision memo
       - Saves a FinalStrategyReport record

  2. final_strategy_view(request)
       - GET endpoint:  /api/strategy/?run_id=xxx&dataset_id=yyy
       - Returns the complete JSON decision package for the dashboard

  3. generate_strategy_pdf_view(request)  [optional]
       - GET endpoint:  /api/strategy/pdf/?run_id=xxx
       - Returns a downloadable PDF report the manager can keep

═══════════════════════════════════════════════════════════════════════════════
"""

import io
import json
import os
import requests
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import minimize_scalar

from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from statsmodels.formula.api import ols

from .models import (
    Dataset, CSRRecord, AnalysisResult,
    MLModel, MLPrediction, AIRecommendation,
    FinalStrategyReport,  # ← add this model (see models section below)
)
from .utils import safe_json

# ─── Llama config (same as analysis engine) ─────────────────────────────────
LLAMA_ENDPOINT = os.getenv("LLAMA_ENDPOINT", "http://localhost:11434/api/generate")
LLAMA_MODEL    = os.getenv("LLAMA_MODEL",    "llama3")


def llama_generate(prompt: str, max_tokens: int = 800) -> str:
    payload = {
        "model":  LLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2},
    }
    try:
        resp = requests.post(LLAMA_ENDPOINT, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response") or data.get("content") or str(data)
    except Exception as exc:
        return f"[Llama unavailable – running rule-based fallback: {exc}]"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — COLLECT & STRUCTURE ALL RESULTS FROM A RUN
# ═══════════════════════════════════════════════════════════════════════════

def collect_run_findings(dataset, run_id: str) -> dict:
    """
    Reads every AnalysisResult for run_id and packages the numbers that
    matter into a clean dict.  This is the single source of truth that
    feeds both the Llama prompt and the JSON response.
    """
    results = {
        r.result_type: r
        for r in AnalysisResult.objects.filter(run_id=run_id)
    }

    findings = {
        "run_id":     run_id,
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "analyses_run": list(results.keys()),
    }

    # ── OLS: does CSR significantly affect ROA? ───────────────────────────
    if "OLS" in results:
        rj = results["OLS"].result_json or {}
        findings["ols"] = {
            "csr_coef":      rj.get("csr", None),
            "intercept":     rj.get("Intercept", None),
            "summary":       results["OLS"].summary_text or "",
        }

    # ── TRADEOFF: slopes of CSR on ROA and TobinQ ────────────────────────
    if "TRADEOFF" in results:
        rj = results["TRADEOFF"].result_json or {}
        findings["tradeoff"] = {
            "roa_coef":   rj.get("roa_coef"),
            "tobq_coef":  rj.get("tobq_coef"),
            "roa_pval":   rj.get("roa_pval"),
            "tobq_pval":  rj.get("tobq_pval"),
            "roa_direction":  "negative" if (rj.get("roa_coef") or 0) < 0 else "positive",
            "tobq_direction": "negative" if (rj.get("tobq_coef") or 0) < 0 else "positive",
        }

    # ── OPTIMUM: what CSR level maximises value? ──────────────────────────
    if "OPTIMUM" in results:
        rj = results["OPTIMUM"].result_json or {}
        findings["optimum"] = {
            "optimal_csr":    rj.get("optimal_csr"),
            "current_csr":    rj.get("current_csr"),
            "csr_gap":        rj.get("csr_gap"),
            "direction":      "increase" if (rj.get("csr_gap") or 0) > 0 else "decrease",
            "optimal_roa":    rj.get("optimal_roa"),
            "optimal_tobinq": rj.get("optimal_tobinq"),
            "tobinq_gain":    rj.get("tobinq_gain"),
            "roa_floor":      rj.get("roa_floor"),
        }

    # ── CSR DRIVERS: what factors drive CSR up or down? ──────────────────
    if "CSR_DRIVERS" in results:
        rj = results["CSR_DRIVERS"].result_json or {}
        # importance dict stored as {feature: {0: val, 1: val ...}}
        try:
            imp = rj.get("importance", {})
            features = list(imp.keys()) if isinstance(imp, dict) else []
            vals = [imp[f].get("0", 0) if isinstance(imp[f], dict) else imp[f]
                    for f in features]
            paired = sorted(zip(features, vals), key=lambda x: -x[1])
            findings["csr_drivers"] = [
                {"feature": f, "importance": round(v, 4)} for f, v in paired[:6]
            ]
        except Exception:
            findings["csr_drivers"] = []

    # ── CSR DIRECTION: positive/negative coefficients ────────────────────
    if "CSR_DIRECTION" in results:
        rj = results["CSR_DIRECTION"].result_json or {}
        try:
            feats   = rj.get("feature", {})
            coefs   = rj.get("coefficient", {})
            pvals   = rj.get("p_value", {})
            rows = []
            for k in feats:
                c = coefs.get(k, 0) if isinstance(coefs, dict) else 0
                p = pvals.get(k, 1) if isinstance(pvals, dict) else 1
                rows.append({
                    "feature": feats[k] if isinstance(feats, dict) else feats,
                    "coef": round(float(c), 4),
                    "pval": round(float(p), 4),
                    "significant": float(p) < 0.05,
                    "direction": "increases CSR" if float(c) > 0 else "decreases CSR",
                })
            findings["csr_direction"] = rows
        except Exception:
            findings["csr_direction"] = []

    # ── ML FEATURE IMPORTANCES (aggregated across models/targets) ─────────
    ml_preds = MLPrediction.objects.filter(model__dataset=dataset)
    aggregated_imp = {}
    for pred in ml_preds:
        fi = pred.feature_importance
        if not fi:
            continue
        model_features = pred.model.features_used or []
        for i, feat in enumerate(model_features):
            if i < len(fi):
                aggregated_imp[feat] = aggregated_imp.get(feat, 0) + fi[i]
    if aggregated_imp:
        total = sum(aggregated_imp.values()) or 1
        findings["ml_feature_importance"] = sorted(
            [{"feature": k, "importance": round(v / total, 4)}
             for k, v in aggregated_imp.items()],
            key=lambda x: -x["importance"]
        )[:8]

    # ── DESCRIPTIVE STATS: basic data health ─────────────────────────────
    if "DESCRIPTIVE" in results:
        rj = results["DESCRIPTIVE"].result_json or {}
        mean_vals = rj.get("mean", {})
        findings["descriptive"] = {
            "csr_mean":  mean_vals.get("csr"),
            "roa_mean":  mean_vals.get("roa"),
            "roe_mean":  mean_vals.get("roe"),
            "tobq_mean": mean_vals.get("tobin_q"),
        }

    # ── CSR SIMULATION results ────────────────────────────────────────────
    if "CSR_SIMULATION" in results:
        rj = results["CSR_SIMULATION"].result_json or {}
        findings["simulation"] = rj
        findings["simulation_summary"] = results["CSR_SIMULATION"].summary_text

    # ── VIF: multicollinearity warning ───────────────────────────────────
    if "VIF" in results:
        rj = results["VIF"].result_json or {}
        try:
            vif_vals = rj.get("VIF", {})
            high = {k: v for k, v in vif_vals.items() if float(v) > 10}
            findings["vif_warning"] = (
                f"High multicollinearity detected in: {', '.join(high.keys())}"
                if high else "No multicollinearity issues."
            )
        except Exception:
            findings["vif_warning"] = ""

    # ── HAUSMAN: FE vs RE ─────────────────────────────────────────────────
    if "HAUSMAN" in results:
        rj = results["HAUSMAN"].result_json or {}
        try:
            p = list((rj.get("p-value") or {}).values())[0]
            findings["hausman"] = (
                "Fixed Effects model preferred (p < 0.05)"
                if float(p) < 0.05 else "Random Effects model acceptable"
            )
        except Exception:
            findings["hausman"] = ""

    return findings


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — BUILD THE LLAMA PROMPT & GENERATE THE DECISION MEMO
# ═══════════════════════════════════════════════════════════════════════════

def _fmt(val, decimals=4):
    """Safe number formatter — handles None."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}"
    except Exception:
        return str(val)


def build_strategy_prompt(f: dict) -> str:
    """
    Builds the Llama prompt from structured findings.
    Sections map directly to what the manager cares about.
    """
    td  = f.get("tradeoff", {})
    opt = f.get("optimum", {})
    drv = f.get("csr_drivers", [])
    csd = f.get("csr_direction", [])
    dsc = f.get("descriptive", {})
    sim = f.get("simulation_summary", "")
    mfi = f.get("ml_feature_importance", [])

    drivers_text = "\n".join(
        f"  • {d['feature']}: importance {d['importance']}"
        for d in drv[:5]
    ) or "  Not available"

    direction_text = "\n".join(
        f"  • {d['feature']} {d['direction']} (coef={d['coef']}, p={d['pval']})"
        for d in csd if d.get("significant")
    ) or "  No significant drivers identified"

    ml_text = "\n".join(
        f"  • {m['feature']}: {m['importance']}"
        for m in mfi[:5]
    ) or "  Not available"

    prompt = f"""You are a senior CSR strategy advisor writing a final decision memo to the CSR Manager of a listed firm.

Below are the quantitative findings from a full statistical and machine learning analysis of the firm's dataset.
Your job is to turn these numbers into a CLEAR, ACTIONABLE decision memo. Write in plain English. Be specific.

═══════════════ ANALYSIS FINDINGS ═══════════════

DATASET: {f.get('dataset_name', 'N/A')}
ANALYSES COMPLETED: {', '.join(f.get('analyses_run', []))}

--- CURRENT PERFORMANCE SNAPSHOT ---
Mean CSR score:    {_fmt(dsc.get('csr_mean'), 3)}
Mean ROA:          {_fmt(dsc.get('roa_mean'), 4)}
Mean ROE:          {_fmt(dsc.get('roe_mean'), 4)}
Mean Tobin Q:      {_fmt(dsc.get('tobq_mean'), 4)}

--- HOW CSR AFFECTS FINANCIAL PERFORMANCE ---
Effect of CSR on short-term profitability (ROA):
  Coefficient = {_fmt(td.get('roa_coef'))}, p-value = {_fmt(td.get('roa_pval'), 3)}
  Direction: CSR has a {td.get('roa_direction','unknown')} effect on ROA
  Interpretation: {"As CSR investment increases, short-term profitability tends to DECLINE — this is the trade-off cost." if td.get('roa_direction') == 'negative' else "CSR investment improves short-term profitability."}

Effect of CSR on market value (Tobin Q):
  Coefficient = {_fmt(td.get('tobq_coef'))}, p-value = {_fmt(td.get('tobq_pval'), 3)}
  Direction: CSR has a {td.get('tobq_direction','unknown')} effect on firm market value
  Interpretation: {"As CSR investment increases, the market values the firm MORE HIGHLY — the long-term payoff." if td.get('tobq_direction') == 'positive' else "CSR investment reduces market valuation."}

--- OPTIMAL CSR LEVEL (CALCULATED) ---
Current median CSR score:      {_fmt(opt.get('current_csr'), 3)}
Calculated OPTIMAL CSR score:  {_fmt(opt.get('optimal_csr'), 3)}
Gap (how much to move):        {_fmt(opt.get('csr_gap'), 3)} units ({opt.get('direction','unknown')})
At the optimal point:
  → Predicted ROA:    {_fmt(opt.get('optimal_roa'))}  (floor maintained at {_fmt(opt.get('roa_floor'))})
  → Predicted Tobin Q:{_fmt(opt.get('optimal_tobinq'))}
  → Expected Tobin Q gain vs current: {_fmt(opt.get('tobinq_gain'))}

--- WHAT DRIVES CSR (ML FEATURE IMPORTANCE) ---
Top factors that most strongly predict CSR level:
{drivers_text}

--- WHAT IMPROVES OR REDUCES CSR (REGRESSION COEFFICIENTS) ---
Significant determinants of CSR (OLS on CSR as dependent variable):
{direction_text}

--- ML MODEL FEATURE IMPORTANCE (AGGREGATED) ---
{ml_text}

--- SCENARIO SIMULATION ---
{sim or 'Not run.'}

--- DATA QUALITY NOTES ---
{f.get('vif_warning', '')}
{f.get('hausman', '')}

═══════════════ YOUR TASK ═══════════════

Write the FINAL DECISION MEMO for the CSR Manager. Use this EXACT structure:

## EXECUTIVE SUMMARY
(2 sentences: what the data shows and what the manager should do)

## FINDING 1 — How CSR Affects Financial Performance
(Explain the trade-off: short-term profitability vs long-term market value. Use the actual numbers.)

## FINDING 2 — The Optimal CSR Level
(Tell the manager the exact recommended CSR score, how far to move, and what improvement to expect.)

## FINDING 3 — What Drives CSR Up (and What Pulls It Down)
(Based on regression + ML: list the top 3 factors the manager can control to improve CSR.)

## FINDING 4 — Financial Performance Can Improve Because...
(Based on the analysis: name 2-3 specific levers that improve ROA and Tobin Q simultaneously.)

## PRIORITY ACTION PLAN
Action 1 (IMMEDIATE): ...
Action 2 (SHORT-TERM, 6–12 months): ...
Action 3 (LONG-TERM, 12–24 months): ...

## WHAT TO MONITOR
- Metric 1: [what, why, how often]
- Metric 2: [what, why, how often]

## RISK WARNING
(One paragraph: what happens if the firm over-invests in CSR beyond the optimal point.)

Keep the memo under 500 words. Use the actual numbers from the findings. Do not use vague language.
"""
    return prompt


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — RULE-BASED FALLBACK (when Llama is offline)
# ═══════════════════════════════════════════════════════════════════════════

def build_rule_based_memo(f: dict) -> str:
    """
    Generates a structured decision memo purely from the numbers,
    no AI required. Used as fallback and for comparison.
    """
    td  = f.get("tradeoff", {})
    opt = f.get("optimum", {})
    drv = f.get("csr_drivers", [])
    csd = f.get("csr_direction", [])
    dsc = f.get("descriptive", {})

    positive_drivers = [d["feature"] for d in csd if d.get("significant") and d.get("coef", 0) > 0]
    negative_drivers = [d["feature"] for d in csd if d.get("significant") and d.get("coef", 0) < 0]
    top_ml = [d["feature"] for d in drv[:3]]

    direction = opt.get("direction", "adjust")
    gap       = abs(opt.get("csr_gap") or 0)
    opt_csr   = opt.get("optimal_csr")
    cur_csr   = opt.get("current_csr")
    tobq_gain = opt.get("tobinq_gain") or 0
    roa_dir   = td.get("roa_direction", "unknown")
    tobq_dir  = td.get("tobq_direction", "unknown")

    memo = f"""
## EXECUTIVE SUMMARY
Based on the full statistical analysis of your dataset, CSR investment has a
{roa_dir} effect on short-term profitability (ROA) and a {tobq_dir} effect on
long-term market value (Tobin Q). The firm should {direction} its CSR score
by {_fmt(gap, 3)} units (from {_fmt(cur_csr, 3)} to {_fmt(opt_csr, 3)}) to
maximise firm value while protecting profitability.

## FINDING 1 — How CSR Affects Financial Performance
CSR→ROA coefficient: {_fmt(td.get('roa_coef'))} (p={_fmt(td.get('roa_pval'),3)}).
{"This is a negative relationship: higher CSR spending compresses short-term profits." if roa_dir == "negative" else "Higher CSR spending improves short-term profits."}

CSR→Tobin Q coefficient: {_fmt(td.get('tobq_coef'))} (p={_fmt(td.get('tobq_pval'),3)}).
{"This is a positive relationship: the market rewards CSR-active firms with higher valuations." if tobq_dir == "positive" else "Market valuation is reduced by CSR spending."}

## FINDING 2 — The Optimal CSR Level
The calculated optimal CSR score is {_fmt(opt_csr, 3)}.
Current position: {_fmt(cur_csr, 3)}.
Recommended move: {direction} by {_fmt(gap, 3)} units.
Expected Tobin Q improvement: +{_fmt(tobq_gain, 4)}.
ROA protected at floor: {_fmt(opt.get('roa_floor'), 4)}.

## FINDING 3 — What Drives CSR Up (and What Pulls It Down)
Top ML predictors of CSR: {', '.join(top_ml) if top_ml else 'N/A'}
Factors that INCREASE CSR (statistically significant): {', '.join(positive_drivers) if positive_drivers else 'None identified'}
Factors that DECREASE CSR (statistically significant): {', '.join(negative_drivers) if negative_drivers else 'None identified'}

## FINDING 4 — Financial Performance Can Improve Because...
1. Moving CSR to its optimal level ({_fmt(opt_csr, 3)}) is projected to improve
   Tobin Q by {_fmt(tobq_gain, 4)} while keeping ROA above {_fmt(opt.get('roa_floor'), 4)}.
2. Reducing {', '.join(negative_drivers[:2]) if negative_drivers else 'leverage/risk factors'}
   is associated with better CSR and improved firm stability.
3. Strengthening {', '.join(positive_drivers[:2]) if positive_drivers else 'governance structures'}
   simultaneously supports both CSR scores and market valuation.

## PRIORITY ACTION PLAN
Action 1 (IMMEDIATE): {direction.capitalize()} CSR investment by {_fmt(gap,3)} units
  to reach the optimal score of {_fmt(opt_csr, 3)}.
Action 2 (SHORT-TERM, 6–12 months): Address the top CSR driver —
  {top_ml[0] if top_ml else 'board composition and governance'} —
  through targeted policy changes.
Action 3 (LONG-TERM, 12–24 months): Build a CSR disclosure framework
  that demonstrates market value creation to investors (supports Tobin Q).

## WHAT TO MONITOR
- Tobin Q: Track quarterly. Target improvement of {_fmt(tobq_gain, 4)} within 12 months.
- ROA: Ensure it stays above floor of {_fmt(opt.get('roa_floor'), 4)} during transition.

## RISK WARNING
If CSR investment is pushed beyond the optimal score of {_fmt(opt_csr, 3)},
the model predicts diminishing returns on firm value while profitability continues
to decline. The firm must treat {_fmt(opt_csr, 3)} as a ceiling in the short term
and reassess annually as new data is collected.
"""
    return memo.strip()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — GENERATE FINAL STRATEGY CHART (summary visual)
# ═══════════════════════════════════════════════════════════════════════════

def generate_strategy_chart(findings: dict) -> io.BytesIO:
    """
    4-panel summary chart:
      [0] CSR trade-off curve (ROA vs TobinQ)
      [1] Optimal CSR bar
      [2] Top CSR drivers horizontal bar
      [3] Priority action text panel
    """
    opt = findings.get("optimum", {})
    td  = findings.get("tradeoff", {})
    drv = findings.get("csr_drivers", []) or findings.get("ml_feature_importance", [])

    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor("#FAFAFA")
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    # ── Panel 0: Trade-off curve ──────────────────────────────────────────
    ax0 = fig.add_subplot(gs[0, 0])
    csr_range = np.linspace(
        (opt.get("current_csr") or 0.3) * 0.5,
        (opt.get("optimal_csr") or 0.8) * 1.5,
        100
    )
    roa_coef  = td.get("roa_coef")  or -0.02
    tobq_coef = td.get("tobq_coef") or  0.15
    pred_roa  = 0.05 + roa_coef  * csr_range
    pred_tobq = 1.0  + tobq_coef * csr_range

    ax0b = ax0.twinx()
    ax0.plot(csr_range, pred_roa,  color="#E85D24", lw=2, label="Predicted ROA")
    ax0b.plot(csr_range, pred_tobq, color="#1D9E75", lw=2, ls="--", label="Predicted Tobin Q")
    if opt.get("optimal_csr"):
        ax0.axvline(opt["optimal_csr"], color="#534AB7", lw=1.5, ls=":", label="Optimal CSR")
    ax0.set_xlabel("CSR Score", fontsize=9)
    ax0.set_ylabel("ROA",      fontsize=9, color="#E85D24")
    ax0b.set_ylabel("Tobin Q", fontsize=9, color="#1D9E75")
    ax0.set_title("CSR Trade-off Curve", fontsize=10, fontweight="bold", pad=8)
    lines  = ax0.get_lines()  + ax0b.get_lines()
    labels = [l.get_label() for l in lines]
    ax0.legend(lines, labels, fontsize=7, loc="upper right")
    ax0.tick_params(labelsize=8)
    ax0b.tick_params(labelsize=8)

    # ── Panel 1: Current vs Optimal CSR bar ──────────────────────────────
    ax1 = fig.add_subplot(gs[0, 1])
    labels_bar = ["Current CSR", "Optimal CSR"]
    values_bar = [
        opt.get("current_csr") or 0,
        opt.get("optimal_csr") or 0,
    ]
    colors_bar = ["#B4B2A9", "#1D9E75"]
    bars = ax1.bar(labels_bar, values_bar, color=colors_bar, width=0.4, zorder=3)
    ax1.set_ylim(0, max(values_bar) * 1.4 if max(values_bar) > 0 else 1)
    for bar, val in zip(bars, values_bar):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                 f"{val:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    gap = opt.get("csr_gap") or 0
    direction = "↑ Increase" if gap > 0 else "↓ Decrease"
    ax1.set_title(
        f"Optimal CSR Level\n{direction} by {abs(gap):.3f} → Tobin Q gain: +{(opt.get('tobinq_gain') or 0):.4f}",
        fontsize=9, fontweight="bold", pad=8
    )
    ax1.set_ylabel("CSR Score", fontsize=9)
    ax1.tick_params(labelsize=8)
    ax1.yaxis.grid(True, alpha=0.3, zorder=0)
    ax1.set_axisbelow(True)

    # ── Panel 2: Top CSR drivers ──────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    if drv:
        feat_labels = [d["feature"] for d in drv[:6]]
        feat_vals   = [d["importance"] for d in drv[:6]]
        y_pos = range(len(feat_labels))
        palette = ["#534AB7" if v == max(feat_vals) else "#AFA9EC" for v in feat_vals]
        ax2.barh(list(y_pos), feat_vals, color=palette, zorder=3)
        ax2.set_yticks(list(y_pos))
        ax2.set_yticklabels(feat_labels, fontsize=9)
        ax2.set_xlabel("Importance Score", fontsize=9)
        ax2.set_title("Top Drivers of CSR", fontsize=10, fontweight="bold", pad=8)
        ax2.xaxis.grid(True, alpha=0.3, zorder=0)
        ax2.set_axisbelow(True)
        ax2.tick_params(labelsize=8)
        for i, v in enumerate(feat_vals):
            ax2.text(v + 0.002, i, f"{v:.3f}", va="center", fontsize=8)
    else:
        ax2.text(0.5, 0.5, "CSR driver data\nnot available",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=10)
        ax2.set_title("Top Drivers of CSR", fontsize=10, fontweight="bold")
        ax2.axis("off")

    # ── Panel 3: Decision summary text ───────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axis("off")
    ax3.set_facecolor("#F0EEF8")

    dsc     = findings.get("descriptive", {})
    pos_drv = [d["feature"] for d in findings.get("csr_direction", [])
               if d.get("significant") and d.get("coef", 0) > 0]
    neg_drv = [d["feature"] for d in findings.get("csr_direction", [])
               if d.get("significant") and d.get("coef", 0) < 0]

    summary_lines = [
        ("DECISION SUMMARY", 12, "bold", "#26215C"),
        ("", 9, "normal", "#000"),
        (f"Dataset:  {findings.get('dataset_name', 'N/A')}", 8, "normal", "#444"),
        (f"Mean CSR: {_fmt(dsc.get('csr_mean'),3)}   "
         f"Mean ROA: {_fmt(dsc.get('roa_mean'),4)}", 8, "normal", "#444"),
        (f"Mean Tobin Q: {_fmt(dsc.get('tobq_mean'),4)}", 8, "normal", "#444"),
        ("", 9, "normal", "#000"),
        ("CSR → ROA:    " + td.get("roa_direction","N/A").upper(), 9, "bold",
         "#E85D24" if td.get("roa_direction") == "negative" else "#1D9E75"),
        ("CSR → Tobin Q: " + td.get("tobq_direction","N/A").upper(), 9, "bold",
         "#1D9E75" if td.get("tobq_direction") == "positive" else "#E85D24"),
        ("", 9, "normal", "#000"),
        (f"RECOMMENDED ACTION:", 9, "bold", "#26215C"),
        (f"  {(opt.get('direction') or 'adjust').upper()} CSR from "
         f"{_fmt(opt.get('current_csr'),3)} → {_fmt(opt.get('optimal_csr'),3)}", 9, "normal", "#000"),
        ("", 9, "normal", "#000"),
        ("Increases CSR: " + (", ".join(pos_drv[:3]) or "N/A"), 8, "normal", "#1D9E75"),
        ("Decreases CSR: " + (", ".join(neg_drv[:3]) or "N/A"), 8, "normal", "#E85D24"),
        ("", 9, "normal", "#000"),
        (findings.get("vif_warning", ""), 7, "italic", "#888"),
        (findings.get("hausman", ""), 7, "italic", "#888"),
    ]
    y_start = 0.97
    for line, size, weight, color in summary_lines:
        ax3.text(0.05, y_start, line, transform=ax3.transAxes,
                 fontsize=size, fontweight=weight, color=color, va="top",
                 wrap=True)
        y_start -= (size / 80)

    ax3.set_title("Strategy Summary", fontsize=10, fontweight="bold", pad=8, color="#26215C")

    # ── Figure title ──────────────────────────────────────────────────────
    fig.suptitle(
        f"CSR Final Strategy Report  ·  {findings.get('dataset_name', '')}",
        fontsize=13, fontweight="bold", color="#26215C", y=1.01
    )

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — MAIN FUNCTION: generate_final_report()
#   Call this at the END of run_analysis() after all loops complete
# ═══════════════════════════════════════════════════════════════════════════

def generate_final_report(dataset, run_id: str) -> dict:
    """
    The orchestrator. Call this at the very end of run_analysis().
    
    Usage inside run_analysis(), just before the final return:
        report = generate_final_report(dataset, run_id)
    
    Returns the full findings dict (also saved to DB).
    """

    # 1. Collect all numbers from the run
    findings = collect_run_findings(dataset, run_id)

    # 2. Build Llama memo (with rule-based fallback)
    prompt = build_strategy_prompt(findings)
    ai_memo = llama_generate(prompt, max_tokens=900)

    # If Llama was unavailable, use rule-based memo
    if ai_memo.startswith("[Llama unavailable"):
        findings["llama_status"] = "offline_fallback"
        memo = build_rule_based_memo(findings)
    else:
        findings["llama_status"] = "online"
        memo = ai_memo

    findings["decision_memo"] = memo

    # 3. Generate the 4-panel strategy chart
    chart_buf = generate_strategy_chart(findings)

    # 4. Also generate the rule-based memo for comparison/export
    rule_memo = build_rule_based_memo(findings)
    findings["rule_based_memo"] = rule_memo

    # 5. Save as AnalysisResult type="STRATEGY"
    AnalysisResult.objects.update_or_create(
        run_id=run_id,
        result_type="STRATEGY",
        defaults={
            "dataset":      dataset,
            "result_json":  safe_json(findings),
            "summary_text": memo,
            "chart_file":   ContentFile(chart_buf.getvalue(), name="strategy_report.png"),
        }
    )

    # 6. Save to FinalStrategyReport (dedicated model, see models section)
    FinalStrategyReport.objects.update_or_create(
        dataset=dataset,
        run_id=run_id,
        defaults={
            "decision_memo":     memo,
            "rule_based_memo":   rule_memo,
            "findings_json":     safe_json(findings),
            "llama_status":      findings["llama_status"],
            "created_at":        timezone.now(),
        }
    )

    # 7. Save to AIRecommendation for audit trail
    AIRecommendation.objects.create(
        dataset=dataset,
        analysis_type="Final Strategy",
        recommendation_text=memo,
    )

    return findings


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — VIEW: /api/strategy/
# ═══════════════════════════════════════════════════════════════════════════

@csrf_exempt
def final_strategy_view(request):
    """
    GET /api/strategy/?run_id=xxx&dataset_id=yyy
    
    Returns the complete decision package as JSON.
    The front-end uses this to populate the Final Strategy dashboard tab.
    """
    run_id     = request.GET.get("run_id")
    dataset_id = request.GET.get("dataset_id")

    if not run_id:
        return JsonResponse({"error": "run_id required"}, status=400)

    # Try to load saved report
    try:
        report = FinalStrategyReport.objects.get(run_id=run_id)
        findings = report.findings_json
        memo     = report.decision_memo

    except FinalStrategyReport.DoesNotExist:
        # Regenerate on the fly if not saved yet
        try:
            dataset  = Dataset.objects.get(id=dataset_id)
            findings = generate_final_report(dataset, run_id)
            memo     = findings.get("decision_memo", "")
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # Pull the strategy chart URL
    strategy_result = AnalysisResult.objects.filter(
        run_id=run_id, result_type="STRATEGY"
    ).first()
    chart_url = (
        request.build_absolute_uri(strategy_result.chart_file.url)
        if strategy_result and strategy_result.chart_file
        else None
    )

    # Pull all per-analysis AI recommendations
    all_recommendations = []
    if dataset_id:
        all_recommendations = list(
            AIRecommendation.objects.filter(dataset_id=dataset_id)
            .order_by("created_at")
            .values("analysis_type", "recommendation_text", "created_at")
        )

    return JsonResponse({
        "run_id":             run_id,
        "dataset_name":       findings.get("dataset_name") if isinstance(findings, dict) else "",
        "analyses_run":       findings.get("analyses_run", []) if isinstance(findings, dict) else [],

        # ── The main deliverable: manager reads this ───────────────
        "decision_memo":      memo,

        # ── Key numbers for the dashboard cards ───────────────────
        "optimum":            findings.get("optimum", {}) if isinstance(findings, dict) else {},
        "tradeoff":           findings.get("tradeoff", {}) if isinstance(findings, dict) else {},
        "descriptive":        findings.get("descriptive", {}) if isinstance(findings, dict) else {},
        "csr_drivers":        findings.get("csr_drivers", []) if isinstance(findings, dict) else [],
        "csr_direction":      findings.get("csr_direction", []) if isinstance(findings, dict) else [],
        "ml_feature_importance": findings.get("ml_feature_importance", []) if isinstance(findings, dict) else [],
        "simulation":         findings.get("simulation", {}) if isinstance(findings, dict) else {},
        "vif_warning":        findings.get("vif_warning", "") if isinstance(findings, dict) else "",
        "hausman":            findings.get("hausman", "") if isinstance(findings, dict) else "",
        "llama_status":       findings.get("llama_status", "unknown") if isinstance(findings, dict) else "unknown",

        # ── Chart and recommendations ─────────────────────────────
        "strategy_chart_url": chart_url,
        "all_ai_recommendations": all_recommendations,
    })


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 — THE TWO LINES TO ADD AT END OF run_analysis()
# ═══════════════════════════════════════════════════════════════════════════

"""
PASTE THESE TWO LINES at the very end of run_analysis(), just before
the final JsonResponse return:

    # ── GENERATE FINAL STRATEGY REPORT ────────────────────────────────────
    from .final_strategy_views import generate_final_report   # if separate file
    generate_final_report(dataset, run_id)                    # ← add this line

    results = AnalysisResult.objects.filter(run_id=run_id)
    response = [ ... ]
    return JsonResponse({"status":"success","run_id":run_id,"results":response})
"""


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 — models.py: ADD FinalStrategyReport
# ═══════════════════════════════════════════════════════════════════════════

"""
Add to your models.py:

class FinalStrategyReport(models.Model):
    dataset         = models.ForeignKey(Dataset, on_delete=models.CASCADE,
                                         related_name="strategy_reports")
    run_id          = models.CharField(max_length=64, unique=True)
    decision_memo   = models.TextField()          # Llama-generated memo
    rule_based_memo = models.TextField(blank=True) # Fallback rule-based
    findings_json   = models.JSONField(default=dict)
    llama_status    = models.CharField(max_length=32, default="unknown")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Strategy {self.run_id[:8]} – {self.dataset}"


class AIRecommendation(models.Model):
    dataset              = models.ForeignKey(Dataset, on_delete=models.CASCADE,
                                              related_name="ai_recommendations")
    analysis_type        = models.CharField(max_length=100)
    recommendation_text  = models.TextField()
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
"""


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9 — urls.py: ADD ROUTE
# ═══════════════════════════════════════════════════════════════════════════

"""
Add to urlpatterns in urls.py:

    path("api/strategy/", final_strategy_view, name="final_strategy"),
"""