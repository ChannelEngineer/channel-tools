#!/usr/bin/env python3
"""
PRISM — Partner Risk & Intelligence Scoring Matrix
AI-powered churn prediction, growth forecasting, and intervention recommendations
for channel partner ecosystems.

Usage:
    prism.py demo                         Load sample partners and run full analysis
    prism.py partner add ...              Add/update partner engagement data
    prism.py partner list                 List all partners
    prism.py partner show <name>          Show detailed partner analysis
    prism.py analyze partner <name>       Run churn/growth analysis for one partner
    prism.py analyze portfolio            Run portfolio-level risk analysis
    prism.py recommend <name>             Get intervention recommendations for partner
    prism.py heatmap                      Show portfolio risk heatmap
    prism.py intervene <name> --playbook  Apply an intervention playbook (logs it)
    prism.py dashboard                    Portfolio executive summary
    prism.py serve                        Start as MCP server for AI agent integration
"""

import argparse
import json
import math
import os
import random
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".prism"
PARTNERS_FILE = DATA_DIR / "partners.json"
ANALYSIS_FILE = DATA_DIR / "analysis.json"
INTERVENTIONS_FILE = DATA_DIR / "interventions.json"
HEATMAP_FILE = DATA_DIR / "heatmap.json"

# ── Scoring Weights ─────────────────────────────────────────────────────────
# These weights define how each signal contributes to churn risk and growth readiness

CHURN_WEIGHTS = {
    "days_since_last_deal": 0.20,        # Longer gap = higher churn risk
    "deal_count_trend": 0.15,            # Decreasing deal count = risk
    "portal_login_frequency": 0.12,       # Low login frequency = disengagement
    "mdf_utilization_trend": 0.10,        # Dropping MDF use = less investment
    "training_recency": 0.10,             # No recent training = disengagement
    "certification_status": 0.08,         # Expired certs = risk
    "support_ticket_trend": 0.08,         # Increasing support tickets = frustration
    "pipeline_velocity": 0.07,            # Slowing pipeline = risk
    "email_engagement_rate": 0.05,        # Unengaged with communications
    "program_compliance_score": 0.05,     # Low compliance = risk indicator
}

GROWTH_WEIGHTS = {
    "revenue_growth_rate": 0.25,          # YoY or QoQ revenue growth
    "deal_size_trend": 0.15,              # Increasing deal sizes
    "new_logo_acquisition_rate": 0.15,    # Winning new customers
    "certification_advancement": 0.12,    # Pursuing higher certifications
    "training_completion_rate": 0.10,     # Completing available training
    "mdf_effectiveness": 0.08,            # ROI from MDF investments
    "co_sell_participation": 0.08,        # Engaging in co-sell opportunities
    "portal_feature_adoption": 0.07,      # Using advanced portal features
}

# ── Risk Thresholds ─────────────────────────────────────────────────────────
RISK_LEVELS = {
    "critical": {"min": 75, "label": "🔴 Critical", "action": "Immediate intervention required"},
    "high": {"min": 55, "label": "🟠 High", "action": "Proactive outreach this week"},
    "moderate": {"min": 35, "label": "🟡 Moderate", "action": "Monitor closely, plan engagement"},
    "low": {"min": 15, "label": "🟢 Low", "action": "Standard engagement cadence"},
    "minimal": {"min": 0, "label": "⚪ Minimal", "action": "Continue current approach"},
}

GROWTH_LEVELS = {
    "high": {"min": 70, "label": "🌟 High Growth", "action": "Invest more resources"},
    "moderate": {"min": 40, "label": "📈 Moderate Growth", "action": "Nurture with targeted enablement"},
    "low": {"min": 0, "label": "📊 Low Growth", "action": "Focus on retention basics"},
}

# ── Intervention Playbooks ──────────────────────────────────────────────────
PLAYBOOKS = {
    "critical_reengagement": {
        "name": "Critical Re-Engagement Sprint",
        "trigger": "critical",
        "steps": [
            "Schedule executive-to-executive call within 48 hours",
            "Offer custom SPIFF for next deal registered",
            "Assign dedicated channel support contact for 30 days",
            "Review and adjust MDF budget — offer 60-day use-it-or-lose-it incentive",
            "Provide free certification training vouchers",
            "Create joint business plan with 90-day milestones",
        ],
        "expected_time_to_impact_days": 14,
    },
    "high_risk_retention": {
        "name": "High-Risk Retention Program",
        "trigger": "high",
        "steps": [
            "Channel manager personal outreach within 5 business days",
            "Send tailored enablement content based on past interests",
            "Offer 90-day accelerated deal registration margin bump (+5%)",
            "Invite to upcoming partner advisory council or exclusive event",
            "Conduct partner health check call with structured agenda",
        ],
        "expected_time_to_impact_days": 30,
    },
    "moderate_engagement_boost": {
        "name": "Moderate Engagement Boost",
        "trigger": "moderate",
        "steps": [
            "Automated personalized email sequence (3-touch over 2 weeks)",
            "Highlight relevant training paths and certification goals",
            "Share top-performing partner success stories",
            "Invite to monthly partner webcast / product update session",
        ],
        "expected_time_to_impact_days": 45,
    },
    "growth_acceleration": {
        "name": "Growth Acceleration Playbook",
        "trigger_growth": "low",
        "steps": [
            "Offer MDF matching (vendor matches 50% of partner investment)",
            "Connect with high-performing partner mentor",
            "Co-create case study with joint customer success story",
            "Invite to quarterly planning session with channel leadership",
            "Provide advanced sales certification track",
        ],
        "expected_time_to_impact_days": 60,
    },
    "high_growth_investment": {
        "name": "High Growth Investment Playbook",
        "trigger_growth": "high",
        "steps": [
            "Propose tier promotion with enhanced benefits package",
            "Increase lead allocation ratio",
            "Offer preferred pricing for expansion deals",
            "Feature in partner locator as 'top recommended'",
            "Co-present at industry event / tradeshow",
        ],
        "expected_time_to_impact_days": 90,
    },
}

# ── Data Store Helpers ──────────────────────────────────────────────────────


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path, default=None):
    if default is None:
        default = []
    if not path.exists():
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def _save_json(path, data):
    _ensure_data_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _get_timestamp():
    return datetime.now().isoformat()


def _days_ago(days):
    return (datetime.now() - timedelta(days=days)).isoformat()


# ── Partner CRUD ────────────────────────────────────────────────────────────


def _all_partners():
    return _load_json(PARTNERS_FILE, {})


def _save_partners(partners):
    _save_json(PARTNERS_FILE, partners)


def _get_partner(name):
    partners = _all_partners()
    return partners.get(name)


def _add_or_update_partner(name, data):
    partners = _all_partners()
    partners[name] = {**partners.get(name, {}), **data, "name": name, "updated_at": _get_timestamp()}
    if "created_at" not in partners[name]:
        partners[name]["created_at"] = _get_timestamp()
    _save_partners(partners)
    return partners[name]


# ── Scoring Engine ──────────────────────────────────────────────────────────


def _normalize(value, min_val, max_val, invert=False):
    """Normalize a value to 0-100 range. If invert=True, higher raw = lower score."""
    if max_val == min_val:
        return 50.0
    raw = max(0, min(100, (value - min_val) / (max_val - min_val) * 100))
    return 100 - raw if invert else raw


def _score_churn_risk(partner):
    """Compute churn risk score (0-100) from partner engagement signals."""
    s = partner

    # 1. Days since last deal
    dsl = s.get("days_since_last_deal", 90)
    score_dsl = _normalize(dsl, 0, 365, invert=False)  # More days = higher risk
    # Cap extreme values: >365 days = 100 risk
    if dsl > 365:
        score_dsl = 100

    # 2. Deal count trend (negative = decreasing)
    deal_trend = s.get("deal_count_trend_pct", 0)
    score_trend = _normalize(abs(min(deal_trend, 0)), 0, 100, invert=False) if deal_trend < 0 else 10

    # 3. Portal login frequency (logins per month)
    logins = s.get("monthly_portal_logins", 2)
    score_logins = _normalize(max(0, 8 - logins), 0, 8, invert=False)

    # 4. MDF utilization trend (% of budget used, dropping = bad)
    mdf_trend = s.get("mdf_utilization_pct", 0)
    score_mdf = _normalize(max(0, 70 - mdf_trend), 0, 70, invert=False)

    # 5. Training recency (months since last training)
    training_months = s.get("months_since_last_training", 12)
    score_training = _normalize(training_months, 0, 24, invert=False)

    # 6. Certification status (0 = none, 1 = basic, 2 = advanced)
    cert_level = s.get("certification_level", 0)
    score_cert = _normalize(2 - cert_level, 0, 2, invert=False)

    # 7. Support ticket trend
    ticket_count = s.get("monthly_support_tickets", 0)
    score_tickets = _normalize(ticket_count, 0, 10, invert=False)

    # 8. Pipeline velocity (deals added per quarter)
    pipeline = s.get("pipeline_deals_per_quarter", 0)
    score_pipeline = _normalize(max(0, 5 - pipeline), 0, 5, invert=False)

    # 9. Email engagement (open rate %)
    email_engagement = s.get("email_open_rate_pct", 30)
    score_email = _normalize(max(0, 50 - email_engagement), 0, 50, invert=False)

    # 10. Compliance score
    compliance = s.get("program_compliance_pct", 80)
    score_compliance = _normalize(max(0, 100 - compliance), 0, 100, invert=False)

    signals = {
        "days_since_last_deal": round(score_dsl, 1),
        "deal_count_trend": round(score_trend, 1),
        "portal_login_frequency": round(score_logins, 1),
        "mdf_utilization_trend": round(score_mdf, 1),
        "training_recency": round(score_training, 1),
        "certification_status": round(score_cert, 1),
        "support_ticket_trend": round(score_tickets, 1),
        "pipeline_velocity": round(score_pipeline, 1),
        "email_engagement_rate": round(score_email, 1),
        "program_compliance_score": round(score_compliance, 1),
    }

    weighted_sum = sum(
        signals[k] * CHURN_WEIGHTS[k] for k in CHURN_WEIGHTS if k in signals
    )

    final_score = round(min(100, max(0, weighted_sum)), 1)

    # Determine risk level
    for level, info in RISK_LEVELS.items():
        if final_score >= info["min"]:
            risk_level = level
            risk_label = info["label"]
            risk_action = info["action"]
            break

    return {
        "churn_risk_score": final_score,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "risk_action": risk_action,
        "churn_signal_breakdown": signals,
        "analyzed_at": _get_timestamp(),
    }


def _score_growth_readiness(partner):
    """Compute growth readiness score (0-100) from partner growth signals."""
    s = partner

    # 1. Revenue growth rate (YoY %)
    rev_growth = s.get("revenue_growth_pct", 0)
    score_rev = _normalize(rev_growth, 0, 200, invert=False)

    # 2. Deal size trend
    deal_size_trend = s.get("deal_size_trend_pct", 0)
    score_deal_size = _normalize(deal_size_trend, 0, 100, invert=False)

    # 3. New logo acquisition rate (per quarter)
    new_logos = s.get("new_logos_per_quarter", 0)
    score_logos = _normalize(new_logos, 0, 5, invert=False)

    # 4. Certification advancement (0=none, 1=basic, 2=advanced)
    cert_level = s.get("certification_level", 0)
    score_cert_adv = _normalize(cert_level, 0, 2, invert=False) * 2  # Scale

    # 5. Training completion rate (%)
    training_complete = s.get("training_completion_pct", 50)
    score_training = _normalize(training_complete, 0, 100, invert=False)

    # 6. MDF effectiveness (ROI from MDF, e.g. 2.5x)
    mdf_roi = s.get("mdf_roi_multiplier", 0)
    score_mdf_eff = _normalize(mdf_roi, 0, 10, invert=False)

    # 7. Co-sell participation (deals this year)
    co_sell = s.get("co_sell_deals_this_year", 0)
    score_co_sell = _normalize(co_sell, 0, 8, invert=False)

    # 8. Portal feature adoption (features used out of 10)
    feature_adoption = s.get("portal_feature_adoption_count", 3)
    score_feature = _normalize(feature_adoption, 0, 10, invert=False)

    signals = {
        "revenue_growth_rate": round(score_rev, 1),
        "deal_size_trend": round(score_deal_size, 1),
        "new_logo_acquisition_rate": round(score_logos, 1),
        "certification_advancement": round(min(100, score_cert_adv), 1),
        "training_completion_rate": round(score_training, 1),
        "mdf_effectiveness": round(score_mdf_eff, 1),
        "co_sell_participation": round(score_co_sell, 1),
        "portal_feature_adoption": round(score_feature, 1),
    }

    weighted_sum = sum(
        signals[k] * GROWTH_WEIGHTS[k] for k in GROWTH_WEIGHTS if k in signals
    )

    final_score = round(min(100, max(0, weighted_sum)), 1)

    for level, info in GROWTH_LEVELS.items():
        if final_score >= info["min"]:
            growth_level = level
            growth_label = info["label"]
            growth_action = info["action"]
            break

    return {
        "growth_readiness_score": final_score,
        "growth_level": growth_level,
        "growth_label": growth_label,
        "growth_action": growth_action,
        "growth_signal_breakdown": signals,
        "analyzed_at": _get_timestamp(),
    }


def _get_recommendations(partner, churn_result, growth_result):
    """Generate specific intervention recommendations based on analysis."""
    recs = []
    risk = churn_result["risk_level"]
    growth = growth_result["growth_level"]

    # Risk-based playbooks
    if risk == "critical":
        recs.append({**PLAYBOOKS["critical_reengagement"], "type": "churn"})
    elif risk == "high":
        recs.append({**PLAYBOOKS["high_risk_retention"], "type": "churn"})
    elif risk == "moderate":
        recs.append({**PLAYBOOKS["moderate_engagement_boost"], "type": "churn"})
    elif risk == "low" and growth == "low":
        recs.append({**PLAYBOOKS["growth_acceleration"], "type": "growth"})

    # Growth-based playbooks
    if growth == "high" and risk in ("low", "minimal"):
        recs.append({**PLAYBOOKS["high_growth_investment"], "type": "growth"})
    elif growth == "low" and risk in ("low", "minimal"):
        recs.append({**PLAYBOOKS["growth_acceleration"], "type": "growth"})

    # Signal-level quick wins
    signals = churn_result["churn_signal_breakdown"]
    for signal, score in signals.items():
        if score >= 60:
            quick_win = _quick_win_for_signal(signal, partner)
            if quick_win:
                recs.append({"type": "quick_win", "signal": signal, "suggestion": quick_win})

    return recs


def _quick_win_for_signal(signal, partner):
    """Suggest quick actions for high-risk signals."""
    tips = {
        "days_since_last_deal": "Set up a deal registration incentive (SPIFF) to restart deal flow",
        "portal_login_frequency": "Send a 'What's New in the Portal' email with direct login link",
        "training_recency": "Offer a free certification voucher — training drives engagement",
        "certification_status": "Connect partner with a certification mentor and waive exam fees",
        "pipeline_velocity": "Co-host a pipeline generation workshop with this partner",
        "email_engagement_rate": "Segment this partner into a re-engagement drip campaign",
        "program_compliance_score": "Schedule a compliance review call — identify specific gaps",
        "mdf_utilization_trend": "Offer a 60-day use-it-or-lose-it MDF incentive",
    }
    return tips.get(signal)


# ── Analysis Engine ─────────────────────────────────────────────────────────


def analyze_partner(partner):
    """Full analysis: churn risk + growth readiness + recommendations."""
    churn = _score_churn_risk(partner)
    growth = _score_growth_readiness(partner)
    recs = _get_recommendations(partner, churn, growth)
    return {"partner": partner["name"], **churn, **growth, "recommendations": recs}


def _ranked_portfolio():
    """Analyze all partners and return ranked by urgency."""
    partners = _all_partners()
    if not partners:
        return {"error": "No partners found. Add partners or run `prism.py demo`."}

    results = []
    for name, partner in partners.items():
        analysis = analyze_partner(partner)
        results.append(analysis)

    # Sort by churn risk descending (most at risk first)
    results.sort(key=lambda r: r["churn_risk_score"], reverse=True)

    return results


def _portfolio_summary(results):
    """Compute portfolio-level metrics."""
    total = len(results)
    if total == 0:
        return {"error": "No partners in portfolio"}

    by_risk = {}
    by_growth = {}
    total_revenue = 0
    at_risk_revenue = 0

    for r in results:
        level = r["risk_level"]
        by_risk[level] = by_risk.get(level, 0) + 1
        g_level = r["growth_level"]
        by_growth[g_level] = by_growth.get(g_level, 0) + 1

        # Revenue info from partner data
        partner = _get_partner(r["partner"])
        if partner:
            rev = partner.get("annual_revenue", 0)
            total_revenue += rev
            if level in ("critical", "high"):
                at_risk_revenue += rev

    return {
        "total_partners": total,
        "risk_distribution": by_risk,
        "growth_distribution": by_growth,
        "total_portfolio_revenue": total_revenue,
        "revenue_at_risk": at_risk_revenue,
        "revenue_at_risk_pct": round(at_risk_revenue / total_revenue * 100, 1) if total_revenue > 0 else 0,
        "analyzed_at": _get_timestamp(),
    }


# ── Sample Data ──────────────────────────────────────────────────────────────


SAMPLE_PARTNERS = {
    "TechSolvers Inc": {
        "tier": "platinum",
        "region": "West",
        "annual_revenue": 850000,
        "days_since_last_deal": 12,
        "deal_count_trend_pct": 15,
        "monthly_portal_logins": 22,
        "mdf_utilization_pct": 65,
        "months_since_last_training": 1,
        "certification_level": 2,
        "monthly_support_tickets": 1,
        "pipeline_deals_per_quarter": 8,
        "email_open_rate_pct": 68,
        "program_compliance_pct": 95,
        "revenue_growth_pct": 35,
        "deal_size_trend_pct": 12,
        "new_logos_per_quarter": 3,
        "training_completion_pct": 90,
        "mdf_roi_multiplier": 4.2,
        "co_sell_deals_this_year": 5,
        "portal_feature_adoption_count": 8,
    },
    "DataBridge Partners": {
        "tier": "gold",
        "region": "Northeast",
        "annual_revenue": 420000,
        "days_since_last_deal": 45,
        "deal_count_trend_pct": -8,
        "monthly_portal_logins": 8,
        "mdf_utilization_pct": 40,
        "months_since_last_training": 4,
        "certification_level": 1,
        "monthly_support_tickets": 2,
        "pipeline_deals_per_quarter": 3,
        "email_open_rate_pct": 42,
        "program_compliance_pct": 72,
        "revenue_growth_pct": 12,
        "deal_size_trend_pct": 5,
        "new_logos_per_quarter": 1,
        "training_completion_pct": 60,
        "mdf_roi_multiplier": 2.1,
        "co_sell_deals_this_year": 1,
        "portal_feature_adoption_count": 5,
    },
    "CloudSync Networks": {
        "tier": "gold",
        "region": "Southeast",
        "annual_revenue": 310000,
        "days_since_last_deal": 90,
        "deal_count_trend_pct": -25,
        "monthly_portal_logins": 3,
        "mdf_utilization_pct": 15,
        "months_since_last_training": 8,
        "certification_level": 1,
        "monthly_support_tickets": 5,
        "pipeline_deals_per_quarter": 1,
        "email_open_rate_pct": 18,
        "program_compliance_pct": 55,
        "revenue_growth_pct": -8,
        "deal_size_trend_pct": -10,
        "new_logos_per_quarter": 0,
        "training_completion_pct": 25,
        "mdf_roi_multiplier": 0.8,
        "co_sell_deals_this_year": 0,
        "portal_feature_adoption_count": 2,
    },
    "EnterpriseOps Group": {
        "tier": "platinum",
        "region": "Midwest",
        "annual_revenue": 1200000,
        "days_since_last_deal": 8,
        "deal_count_trend_pct": 22,
        "monthly_portal_logins": 30,
        "mdf_utilization_pct": 80,
        "months_since_last_training": 2,
        "certification_level": 2,
        "monthly_support_tickets": 0,
        "pipeline_deals_per_quarter": 12,
        "email_open_rate_pct": 82,
        "program_compliance_pct": 100,
        "revenue_growth_pct": 48,
        "deal_size_trend_pct": 20,
        "new_logos_per_quarter": 4,
        "training_completion_pct": 95,
        "mdf_roi_multiplier": 6.5,
        "co_sell_deals_this_year": 8,
        "portal_feature_adoption_count": 10,
    },
    "NorthStar Solutions": {
        "tier": "authorized",
        "region": "Southwest",
        "annual_revenue": 95000,
        "days_since_last_deal": 180,
        "deal_count_trend_pct": -50,
        "monthly_portal_logins": 1,
        "mdf_utilization_pct": 5,
        "months_since_last_training": 18,
        "certification_level": 0,
        "monthly_support_tickets": 3,
        "pipeline_deals_per_quarter": 0,
        "email_open_rate_pct": 8,
        "program_compliance_pct": 30,
        "revenue_growth_pct": -25,
        "deal_size_trend_pct": -15,
        "new_logos_per_quarter": 0,
        "training_completion_pct": 10,
        "mdf_roi_multiplier": 0.0,
        "co_sell_deals_this_year": 0,
        "portal_feature_adoption_count": 1,
    },
    "Summit Global": {
        "tier": "gold",
        "region": "Pacific Northwest",
        "annual_revenue": 520000,
        "days_since_last_deal": 30,
        "deal_count_trend_pct": 5,
        "monthly_portal_logins": 12,
        "mdf_utilization_pct": 50,
        "months_since_last_training": 3,
        "certification_level": 1,
        "monthly_support_tickets": 2,
        "pipeline_deals_per_quarter": 4,
        "email_open_rate_pct": 55,
        "program_compliance_pct": 80,
        "revenue_growth_pct": 18,
        "deal_size_trend_pct": 8,
        "new_logos_per_quarter": 2,
        "training_completion_pct": 70,
        "mdf_roi_multiplier": 3.0,
        "co_sell_deals_this_year": 3,
        "portal_feature_adoption_count": 6,
    },
}


def _load_demo_data():
    """Load 6 sample partners with varying risk/growth profiles."""
    partners = _all_partners()
    for name, data in SAMPLE_PARTNERS.items():
        if name not in partners:
            data["created_at"] = _get_timestamp()
            data["updated_at"] = _get_timestamp()
            data["name"] = name
            partners[name] = data
    _save_partners(partners)
    return len(partners)


# ── CLI Formatting ──────────────────────────────────────────────────────────


def _fmt_partner_table(partners):
    lines = []
    lines.append(f"{'Partner':<22} {'Tier':<12} {'Risk Score':<12} {'Risk Level':<14} {'Growth':<14} {'Action':<32}")
    lines.append("-" * 106)
    for p in partners:
        name = p["partner"]
        partner_data = _get_partner(name) or {}
        tier = partner_data.get("tier", "?")
        risk = f"{p['churn_risk_score']:.0f}"
        risk_lbl = p["risk_label"]
        growth_lbl = p["growth_label"]
        # Pick the first recommendation or the risk action
        recs = p.get("recommendations", [])
        action = recs[0].get("name", p.get("risk_action", "")) if recs else p.get("risk_action", "")
        if len(action) > 30:
            action = action[:29] + "…"
        lines.append(f"{name:<22} {tier:<12} {risk:<12} {risk_lbl:<14} {growth_lbl:<14} {action:<32}")
    return "\n".join(lines)


def _fmt_signal_table(signals):
    lines = []
    lines.append(f"{'Signal':<30} {'Score':<8} {'Weight':<8} {'Contribution':<12}")
    lines.append("-" * 58)
    for signal, score in sorted(signals.items(), key=lambda x: x[1], reverse=True):
        weight = CHURN_WEIGHTS.get(signal, 0)
        contrib = score * weight
        lines.append(f"{signal:<30} {score:<8.1f} {weight:<8.2f} {contrib:<12.1f}")
    return "\n".join(lines)


def _fmt_growth_table(signals):
    lines = []
    lines.append(f"{'Signal':<30} {'Score':<8} {'Weight':<8} {'Contribution':<12}")
    lines.append("-" * 58)
    for signal, score in sorted(signals.items(), key=lambda x: x[1], reverse=True):
        weight = GROWTH_WEIGHTS.get(signal, 0)
        contrib = score * weight
        lines.append(f"{signal:<30} {score:<8.1f} {weight:<8.2f} {contrib:<12.1f}")
    return "\n".join(lines)


def _fmt_heatmap(ranked):
    """Color-coded ASCII heatmap of portfolio risk."""
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║               PRISM Portfolio Risk Heatmap                  ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")

    # Header
    lines.append(f"{'Partner':<22} {'Tier':<10} {'Risk':<7} {'Growth':<8} {'Revenue':<12} {'Bar':<32}")
    lines.append("-" * 91)

    for p in ranked:
        name = p["partner"]
        partner_data = _get_partner(name) or {}
        tier = partner_data.get("tier", "?")
        risk = p["churn_risk_score"]
        growth = p["growth_readiness_score"]
        rev = partner_data.get("annual_revenue", 0)

        # Color bar: risk in red intensity, growth in green
        risk_bar_len = int(risk / 100 * 15)
        growth_bar_len = int(growth / 100 * 15)
        risk_bar = "█" * risk_bar_len + "░" * (15 - risk_bar_len)
        growth_bar = "█" * growth_bar_len + "░" * (15 - growth_bar_len)

        rev_str = f"${rev:,.0f}"
        lines.append(f"{name:<22} {tier:<10} {risk:<5.0f}  {growth:<5.0f}  {rev_str:<10}  ⚠{risk_bar} 🌱{growth_bar}")

    lines.append("")
    lines.append("  ⚠ Risk bar (left)  — ██ = higher churn risk")
    lines.append("  🌱 Growth bar (right) — ██ = higher growth readiness")
    return "\n".join(lines)


def _fmt_recommendations(recs):
    lines = []
    for i, rec in enumerate(recs, 1):
        lines.append(f"\n  {'─' * 40}")
        lines.append(f"  Playbook {i}: {rec.get('name', rec.get('suggestion', 'Quick Win'))}")
        lines.append(f"  Type: {rec.get('type', 'general').upper()}")
        if "trigger" in rec:
            lines.append(f"  Trigger: {rec['trigger']}")
        if "expected_time_to_impact_days" in rec:
            lines.append(f"  Expected impact: {rec['expected_time_to_impact_days']} days")
        if "steps" in rec:
            for step in rec["steps"]:
                lines.append(f"    • {step}")
        else:
            lines.append(f"    → {rec.get('suggestion', '')}")
    return "\n".join(lines)


# ── CLI Commands ────────────────────────────────────────────────────────────


def cmd_demo():
    count = _load_demo_data()
    print(f"✅ Loaded {count} sample partners with varying risk profiles.")
    print()
    results = _ranked_portfolio()
    print(_fmt_partner_table(results))
    print()
    summary = _portfolio_summary(results)
    print(f"\n📊 Portfolio Summary: {summary['total_partners']} partners | "
          f"${summary['total_portfolio_revenue']:,.0f} total revenue | "
          f"${summary['revenue_at_risk']:,.0f} at risk ({summary['revenue_at_risk_pct']}%)")


def cmd_partner_add(args):
    name = args.name
    data = {k: v for k, v in vars(args).items() if v is not None and k != "name" and k != "func"}
    data = {k: v for k, v in data.items() if k != "command"}
    partner = _add_or_update_partner(name, data)
    print(f"✅ Partner '{name}' saved.")
    if args.analyze:
        print()
        cmd_analyze_partner(name)


def cmd_partner_list():
    partners = _all_partners()
    if not partners:
        print("No partners. Run `prism.py demo` or `prism.py partner add ...`")
        return
    print(f"{'Name':<22} {'Tier':<12} {'Revenue':<14} {'Region':<18} {'Last Deal':<12} {'Logins/mo':<10}")
    print("-" * 88)
    for name, p in sorted(partners.items()):
        rev = p.get("annual_revenue", 0)
        last_deal = p.get("days_since_last_deal", "?")
        logins = p.get("monthly_portal_logins", "?")
        print(f"{name:<22} {p.get('tier','?'):<12} ${rev:<10,.0f} {p.get('region','?'):<18} {str(last_deal):<12} {str(logins):<10}")


def cmd_partner_show(args):
    partner = _get_partner(args.name)
    if not partner:
        print(f"❌ Partner '{args.name}' not found.")
        return
    analysis = analyze_partner(partner)
    print(f"\n{'═' * 60}")
    print(f"  PRISM Analysis — {analysis['partner']}")
    print(f"{'═' * 60}")
    print(f"  Churn Risk:      {analysis['risk_label']} ({analysis['churn_risk_score']}/100)")
    print(f"  Growth Readiness: {analysis['growth_label']} ({analysis['growth_readiness_score']}/100)")
    print(f"  Tier:            {partner.get('tier', '?')}  |  Region: {partner.get('region', '?')}")
    print(f"  Annual Revenue:  ${partner.get('annual_revenue', 0):,.0f}")
    print()
    print(f"  {analysis['risk_action']}")
    print(f"  {analysis['growth_action']}")
    print()
    print("  Churn Signal Breakdown:")
    print(_fmt_signal_table(analysis["churn_signal_breakdown"]))
    print()
    print("  Growth Signal Breakdown:")
    print(_fmt_growth_table(analysis["growth_signal_breakdown"]))
    print()
    if analysis.get("recommendations"):
        print("  Recommended Interventions:")
        print(_fmt_recommendations(analysis["recommendations"]))


def cmd_analyze(args):
    if args.target == "portfolio":
        cmd_analyze_portfolio()
    else:
        cmd_analyze_partner(args.target)


def cmd_analyze_partner(name):
    partner = _get_partner(name)
    if not partner:
        print(f"❌ Partner '{name}' not found.")
        return
    analysis = analyze_partner(partner)
    print(json.dumps(analysis, indent=2))


def cmd_analyze_portfolio():
    results = _ranked_portfolio()
    if isinstance(results, dict) and "error" in results:
        print(results["error"])
        return
    print(_fmt_partner_table(results))
    print()
    summary = _portfolio_summary(results)
    print(f"📊 Portfolio Summary: {summary['total_partners']} partners | "
          f"${summary['total_portfolio_revenue']:,.0f} total revenue | "
          f"${summary['revenue_at_risk']:,.0f} at risk ({summary['revenue_at_risk_pct']}%)")


def cmd_recommend(args):
    partner = _get_partner(args.name)
    if not partner:
        print(f"❌ Partner '{args.name}' not found.")
        return
    churn = _score_churn_risk(partner)
    growth = _score_growth_readiness(partner)
    recs = _get_recommendations(partner, churn, growth)
    print(f"\n{'─' * 50}")
    print(f"  Recommendations for: {args.name}")
    print(f"  Risk Level: {churn['risk_label']}  |  Growth: {growth['growth_label']}")
    print(f"{'─' * 50}")
    if recs:
        print(_fmt_recommendations(recs))
    else:
        print("  ✅ Partner is in good standing. No urgent interventions needed.")
        print("  Continue standard engagement cadence.")


def cmd_heatmap():
    results = _ranked_portfolio()
    if isinstance(results, dict) and "error" in results:
        print(results["error"])
        return
    print(_fmt_heatmap(results))
    print()
    summary = _portfolio_summary(results)
    print(f"📊 At-risk revenue: ${summary['revenue_at_risk']:,.0f} "
          f"({summary['revenue_at_risk_pct']}% of portfolio)")


def cmd_intervene(args):
    partner = _get_partner(args.name)
    if not partner:
        print(f"❌ Partner '{args.name}' not found.")
        return

    interventions = _load_json(INTERVENTIONS_FILE, [])
    intervention = {
        "id": str(uuid.uuid4())[:8],
        "partner": args.name,
        "playbook": args.playbook,
        "applied_at": _get_timestamp(),
        "status": "active",
        "notes": args.notes or "",
    }
    interventions.append(intervention)
    _save_json(INTERVENTIONS_FILE, interventions)

    print(f"✅ Intervention logged: {intervention['playbook']} for {args.name}")
    print(f"   ID: {intervention['id']} | Status: active")

    # Show the playbook steps
    for pb_name, pb in PLAYBOOKS.items():
        if pb["name"] == args.playbook or pb_name == args.playbook:
            print(f"\n   Steps for '{pb['name']}':")
            for step in pb["steps"]:
                print(f"     • {step}")
            print(f"   Expected impact: {pb.get('expected_time_to_impact_days', '?')} days")
            break


def cmd_dashboard():
    results = _ranked_portfolio()
    if isinstance(results, dict) and "error" in results:
        print(results["error"])
        return
    summary = _portfolio_summary(results)

    print(f"\n{'═' * 60}")
    print(f"  PRISM Portfolio Dashboard")
    print(f"  {datetime.now().strftime('%B %d, %Y — %I:%M %p')}")
    print(f"{'═' * 60}")

    print(f"\n  Partners: {summary['total_partners']}")
    print(f"  Portfolio Revenue: ${summary['total_portfolio_revenue']:,.0f}")
    print(f"  Revenue at Risk:   ${summary['revenue_at_risk']:,.0f} ({summary['revenue_at_risk_pct']}%)")
    print()
    print("  Risk Distribution:")
    for level in ["critical", "high", "moderate", "low", "minimal"]:
        count = summary["risk_distribution"].get(level, 0)
        label = RISK_LEVELS[level]["label"]
        bar = "█" * count + "░" * max(0, 10 - count)
        print(f"    {label:<18} {count:>2}  {bar}")
    print()
    print("  Growth Distribution:")
    for level in ["high", "moderate", "low"]:
        count = summary["growth_distribution"].get(level, 0)
        label = GROWTH_LEVELS[level]["label"]
        bar = "█" * count + "░" * max(0, 10 - count)
        print(f"    {label:<18} {count:>2}  {bar}")
    print()
    print("  Top 3 Partners at Risk:")
    for p in results[:3]:
        partner = _get_partner(p["partner"])
        rev = partner.get("annual_revenue", 0) if partner else 0
        print(f"    {p['risk_label']:<6} {p['partner']:<22} "
              f"Score: {p['churn_risk_score']:.0f} | Rev: ${rev:,.0f}")
    print()


# ── MCP Server Mode ─────────────────────────────────────────────────────────


def cmd_serve():
    """Start PRISM as an MCP server for AI agent integration."""
    try:
        from mcp.server import Server, NotificationOptions
        from mcp.server.models import InitializationOptions
        import mcp.server.stdio
        import mcp.types as types
    except ImportError:
        print("❌ MCP package required. Install with: pip install mcp")
        sys.exit(1)

    server = Server("prism")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="add_partner_data",
                description="Add or update partner engagement data for churn/growth analysis",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Partner company name"},
                        "tier": {"type": "string", "enum": ["authorized", "gold", "platinum"]},
                        "annual_revenue": {"type": "number"},
                        "days_since_last_deal": {"type": "integer"},
                        "deal_count_trend_pct": {"type": "number"},
                        "monthly_portal_logins": {"type": "integer"},
                        "mdf_utilization_pct": {"type": "number"},
                        "months_since_last_training": {"type": "integer"},
                        "certification_level": {"type": "integer", "description": "0=none, 1=basic, 2=advanced"},
                        "pipeline_deals_per_quarter": {"type": "integer"},
                        "email_open_rate_pct": {"type": "number"},
                        "program_compliance_pct": {"type": "number"},
                        "revenue_growth_pct": {"type": "number"},
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="analyze_partner_churn",
                description="Run churn risk + growth readiness analysis on a partner",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Partner company name"},
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="analyze_portfolio",
                description="Run full portfolio risk analysis across all partners",
                inputSchema={
                    "type": "object",
                    "properties": {"": {"type": "string"}},
                },
            ),
            types.Tool(
                name="get_recommendations",
                description="Get intervention recommendations for a specific partner",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Partner company name"},
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="get_portfolio_heatmap",
                description="Get portfolio risk heatmap showing all partners ranked by churn risk",
                inputSchema={
                    "type": "object",
                    "properties": {"": {"type": "string"}},
                },
            ),
            types.Tool(
                name="get_portfolio_dashboard",
                description="Get portfolio-level executive summary with risk/growth distribution",
                inputSchema={
                    "type": "object",
                    "properties": {"": {"type": "string"}},
                },
            ),
            types.Tool(
                name="log_intervention",
                description="Log that an intervention playbook was applied to a partner",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Partner company name"},
                        "playbook": {"type": "string", "description": "Playbook name (e.g. 'Critical Re-Engagement Sprint', 'High-Risk Retention Program')"},
                        "notes": {"type": "string", "description": "Optional notes about the intervention"},
                    },
                    "required": ["name", "playbook"],
                },
            ),
            types.Tool(
                name="load_demo_data",
                description="Load 6 sample partners with varying risk profiles for testing",
                inputSchema={
                    "type": "object",
                    "properties": {"": {"type": "string"}},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "add_partner_data":
            partner_name = arguments.pop("name")
            p = _add_or_update_partner(partner_name, arguments)
            return [types.TextContent(type="text", text=json.dumps(p, indent=2))]

        elif name == "analyze_partner_churn":
            partner = _get_partner(arguments["name"])
            if not partner:
                return [types.TextContent(type="text", text=json.dumps({"error": f"Partner '{arguments['name']}' not found"}))]
            analysis = analyze_partner(partner)
            return [types.TextContent(type="text", text=json.dumps(analysis, indent=2))]

        elif name == "analyze_portfolio":
            results = _ranked_portfolio()
            if isinstance(results, dict):
                return [types.TextContent(type="text", text=json.dumps(results))]
            summary = _portfolio_summary(results)
            return [types.TextContent(type="text", text=json.dumps({"ranked_partners": results, "summary": summary}, indent=2))]

        elif name == "get_recommendations":
            partner = _get_partner(arguments["name"])
            if not partner:
                return [types.TextContent(type="text", text=json.dumps({"error": f"Partner '{arguments['name']}' not found"}))]
            churn = _score_churn_risk(partner)
            growth = _score_growth_readiness(partner)
            recs = _get_recommendations(partner, churn, growth)
            return [types.TextContent(type="text", text=json.dumps({
                "partner": arguments["name"],
                "churn_risk": {k: v for k, v in churn.items() if k != "churn_signal_breakdown"},
                "growth_readiness": {k: v for k, v in growth.items() if k != "growth_signal_breakdown"},
                "recommendations": recs,
            }, indent=2))]

        elif name == "get_portfolio_heatmap":
            results = _ranked_portfolio()
            if isinstance(results, dict):
                return [types.TextContent(type="text", text=_fmt_heatmap([]))]
            return [types.TextContent(type="text", text=_fmt_heatmap(results))]

        elif name == "get_portfolio_dashboard":
            results = _ranked_portfolio()
            if isinstance(results, dict):
                return [types.TextContent(type="text", text=json.dumps({"error": results["error"]}))]
            summary = _portfolio_summary(results)
            return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]

        elif name == "log_intervention":
            interventions = _load_json(INTERVENTIONS_FILE, [])
            intervention = {
                "id": str(uuid.uuid4())[:8],
                "partner": arguments["name"],
                "playbook": arguments["playbook"],
                "applied_at": _get_timestamp(),
                "status": "active",
                "notes": arguments.get("notes", ""),
            }
            interventions.append(intervention)
            _save_json(INTERVENTIONS_FILE, interventions)
            return [types.TextContent(type="text", text=json.dumps(intervention, indent=2))]

        elif name == "load_demo_data":
            count = _load_demo_data()
            return [types.TextContent(type="text", text=json.dumps({"loaded": count, "message": f"Loaded {count} sample partners"}))]

        raise ValueError(f"Unknown tool: {name}")

    async def run():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="prism",
                    server_version="0.1.0",
                ),
            )

    import asyncio
    asyncio.run(run())


# ── CLI Argument Parser ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="PRISM — Partner Risk & Intelligence Scoring Matrix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  prism.py demo                                 Load samples + full analysis
  prism.py partner add AcmeCo --tier gold --annual-revenue 200000
  prism.py partner show AcmeCo                  Detailed partner report
  prism.py analyze portfolio                    Rank all partners by risk
  prism.py recommend CloudSync Networks         Get intervention playbooks
  prism.py heatmap                              Portfolio risk heatmap
  prism.py intervene "CloudSync Networks" --playbook "High-Risk Retention Program"
  prism.py dashboard                            Executive summary
  prism.py serve                                Start MCP server
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # demo
    subparsers.add_parser("demo", help="Load sample partners and run full analysis")

    # partner
    partner_parser = subparsers.add_parser("partner", help="Manage partners")
    partner_sub = partner_parser.add_subparsers(dest="partner_cmd")

    p_add = partner_sub.add_parser("add", help="Add or update a partner")
    p_add.add_argument("name", help="Partner company name")
    p_add.add_argument("--tier", choices=["authorized", "gold", "platinum"])
    p_add.add_argument("--annual-revenue", type=float)
    p_add.add_argument("--days-since-last-deal", type=int)
    p_add.add_argument("--deal-count-trend-pct", type=float)
    p_add.add_argument("--monthly-portal-logins", type=int)
    p_add.add_argument("--mdf-utilization-pct", type=float)
    p_add.add_argument("--months-since-last-training", type=int)
    p_add.add_argument("--certification-level", type=int, choices=[0, 1, 2])
    p_add.add_argument("--monthly-support-tickets", type=int)
    p_add.add_argument("--pipeline-deals-per-quarter", type=int)
    p_add.add_argument("--email-open-rate-pct", type=float)
    p_add.add_argument("--program-compliance-pct", type=float)
    p_add.add_argument("--revenue-growth-pct", type=float)
    p_add.add_argument("--deal-size-trend-pct", type=float)
    p_add.add_argument("--new-logos-per-quarter", type=int)
    p_add.add_argument("--training-completion-pct", type=float)
    p_add.add_argument("--mdf-roi-multiplier", type=float)
    p_add.add_argument("--co-sell-deals-this-year", type=int)
    p_add.add_argument("--portal-feature-adoption-count", type=int)
    p_add.add_argument("--region")
    p_add.add_argument("--analyze", action="store_true", help="Run analysis after adding")

    partner_sub.add_parser("list", help="List all partners")

    p_show = partner_sub.add_parser("show", help="Show detailed partner analysis")
    p_show.add_argument("name", help="Partner company name")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run churn/growth analysis")
    analyze_sub = analyze_parser.add_subparsers(dest="target")

    p_ap = analyze_sub.add_parser("portfolio", help="Analyze full portfolio")
    p_ap = analyze_sub.add_parser("partner", help="Analyze a specific partner")
    p_ap.add_argument("name", help="Partner company name")

    # recommend
    rec_parser = subparsers.add_parser("recommend", help="Get intervention recommendations")
    rec_parser.add_argument("name", help="Partner company name")

    # heatmap
    subparsers.add_parser("heatmap", help="Show portfolio risk heatmap")

    # intervene
    int_parser = subparsers.add_parser("intervene", help="Log an intervention for a partner")
    int_parser.add_argument("name", help="Partner company name")
    int_parser.add_argument("--playbook", required=True, help="Playbook name (e.g. 'Critical Re-Engagement Sprint')")
    int_parser.add_argument("--notes", help="Optional notes")

    # dashboard
    subparsers.add_parser("dashboard", help="Portfolio executive summary")

    # serve
    subparsers.add_parser("serve", help="Start MCP server mode")

    args = parser.parse_args()

    if args.command == "demo":
        cmd_demo()
    elif args.command == "partner":
        if args.partner_cmd == "add":
            cmd_partner_add(args)
        elif args.partner_cmd == "list":
            cmd_partner_list()
        elif args.partner_cmd == "show":
            cmd_partner_show(args)
        else:
            parser.print_help()
    elif args.command == "analyze":
        if args.target == "portfolio":
            cmd_analyze_portfolio()
        elif args.target == "partner":
            cmd_analyze_partner(args.name)
        else:
            print("Specify: portfolio or partner <name>")
    elif args.command == "recommend":
        cmd_recommend(args)
    elif args.command == "heatmap":
        cmd_heatmap()
    elif args.command == "intervene":
        cmd_intervene(args)
    elif args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "serve":
        cmd_serve()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()