"""Health & Risk module.

Consolidates: CHAMP (compliance/health scoring), PRISM (churn & growth risk),
PEDRA (ecosystem dependency risk), PULSE (engagement).
Ported weights and thresholds from the original prototypes.
"""
import json
from .. import db

# ── From CHAMP ───────────────────────────────────────────────────────────────
HEALTH_WEIGHTS = {
    "revenue_attainment": 0.25,
    "deal_activity": 0.20,
    "certification_status": 0.20,
    "training_completion": 0.15,
    "mdf_utilization": 0.10,
    "portal_engagement": 0.05,
    "deal_recency": 0.05,
}

TIER_REQUIREMENTS = {
    "authorized": {"min_revenue": 0, "min_certifications": 0, "min_deals": 0,
                   "min_training_hours": 2, "min_mdf_utilization_pct": 0,
                   "expected_portal_logins_monthly": 2, "max_days_since_last_deal": 180},
    "gold": {"min_revenue": 50000, "min_certifications": 1, "min_deals": 5,
             "min_training_hours": 10, "min_mdf_utilization_pct": 30,
             "expected_portal_logins_monthly": 8, "max_days_since_last_deal": 90},
    "platinum": {"min_revenue": 200000, "min_certifications": 2, "min_deals": 15,
                 "min_training_hours": 20, "min_mdf_utilization_pct": 50,
                 "expected_portal_logins_monthly": 15, "max_days_since_last_deal": 60},
}

# ── From PRISM ───────────────────────────────────────────────────────────────
RISK_LEVELS = [
    (75, "critical", "Immediate intervention required"),
    (55, "high", "Proactive outreach this week"),
    (35, "moderate", "Monitor closely, plan engagement"),
    (15, "low", "Standard engagement cadence"),
    (0, "minimal", "Continue current approach"),
]


def _ratio(actual, required, cap=1.0):
    if required <= 0:
        return cap
    return min(actual / required, cap)


def health_score(partner: dict) -> dict:
    """CHAMP-style weighted compliance/health score, 0-100."""
    req = TIER_REQUIREMENTS[partner["tier"]]
    mdf_pct = (partner["mdf_used"] / partner["mdf_allocated"] * 100) if partner["mdf_allocated"] else 0
    components = {
        "revenue_attainment": _ratio(partner["annual_revenue"], req["min_revenue"]),
        "deal_activity": _ratio(partner["deals_registered"], req["min_deals"]),
        "certification_status": _ratio(partner["certifications"], req["min_certifications"]),
        "training_completion": _ratio(partner["training_hours"], req["min_training_hours"]),
        "mdf_utilization": _ratio(mdf_pct, req["min_mdf_utilization_pct"]),
        "portal_engagement": _ratio(partner["portal_logins_30d"], req["expected_portal_logins_monthly"]),
        "deal_recency": 1.0 if partner["days_since_last_deal"] <= req["max_days_since_last_deal"]
                        else max(0, 1 - (partner["days_since_last_deal"] - req["max_days_since_last_deal"]) / 180),
    }
    score = round(sum(components[k] * HEALTH_WEIGHTS[k] for k in HEALTH_WEIGHTS) * 100, 1)
    if score >= 80:
        level, action = "green", "Healthy — standard cadence"
    elif score >= 55:
        level, action = "yellow", "Check-in call within 5 business days"
    else:
        level, action = "red", "CM contact within 24h; leadership review"
    detail = {"components": {k: round(v * 100, 1) for k, v in components.items()}, "action": action}
    db.record_score(partner["id"], "health", score, level, detail)
    return {"partner_id": partner["id"], "score": score, "level": level, **detail}


def churn_risk(partner: dict) -> dict:
    """PRISM-style churn risk, 0-100 (higher = riskier).

    Derives signals from unified schema fields; extended signals can be
    supplied through partner metadata.
    """
    meta = json.loads(partner.get("metadata") or "{}")
    req = TIER_REQUIREMENTS[partner["tier"]]
    mdf_pct = (partner["mdf_used"] / partner["mdf_allocated"] * 100) if partner["mdf_allocated"] else 0

    signals = {
        "days_since_last_deal": (min(partner["days_since_last_deal"] / req["max_days_since_last_deal"], 2) / 2, 0.20),
        "deal_count_trend": (meta.get("deal_trend_risk", 0.5), 0.15),
        "portal_login_frequency": (1 - _ratio(partner["portal_logins_30d"], req["expected_portal_logins_monthly"]), 0.12),
        "mdf_utilization_trend": (1 - _ratio(mdf_pct, max(req["min_mdf_utilization_pct"], 1)), 0.10),
        "training_recency": (1 - _ratio(partner["training_hours"], req["min_training_hours"]), 0.10),
        "certification_status": (1 - _ratio(partner["certifications"], max(req["min_certifications"], 1)), 0.08),
        "support_ticket_trend": (meta.get("support_ticket_risk", 0.3), 0.08),
        "pipeline_velocity": (meta.get("pipeline_velocity_risk", 0.4), 0.07),
        "email_engagement_rate": (meta.get("email_disengagement", 0.4), 0.05),
        "program_compliance_score": (meta.get("compliance_risk", 0.3), 0.05),
    }
    score = round(sum(v * w for v, w in signals.values()) * 100, 1)
    for threshold, level, action in RISK_LEVELS:
        if score >= threshold:
            break
    detail = {"signals": {k: round(v * 100, 1) for k, (v, _) in signals.items()}, "action": action}
    db.record_score(partner["id"], "churn_risk", score, level, detail)
    return {"partner_id": partner["id"], "score": score, "level": level, **detail}


def portfolio_report() -> dict:
    """PEDRA-style concentration/dependency view across the whole portfolio."""
    partners = db.list_partners()
    total_rev = sum(p["annual_revenue"] for p in partners) or 1
    concentration = sorted(
        ({"id": p["id"], "name": p["name"], "tier": p["tier"],
          "revenue_share_pct": round(p["annual_revenue"] / total_rev * 100, 1)}
         for p in partners),
        key=lambda x: -x["revenue_share_pct"],
    )
    top3 = sum(c["revenue_share_pct"] for c in concentration[:3])
    return {
        "partner_count": len(partners),
        "total_revenue": total_rev,
        "top3_concentration_pct": round(top3, 1),
        "concentration_risk": "high" if top3 > 60 else "moderate" if top3 > 40 else "low",
        "partners": concentration,
    }


def run_all() -> list[dict]:
    out = []
    for p in db.list_partners():
        out.append({"health": health_score(p), "churn_risk": churn_risk(p)})
    return out
