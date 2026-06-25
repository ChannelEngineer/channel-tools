#!/usr/bin/env python3
"""
CHAMP — Channel Health & Audit Monitoring Platform

Automated partner program compliance auditing and tier management.
CLI tool + MCP server for continuous channel program compliance monitoring.

Usage:
    python3 champ.py program define --name "Partner-2026" ...
    python3 champ.py partner add --name "TechSolvers" ...
    python3 champ.py audit partner --name "TechSolvers"
    python3 champ.py audit program --program "Partner-2026"
    python3 champ.py tier recommend
    python3 champ.py report --format text
    python3 champ.py demo          # Load sample data
    python3 champ.py serve         # Start MCP server
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────

DATA_DIR = Path.home() / ".champ"
PROGRAM_FILE = DATA_DIR / "programs.json"
PARTNERS_FILE = DATA_DIR / "partners.json"
AUDITS_FILE = DATA_DIR / "audits.json"
TIER_CHANGES_FILE = DATA_DIR / "tier_changes.json"
REPORTS_FILE = DATA_DIR / "reports.json"

# Default compliance weights
DEFAULT_WEIGHTS = {
    "revenue_attainment": 0.25,
    "deal_activity": 0.20,
    "certification_status": 0.20,
    "training_completion": 0.15,
    "mdf_utilization": 0.10,
    "portal_engagement": 0.05,
    "deal_recency": 0.05,
}

DEFAULT_TIERS = {
    "authorized": {
        "name": "Authorized",
        "index": 0,
        "min_revenue": 0,
        "min_certifications": 0,
        "min_deals": 0,
        "min_training_hours": 2,
        "min_mdf_utilization_pct": 0,
        "expected_portal_logins_monthly": 2,
        "max_days_since_last_deal": 180,
    },
    "gold": {
        "name": "Gold",
        "index": 1,
        "min_revenue": 50000,
        "min_certifications": 1,
        "min_deals": 5,
        "min_training_hours": 10,
        "min_mdf_utilization_pct": 30,
        "expected_portal_logins_monthly": 8,
        "max_days_since_last_deal": 90,
    },
    "platinum": {
        "name": "Platinum",
        "index": 2,
        "min_revenue": 200000,
        "min_certifications": 2,
        "min_deals": 15,
        "min_training_hours": 20,
        "min_mdf_utilization_pct": 50,
        "expected_portal_logins_monthly": 15,
        "max_days_since_last_deal": 45,
    },
}


# ── Data Layer ─────────────────────────────────────────────────────────────

def _ensure_data_dir():
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Any = None) -> Any:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def _save_json(path: Path, data: Any):
    _ensure_data_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_programs() -> dict:
    return _load_json(PROGRAM_FILE, {})


def _save_programs(programs: dict):
    _save_json(PROGRAM_FILE, programs)


def _load_partners() -> dict:
    return _load_json(PARTNERS_FILE, {})


def _save_partners(partners: dict):
    _save_json(PARTNERS_FILE, partners)


def _load_audits() -> list:
    return _load_json(AUDITS_FILE, [])


def _save_audits(audits: list):
    _save_json(AUDITS_FILE, audits)


def _load_tier_changes() -> list:
    return _load_json(TIER_CHANGES_FILE, [])


def _save_tier_changes(changes: list):
    _save_json(TIER_CHANGES_FILE, changes)


# ── Compliance Engine ──────────────────────────────────────────────────────

def _score_revenue_attainment(revenue: float, min_revenue: float) -> dict:
    """Score revenue attainment against tier minimum."""
    if min_revenue == 0:
        return {"score": 100.0, "status": "pass", "details": f"${revenue:,.0f} (no minimum)"}
    ratio = revenue / min_revenue
    if ratio >= 1.5:
        score = 100.0
        status = "exceeds"
    elif ratio >= 1.0:
        score = 85.0 + (ratio - 1.0) * 30  # 85-100
        status = "pass"
    elif ratio >= 0.75:
        score = 60.0 + (ratio - 0.75) * 100  # 60-85
        status = "warning"
    elif ratio >= 0.5:
        score = 30.0 + (ratio - 0.5) * 120  # 30-60
        status = "below"
    else:
        score = max(0, ratio * 60)
        status = "fail"
    return {
        "score": round(score, 1),
        "status": status,
        "details": f"${revenue:,.0f} / ${min_revenue:,.0f} ({ratio*100:.0f}%)",
    }


def _score_deal_activity(deals: int, min_deals: int) -> dict:
    """Score deal registration activity."""
    if min_deals == 0:
        return {"score": 100.0, "status": "pass", "details": f"{deals} deals (no minimum)"}
    ratio = deals / min_deals
    if ratio >= 1.5:
        score = 100.0
        status = "exceeds"
    elif ratio >= 1.0:
        score = 80.0 + (ratio - 1.0) * 40
        status = "pass"
    elif ratio >= 0.5:
        score = 40.0 + (ratio - 0.5) * 80
        status = "warning"
    else:
        score = max(0, ratio * 80)
        status = "fail"
    return {
        "score": round(score, 1),
        "status": status,
        "details": f"{deals} deals / {min_deals} minimum ({ratio*100:.0f}%)",
    }


def _score_certifications(certs: int, min_certs: int) -> dict:
    """Score certification status."""
    if min_certs == 0:
        return {"score": 100.0, "status": "pass", "details": f"{certs} cert(s) (no minimum)"}
    if certs >= min_certs:
        extra = min((certs - min_certs) * 10, 15)
        score = 85.0 + extra
        return {"score": round(score, 1), "status": "exceeds" if certs > min_certs else "pass",
                "details": f"{certs} cert(s) / {min_certs} required"}
    return {
        "score": max(0, (certs / min_certs) * 60),
        "status": "fail" if certs == 0 else "below",
        "details": f"{certs} cert(s) / {min_certs} required",
    }


def _score_training(hours: float, min_hours: float) -> dict:
    """Score training completion."""
    if min_hours == 0:
        return {"score": 100.0, "status": "pass", "details": f"{hours}h (no minimum)"}
    ratio = hours / min_hours
    if ratio >= 1.0:
        score = min(100, 80 + (ratio - 1.0) * 20)
        return {"score": round(score, 1), "status": "pass",
                "details": f"{hours}h / {min_hours}h required"}
    score = max(0, ratio * 70)
    return {
        "score": round(score, 1),
        "status": "warning" if ratio >= 0.5 else "fail",
        "details": f"{hours}h / {min_hours}h required ({ratio*100:.0f}%)",
    }


def _score_mdf_utilization(mdf_used: float, mdf_allocated: float) -> dict:
    """Score MDF utilization — both underuse and overuse are flagged."""
    if mdf_allocated == 0:
        return {"score": 100.0, "status": "pass", "details": "No MDF allocated"}
    ratio = mdf_used / mdf_allocated
    # Ideal: 50-80% utilization
    if 0.5 <= ratio <= 0.8:
        score = 100.0
        status = "pass"
    elif 0.3 <= ratio < 0.5:
        score = 70.0
        status = "warning"
    elif 0.8 < ratio <= 1.0:
        score = 60.0
        status = "warning"
    elif ratio > 1.0:
        score = 30.0
        status = "fail"  # Overdrawn
    else:
        score = max(0, ratio * 100)
        status = "fail" if ratio < 0.1 else "warning"
    return {
        "score": round(score, 1),
        "status": status,
        "details": f"${mdf_used:,.0f} / ${mdf_allocated:,.0f} ({ratio*100:.0f}%)",
        "flag": "overdrawn" if ratio > 1.0 else ("underutilized" if ratio < 0.3 else "on_track"),
    }


def _score_portal_engagement(logins: int, expected: int) -> dict:
    """Score portal engagement."""
    ratio = logins / expected if expected > 0 else 1.0
    if ratio >= 1.0:
        score = min(100, 75 + (ratio - 1.0) * 25)
        return {"score": round(score, 1), "status": "pass",
                "details": f"{logins} logins / {expected} expected"}
    score = max(0, ratio * 70)
    return {
        "score": round(score, 1),
        "status": "warning" if ratio >= 0.5 else "fail",
        "details": f"{logins} logins / {expected} expected ({ratio*100:.0f}%)",
    }


def _score_deal_recency(days_since_last_deal: int, max_days: int) -> dict:
    """Score deal recency."""
    if days_since_last_deal <= max_days:
        if days_since_last_deal <= max_days * 0.3:
            score = 100.0
            status = "exceeds"
        else:
            score = 80.0 + (1 - days_since_last_deal / max_days) * 20
            status = "pass"
    else:
        excess = days_since_last_deal / max_days
        if excess <= 1.5:
            score = 50.0
            status = "warning"
        elif excess <= 2.0:
            score = 25.0
            status = "below"
        else:
            score = 0.0
            status = "fail"
    return {
        "score": round(score, 1),
        "status": status,
        "details": f"{days_since_last_deal} days / {max_days} day limit",
    }


def _calculate_compliance_score(partner: dict, tier_config: dict, weights: dict | None = None) -> dict:
    """Calculate full compliance score for a partner."""
    w = weights or DEFAULT_WEIGHTS

    scores = {
        "revenue_attainment": _score_revenue_attainment(
            partner.get("revenue", 0), tier_config.get("min_revenue", 0)
        ),
        "deal_activity": _score_deal_activity(
            partner.get("deals", 0), tier_config.get("min_deals", 0)
        ),
        "certification_status": _score_certifications(
            partner.get("certifications", 0), tier_config.get("min_certifications", 0)
        ),
        "training_completion": _score_training(
            partner.get("training_hours", 0), tier_config.get("min_training_hours", 0)
        ),
        "mdf_utilization": _score_mdf_utilization(
            partner.get("mdf_used", 0), partner.get("mdf_allocated", 0)
        ),
        "portal_engagement": _score_portal_engagement(
            partner.get("portal_logins", 0), tier_config.get("expected_portal_logins_monthly", 4)
        ),
        "deal_recency": _score_deal_recency(
            partner.get("days_since_last_deal", 999), tier_config.get("max_days_since_last_deal", 180)
        ),
    }

    # Weighted total
    total = 0.0
    breakdown = {}
    for factor, result in scores.items():
        factor_weight = w.get(factor, 1.0 / len(scores))
        contrib = result["score"] * factor_weight
        total += contrib
        breakdown[factor] = {
            "score": result["score"],
            "weight": factor_weight,
            "contribution": round(contrib, 1),
            "status": result["status"],
            "details": result["details"],
        }
        if "flag" in result:
            breakdown[factor]["flag"] = result["flag"]

    total = round(total, 1)

    # Determine overall status
    failing = sum(1 for f in scores.values() if f["status"] == "fail")
    warnings = sum(1 for f in scores.values() if f["status"] in ("warning", "below"))

    if total >= 80 and failing == 0:
        overall_status = "compliant"
    elif total >= 60 and failing <= 1:
        overall_status = "at_risk"
    elif total >= 40 and failing <= 2:
        overall_status = "non_compliant"
    else:
        overall_status = "critical"

    return {
        "overall_score": total,
        "overall_status": overall_status,
        "breakdown": breakdown,
        "failing_factors": failing,
        "warning_factors": warnings,
        "weight_snapshot": w,
    }


def _get_tier_change_recommendation(partner: dict, score_result: dict,
                                     current_tier_index: int, tiers: dict) -> dict:
    """Determine tier promotion/demotion recommendation."""
    score = score_result["overall_score"]
    status = score_result["overall_status"]
    failing = score_result["failing_factors"]
    now = datetime.now()

    tier_keys = sorted(tiers.keys(), key=lambda k: tiers[k]["index"])
    current_key = tier_keys[current_tier_index]

    recommendation = {
        "current_tier": tiers[current_key]["name"],
        "current_tier_key": current_key,
        "score": score,
        "status": status,
        "recommendation": "stable",
        "recommended_tier": tiers[current_key]["name"],
        "reason": "",
        "urgency": "none",
    }

    # Check promotion eligibility
    if current_tier_index < len(tier_keys) - 1:
        next_key = tier_keys[current_tier_index + 1]
        next_tier = tiers[next_key]

        meets_revenue = partner.get("revenue", 0) >= next_tier["min_revenue"]
        meets_deals = partner.get("deals", 0) >= next_tier["min_deals"]
        meets_certs = partner.get("certifications", 0) >= next_tier["min_certifications"]

        if score >= 80 and meets_revenue and meets_deals and meets_certs:
            recommendation["recommendation"] = "promote"
            recommendation["recommended_tier"] = tiers[next_key]["name"]
            recommendation["recommended_tier_key"] = next_key
            recommendation["urgency"] = "medium"
            recommendation["reason"] = (
                f"Score {score}% exceeds 80% threshold and meets all {tiers[next_key]['name']} "
                f"hard requirements (${next_tier['min_revenue']:,.0f} revenue, "
                f"{next_tier['min_deals']} deals, {next_tier['min_certifications']} certifications)"
            )
            return recommendation
        elif score >= 80 and (not meets_revenue or not meets_deals):
            recommendation["recommendation"] = "consider_promotion"
            recommendation["recommended_tier"] = tiers[next_key]["name"]
            recommendation["urgency"] = "low"
            recommendation["reason"] = (
                f"Score {score}% meets threshold but missing hard requirements for "
                f"{tiers[next_key]['name']}: "
                f"{'✓' if meets_revenue else '✗'} revenue, "
                f"{'✓' if meets_deals else '✗'} deals, "
                f"{'✓' if meets_certs else '✗'} certs"
            )
            return recommendation

    # Check demotion risk
    if score < 60 or failing >= 2:
        if current_tier_index > 0:
            prev_key = tier_keys[current_tier_index - 1]
            demote_reason_parts = []
            if score < 40:
                demote_reason_parts.append(f"Critical score ({score}%)")
            if failing >= 3:
                demote_reason_parts.append(f"{failing} failing factors")
            if score < 60:
                demote_reason_parts.append(f"Score ({score}%) below 60% threshold")

            recommendation["recommendation"] = "demote"
            recommendation["recommended_tier"] = tiers[prev_key]["name"]
            recommendation["recommended_tier_key"] = prev_key
            recommendation["urgency"] = "high" if score < 40 else "medium"
            recommendation["reason"] = "; ".join(demote_reason_parts)
            return recommendation
        else:
            # Already at lowest tier — flag for program review
            recommendation["recommendation"] = "review"
            recommendation["urgency"] = "high" if score < 30 else "medium"
            recommendation["reason"] = f"Critical compliance ({score}%, {failing} failing factors) — consider program exit"
            return recommendation

    # At risk warning
    if status == "at_risk":
        recommendation["recommendation"] = "warn"
        recommendation["urgency"] = "low"
        recommendation["reason"] = f"At-risk score ({score}%) — {failing} failing factor(s), {score_result['warning_factors']} warning(s)"
        return recommendation

    recommendation["reason"] = f"All requirements met — score {score}%, {status}"
    return recommendation


# ── Core Logic ─────────────────────────────────────────────────────────────

def cmd_program_define(args):
    """Define or update a partner program with tier requirements."""
    programs = _load_programs()
    name = args.name

    if args.tiers:
        tier_list = [t.strip() for t in args.tiers.split(",")]
    else:
        tier_list = ["authorized", "gold", "platinum"]

    if args.requirements:
        reqs = json.loads(args.requirements)
    else:
        reqs = {}

    tiers = {}
    for key in tier_list:
        base = dict(DEFAULT_TIERS.get(key, {}))
        if key in reqs:
            base.update(reqs[key])
        base["key"] = key
        tiers[key] = base

    program = {
        "name": name,
        "description": args.description or f"{name} Partner Program",
        "tiers": tiers,
        "tier_order": tier_list,
        "weights": DEFAULT_WEIGHTS,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }

    programs[name] = program
    _save_programs(programs)

    print(f"✅ Program '{name}' defined with {len(tier_list)} tiers:")
    for key, cfg in tiers.items():
        print(f"   {cfg['name']:15s} — rev=${cfg['min_revenue']:<8,} deals={cfg['min_deals']:<3} "
              f"certs={cfg['min_certifications']:<2} training={cfg['min_training_hours']}h")
    return program


def cmd_partner_add(args):
    """Add or update partner performance data."""
    partners = _load_partners()
    name = args.name

    partner = {
        "name": name,
        "tier": args.tier,
        "revenue": args.revenue,
        "deals": args.deals,
        "certifications": args.certifications,
        "training_hours": args.training_hours,
        "mdf_used": args.mdf_used,
        "mdf_allocated": args.mdf_allocated,
        "portal_logins": args.portal_logins,
        "days_since_last_deal": args.days_since_last_deal,
        "added": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }

    partners[name] = partner
    _save_partners(partners)
    print(f"✅ Partner '{name}' added/updated ({args.tier} tier)")
    return partner


def cmd_partner_list(args):
    """List all partners."""
    partners = _load_partners()
    if not partners:
        print("No partners found. Add one with `partner add` or load demo data with `demo`.")
        return

    print(f"{'Partner':25s} {'Tier':15s} {'Revenue':>12s} {'Deals':>6s} {'Certs':>5s} {'Score':>6s}")
    print("-" * 75)
    for pname, pdata in sorted(partners.items()):
        tier_config = DEFAULT_TIERS.get(pdata.get("tier", "authorized"), {})
        score_result = _calculate_compliance_score(pdata, tier_config)
        score = score_result["overall_score"]
        print(f"{pname:25s} {pdata.get('tier', '-'):15s} "
              f"${pdata.get('revenue', 0):>10,.0f} {pdata.get('deals', 0):>6d} "
              f"{pdata.get('certifications', 0):>5d} {score:>5.1f}%")
    print(f"\nTotal: {len(partners)} partner(s)")


def cmd_audit_partner(args):
    """Run compliance audit for a specific partner."""
    partners = _load_partners()
    programs = _load_programs()

    name = args.name
    if name not in partners:
        print(f"❌ Partner '{name}' not found.")
        return

    partner = partners[name]
    tier_key = partner.get("tier", "authorized")

    # Try to load program-specific tier config, fall back to defaults
    program_name = args.program
    if program_name and program_name in programs:
        prog = programs[program_name]
        tiers = prog["tiers"]
        weights = prog.get("weights", DEFAULT_WEIGHTS)
    else:
        tiers = DEFAULT_TIERS
        weights = DEFAULT_WEIGHTS

    if tier_key not in tiers:
        print(f"❌ Tier '{tier_key}' not found in program/program '{program_name or 'default'}'.")
        return

    tier_config = tiers[tier_key]
    score_result = _calculate_compliance_score(partner, tier_config, weights)
    tier_index = tiers[tier_key]["index"]
    recommendation = _get_tier_change_recommendation(partner, score_result, tier_index, tiers)

    # Save audit
    audits = _load_audits()
    audit = {
        "partner": name,
        "partner_tier": tier_key,
        "program": program_name or "default",
        "timestamp": datetime.now().isoformat(),
        "score_result": score_result,
        "tier_recommendation": recommendation,
    }
    audits.append(audit)
    _save_audits(audits)

    # Display
    print(f"\n{'='*60}")
    print(f"  COMPLIANCE AUDIT: {name}")
    print(f"  Current Tier: {tier_config['name']}")
    print(f"  Overall Score: {score_result['overall_score']:.1f}% — {score_result['overall_status'].upper()}")
    print(f"{'='*60}")

    print(f"\n  {'Factor':25s} {'Score':>7s} {'Weight':>7s} {'Contrib':>8s} {'Status':>10s}")
    print(f"  {'-'*57}")
    for factor, data in score_result["breakdown"].items():
        label = factor.replace("_", " ").title()
        flag = data.get("flag", "")
        flag_str = f" [{flag}]" if flag else ""
        print(f"  {label:25s} {data['score']:>6.1f}% {data['weight']:>6.2f} "
              f"{data['contribution']:>7.1f}% {data['status']:>10s}{flag_str}")
    print(f"  {'-'*57}")
    print(f"  {'TOTAL':25s} {score_result['overall_score']:>6.1f}% {'1.00':>7s} "
          f"{score_result['overall_score']:>8.1f}%")

    print(f"\n  ── Tier Recommendation ──")
    rec = recommendation
    emoji = {"promote": "⬆️", "demote": "⬇️", "warn": "⚠️", "review": "🔍", "stable": "✅",
             "consider_promotion": "↗️"}
    print(f"  {emoji.get(rec['recommendation'], '❓')} {rec['recommendation'].upper()}: {rec['reason']}")
    if rec['recommendation'] in ('promote', 'demote', 'consider_promotion'):
        print(f"     Recommended tier: {rec['recommended_tier']}")
    print(f"     Urgency: {rec['urgency']}")

    return audit


def cmd_audit_program(args):
    """Run full program compliance audit across all partners."""
    partners = _load_partners()
    programs = _load_programs()

    program_name = args.program
    if program_name and program_name in programs:
        prog = programs[program_name]
        tiers = prog["tiers"]
        weights = prog.get("weights", DEFAULT_WEIGHTS)
    else:
        tiers = DEFAULT_TIERS
        weights = DEFAULT_WEIGHTS

    if not partners:
        print("No partners to audit. Add partners first.")
        return

    results = []
    summary = {"compliant": 0, "at_risk": 0, "non_compliant": 0, "critical": 0,
               "promote": 0, "demote": 0, "stable": 0}

    print(f"\n{'='*70}")
    print(f"  PROGRAM COMPLIANCE AUDIT: {program_name or 'Default Program'}")
    print(f"  Partners: {len(partners)}")
    print(f"{'='*70}")

    for pname, pdata in sorted(partners.items()):
        tier_key = pdata.get("tier", "authorized")
        if tier_key not in tiers:
            continue
        tier_config = tiers[tier_key]
        score_result = _calculate_compliance_score(pdata, tier_config, weights)
        tier_index = tiers[tier_key]["index"]
        rec = _get_tier_change_recommendation(pdata, score_result, tier_index, tiers)

        results.append({
            "partner": pname,
            "tier": tier_key,
            "tier_name": tier_config["name"],
            "score": score_result["overall_score"],
            "status": score_result["overall_status"],
            "recommendation": rec["recommendation"],
            "failing": score_result["failing_factors"],
        })

        summary[score_result["overall_status"]] = summary.get(score_result["overall_status"], 0) + 1
        summary[rec["recommendation"]] = summary.get(rec["recommendation"], 0) + 1

        emoji = {"promote": "⬆️", "demote": "⬇️", "warn": "⚠️", "review": "🔍", "stable": "✅",
                 "consider_promotion": "↗️"}
        print(f"\n  {pname:25s} | {tier_config['name']:12s} | "
              f"Score: {score_result['overall_score']:5.1f}% | "
              f"{score_result['overall_status'].upper():14s} | "
              f"{emoji.get(rec['recommendation'], '❓')} {rec['recommendation']}")

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Compliant:    {summary.get('compliant', 0)}")
    print(f"  At Risk:      {summary.get('at_risk', 0)}")
    print(f"  Non-compliant: {summary.get('non_compliant', 0)}")
    print(f"  Critical:     {summary.get('critical', 0)}")
    print(f"  ──")
    print(f"  Promote:      {summary.get('promote', 0)}")
    print(f"  Consider Promotion: {summary.get('consider_promotion', 0)}")
    print(f"  Demote:       {summary.get('demote', 0)}")
    print(f"  Warn:         {summary.get('warn', 0)}")
    print(f"  Review/Exit:  {summary.get('review', 0)}")
    print(f"  Stable:       {summary.get('stable', 0)}")

    return {"program": program_name or "default", "partners_audited": len(partners),
            "results": results, "summary": summary}


def cmd_tier_recommend(args):
    """Show tier change recommendations for all partners."""
    partners = _load_partners()
    programs = _load_programs()

    if not partners:
        print("No partners found. Add partners first.")
        return

    print(f"\n{'='*70}")
    print(f"  TIER CHANGE RECOMMENDATIONS")
    print(f"{'='*70}")

    changes = []
    for pname, pdata in sorted(partners.items()):
        tier_key = pdata.get("tier", "authorized")
        tier_config = DEFAULT_TIERS.get(tier_key, DEFAULT_TIERS["authorized"])
        score_result = _calculate_compliance_score(pdata, tier_config)
        tier_index = tier_config["index"]
        rec = _get_tier_change_recommendation(pdata, score_result, tier_index, DEFAULT_TIERS)

        changes.append({
            "partner": pname,
            "current_tier": rec["current_tier"],
            "score": rec["score"],
            "recommendation": rec["recommendation"],
            "recommended_tier": rec["recommended_tier"] if rec["recommendation"] in ("promote", "demote", "consider_promotion") else "",
            "urgency": rec["urgency"],
            "reason": rec["reason"],
        })

        emoji_map = {"promote": "⬆️", "demote": "⬇️", "warn": "⚠️", "review": "🔍",
                     "stable": "✅", "consider_promotion": "↗️"}
        emoji = emoji_map.get(rec['recommendation'], '❓')

        print(f"\n  {emoji} {pname}")
        print(f"     {rec['current_tier']:15s} → Score: {rec['score']:.1f}%")
        if rec['recommendation'] in ('promote', 'demote', 'consider_promotion'):
            print(f"     {'→ ' + rec['recommended_tier']:15s} (urgency: {rec['urgency']})")
        elif rec['recommendation'] == 'warn':
            print(f"     {'⚠️ At-risk':15s} (urgency: {rec['urgency']})")
        elif rec['recommendation'] == 'review':
            print(f"     {'🔍 Review needed':15s} (urgency: {rec['urgency']})")
        print(f"     {rec['reason']}")

    # Save tier change recommendations
    _save_tier_changes(changes)
    return changes


def cmd_report(args):
    """Generate a compliance report."""
    partners = _load_partners()
    audits = _load_audits()
    tier_changes = _load_tier_changes()

    report = {
        "generated": datetime.now().isoformat(),
        "partner_count": len(partners),
        "audit_count": len(audits),
        "tier_changes_pending": len([c for c in tier_changes if c.get("recommendation") in ("promote", "demote")]),
        "latest_audits": audits[-5:] if audits else [],
        "tier_recommendations": tier_changes,
    }

    _save_json(REPORTS_FILE, report)

    fmt = args.format or "text"
    if fmt == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"\n{'='*60}")
        print(f"  CHAMP COMPLIANCE REPORT")
        print(f"  Generated: {report['generated']}")
        print(f"{'='*60}")
        print(f"  Partners tracked:     {report['partner_count']}")
        print(f"  Audits performed:     {report['audit_count']}")
        print(f"  Pending tier changes: {report['tier_changes_pending']}")
        print(f"{'='*60}")

        pending = [c for c in tier_changes if c.get("recommendation") in ("promote", "demote")]
        if pending:
            print(f"\n  PENDING TIER CHANGES:")
            for c in pending:
                print(f"    {c['partner']:25s} → {c['recommended_tier']:15s} "
                      f"[{c['recommendation']}] urgency: {c['urgency']}")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n  Report saved to: {args.output}")

    return report


def cmd_demo(args):
    """Load sample partner data for testing."""
    sample_data = [
        {"name": "TechSolvers Inc", "tier": "platinum", "revenue": 285000,
         "deals": 22, "certifications": 3, "training_hours": 25,
         "mdf_used": 15000, "mdf_allocated": 25000, "portal_logins": 18,
         "days_since_last_deal": 10},
        {"name": "CloudBridge Partners", "tier": "gold", "revenue": 82000,
         "deals": 9, "certifications": 1, "training_hours": 14,
         "mdf_used": 5000, "mdf_allocated": 12000, "portal_logins": 10,
         "days_since_last_deal": 22},
        {"name": "Meridian Solutions", "tier": "gold", "revenue": 45000,
         "deals": 4, "certifications": 0, "training_hours": 6,
         "mdf_used": 2000, "mdf_allocated": 10000, "portal_logins": 3,
         "days_since_last_deal": 120},
        {"name": "Atlas Consulting Group", "tier": "authorized", "revenue": 15000,
         "deals": 2, "certifications": 0, "training_hours": 4,
         "mdf_used": 0, "mdf_allocated": 5000, "portal_logins": 2,
         "days_since_last_deal": 65},
        {"name": "Pinnacle Systems", "tier": "platinum", "revenue": 310000,
         "deals": 18, "certifications": 2, "training_hours": 22,
         "mdf_used": 18000, "mdf_allocated": 30000, "portal_logins": 16,
         "days_since_last_deal": 8},
    ]

    partners = _load_partners()
    for p in sample_data:
        partners[p["name"]] = p

    _save_partners(partners)
    print(f"✅ Loaded {len(sample_data)} sample partners:")
    for p in sample_data:
        print(f"   {p['name']:30s} ({p['tier']:10s}) — ${p['revenue']:>6,.0f} rev, {p['deals']} deals, {p['certifications']} certs")

    # Also ensure default program exists
    programs = _load_programs()
    if "Partner-2026" not in programs:
        prog = {
            "name": "Partner-2026",
            "description": "2026 Partner Program",
            "tiers": DEFAULT_TIERS,
            "tier_order": ["authorized", "gold", "platinum"],
            "weights": DEFAULT_WEIGHTS,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        programs["Partner-2026"] = prog
        _save_programs(programs)
        print("✅ Default program 'Partner-2026' created")

    print("\nRun `python3 champ.py audit program` to audit all partners!")
    return sample_data


def cmd_serve(args):
    """Start as MCP server."""
    try:
        from mcp.server import Server, NotificationOptions
        from mcp.server.models import InitializationOptions
        import mcp.server.stdio
        import mcp.types as types
    except ImportError:
        print("❌ MCP package not installed. Run: pip install mcp")
        sys.exit(1)

    server = Server("champ-compliance")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="define_program",
                description="Define or update a partner program with tier requirements (revenue, deals, certifications, training, MDF).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Program name"},
                        "description": {"type": "string", "description": "Program description"},
                        "tiers": {"type": "string", "description": "Comma-separated tier keys (e.g., 'authorized,gold,platinum')"},
                        "requirements": {"type": "string", "description": "JSON string of custom requirements per tier"},
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="add_partner",
                description="Add or update partner performance data for compliance scoring.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Partner company name"},
                        "tier": {"type": "string", "enum": ["authorized", "gold", "platinum"], "description": "Current tier"},
                        "revenue": {"type": "number", "description": "Trailing 12-month revenue"},
                        "deals": {"type": "integer", "description": "Number of registered deals"},
                        "certifications": {"type": "integer", "description": "Certifications held"},
                        "training_hours": {"type": "number", "description": "Training hours completed"},
                        "mdf_used": {"type": "number", "description": "MDF funds used"},
                        "mdf_allocated": {"type": "number", "description": "MDF funds allocated"},
                        "portal_logins": {"type": "integer", "description": "Portal logins this month"},
                        "days_since_last_deal": {"type": "integer", "description": "Days since last deal registered"},
                    },
                    "required": ["name", "tier"],
                },
            ),
            types.Tool(
                name="audit_partner",
                description="Run a full compliance audit for a specific partner.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Partner company name"},
                        "program": {"type": "string", "description": "Program name (optional)"},
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="audit_program",
                description="Run a full program compliance audit across all partners.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "program": {"type": "string", "description": "Program name (optional)"},
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="get_tier_recommendations",
                description="Get tier promotion/demotion recommendations for all partners.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            types.Tool(
                name="generate_compliance_report",
                description="Generate a structured compliance report.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        try:
            if name == "define_program":
                class Args: pass
                a = Args()
                a.name = arguments["name"]
                a.description = arguments.get("description", "")
                a.tiers = arguments.get("tiers", "authorized,gold,platinum")
                a.requirements = arguments.get("requirements", "{}")
                result = cmd_program_define(a)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            elif name == "add_partner":
                class Args: pass
                a = Args()
                for k in ("name", "tier", "revenue", "deals", "certifications",
                          "training_hours", "mdf_used", "mdf_allocated",
                          "portal_logins", "days_since_last_deal"):
                    setattr(a, k, arguments.get(k, 0))
                result = cmd_partner_add(a)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            elif name == "audit_partner":
                class Args: pass
                a = Args()
                a.name = arguments["name"]
                a.program = arguments.get("program", None)
                result = cmd_audit_partner(a)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            elif name == "audit_program":
                class Args: pass
                a = Args()
                a.program = arguments.get("program", None)
                result = cmd_audit_program(a)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            elif name == "get_tier_recommendations":
                result = cmd_tier_recommend(None)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            elif name == "generate_compliance_report":
                class Args: pass
                a = Args()
                a.format = "json"
                a.output = None
                result = cmd_report(a)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]

    async def run():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream,
                InitializationOptions(
                    server_name="champ-compliance",
                    server_version="0.1.0",
                ),
            )

    import asyncio
    asyncio.run(run())


# ── Main CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CHAMP — Channel Health & Audit Monitoring Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 champ.py demo
  python3 champ.py audit partner --name "TechSolvers Inc"
  python3 champ.py audit program
  python3 champ.py tier recommend
  python3 champ.py report --format json
  python3 champ.py serve
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # program define
    p_program = subparsers.add_parser("program", help="Manage programs")
    p_program.add_argument("action", choices=["define"])
    p_program.add_argument("--name", required=True, help="Program name")
    p_program.add_argument("--description", help="Program description")
    p_program.add_argument("--tiers", default="authorized,gold,platinum",
                           help="Comma-separated tier keys")
    p_program.add_argument("--requirements", help="JSON string of custom requirements")

    # partner add
    p_partner = subparsers.add_parser("partner", help="Manage partners")
    p_partner.add_argument("action", choices=["add", "list"])
    p_partner.add_argument("--name", help="Partner company name")
    p_partner.add_argument("--tier", choices=["authorized", "gold", "platinum"], default="authorized")
    p_partner.add_argument("--revenue", type=float, default=0)
    p_partner.add_argument("--deals", type=int, default=0)
    p_partner.add_argument("--certifications", type=int, default=0)
    p_partner.add_argument("--training-hours", type=float, default=0)
    p_partner.add_argument("--mdf-used", type=float, default=0)
    p_partner.add_argument("--mdf-allocated", type=float, default=0)
    p_partner.add_argument("--portal-logins", type=int, default=0)
    p_partner.add_argument("--days-since-last-deal", type=int, default=999)

    # audit
    p_audit = subparsers.add_parser("audit", help="Run compliance audits")
    p_audit.add_argument("scope", choices=["partner", "program"])
    p_audit.add_argument("--name", help="Partner name (for partner audit)")
    p_audit.add_argument("--program", help="Program name (optional)")

    # tier recommend
    subparsers.add_parser("tier", help="Show tier recommendations")

    # report
    p_report = subparsers.add_parser("report", help="Generate compliance report")
    p_report.add_argument("--format", choices=["text", "json"], default="text")
    p_report.add_argument("--output", help="Output file path")

    # demo
    subparsers.add_parser("demo", help="Load sample data")

    # serve
    p_serve = subparsers.add_parser("serve", help="Start MCP server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=0)

    args = parser.parse_args()

    if args.command == "program":
        if args.action == "define":
            cmd_program_define(args)
    elif args.command == "partner":
        if args.action == "add":
            cmd_partner_add(args)
        elif args.action == "list":
            cmd_partner_list(args)
    elif args.command == "audit":
        if args.scope == "partner":
            cmd_audit_partner(args)
        elif args.scope == "program":
            cmd_audit_program(args)
    elif args.command == "tier":
        cmd_tier_recommend(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()