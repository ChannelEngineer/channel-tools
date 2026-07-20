"""Velocity module.

Consolidates: CHRONOS (time-to-value velocity), ASCEND (tier advancement),
PACE (campaign pacing rolled into velocity summaries).
Benchmarks and velocity math ported from CHRONOS.
"""
from datetime import datetime
from .. import db
from .health import TIER_REQUIREMENTS

# ── Ported from CHRONOS ──────────────────────────────────────────────────────
BENCHMARKS = {
    "platinum": {"green_pct": 100, "yellow_pct": 75, "milestones": {
        "onboarding_started": 1, "onboarding_complete": 5, "first_training": 7,
        "first_certification": 21, "first_deal_registered": 30, "first_deal_won": 60,
        "first_mdf_claim": 45, "first_qbr_attended": 90}},
    "gold": {"green_pct": 100, "yellow_pct": 65, "milestones": {
        "onboarding_started": 1, "onboarding_complete": 10, "first_training": 14,
        "first_certification": 30, "first_deal_registered": 45, "first_deal_won": 90,
        "first_mdf_claim": 60, "first_qbr_attended": 120}},
    "authorized": {"green_pct": 100, "yellow_pct": 55, "milestones": {
        "onboarding_started": 2, "onboarding_complete": 14, "first_training": 21,
        "first_certification": 45, "first_deal_registered": 60, "first_deal_won": 120,
        "first_mdf_claim": 90, "first_qbr_attended": 180}},
}


def record_milestone(partner_id: str, milestone: str, achieved_days: int) -> dict:
    partner = db.get_partner(partner_id)
    if not partner:
        raise ValueError(f"Unknown partner: {partner_id}")
    db.insert("milestones", {"partner_id": partner_id, "milestone": milestone,
                             "achieved_days": achieved_days,
                             "recorded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"})
    score, benchmark = calculate_velocity(partner["tier"], milestone, achieved_days)
    return {"partner_id": partner_id, "milestone": milestone, "achieved_days": achieved_days,
            "benchmark_days": benchmark, "velocity_score": score,
            "status": velocity_status(score, partner["tier"]) if score is not None else "unknown"}


def calculate_velocity(tier: str, milestone: str, actual_days: int):
    """score = benchmark/actual * 100; 100 = on benchmark, capped at 300."""
    cfg = BENCHMARKS.get(tier)
    if not cfg:
        return None, None
    benchmark = cfg["milestones"].get(milestone)
    if benchmark is None:
        return None, None
    if actual_days <= 0:
        return 100, benchmark
    return min(round(benchmark / actual_days * 100), 300), benchmark


def velocity_status(score: float, tier: str) -> str:
    cfg = BENCHMARKS.get(tier)
    if not cfg or score is None:
        return "unknown"
    if score >= cfg["green_pct"] + 10:
        return "ahead"
    if score >= cfg["green_pct"] - 10:
        return "on_track"
    if score >= cfg["yellow_pct"] - 10:
        return "at_risk"
    return "critical"


def partner_velocity(partner_id: str) -> dict:
    partner = db.get_partner(partner_id)
    if not partner:
        raise ValueError(f"Unknown partner: {partner_id}")
    rows = db.query("SELECT milestone, achieved_days FROM milestones WHERE partner_id=?", (partner_id,))
    detail, scores = [], []
    for r in rows:
        score, benchmark = calculate_velocity(partner["tier"], r["milestone"], r["achieved_days"])
        if score is None:
            continue
        scores.append(score)
        detail.append({**r, "benchmark_days": benchmark, "velocity_score": score,
                       "status": velocity_status(score, partner["tier"])})
    avg = round(sum(scores) / len(scores), 1) if scores else None
    overall = velocity_status(avg, partner["tier"]) if avg is not None else "no_data"
    if avg is not None:
        db.record_score(partner_id, "velocity", avg, overall, {"milestones": detail})
    return {"partner_id": partner_id, "tier": partner["tier"], "avg_velocity": avg,
            "overall_status": overall, "milestones": detail}


def tier_advancement(partner_id: str) -> dict:
    """ASCEND-style: is the partner eligible to move up a tier?"""
    partner = db.get_partner(partner_id)
    if not partner:
        raise ValueError(f"Unknown partner: {partner_id}")
    order = ["authorized", "gold", "platinum"]
    idx = order.index(partner["tier"])
    if idx == len(order) - 1:
        return {"partner_id": partner_id, "current_tier": partner["tier"],
                "next_tier": None, "eligible": False, "note": "Already at top tier"}
    next_tier = order[idx + 1]
    req = TIER_REQUIREMENTS[next_tier]
    mdf_pct = (partner["mdf_used"] / partner["mdf_allocated"] * 100) if partner["mdf_allocated"] else 0
    checks = {
        "revenue": (partner["annual_revenue"], req["min_revenue"]),
        "certifications": (partner["certifications"], req["min_certifications"]),
        "deals": (partner["deals_registered"], req["min_deals"]),
        "training_hours": (partner["training_hours"], req["min_training_hours"]),
        "mdf_utilization_pct": (round(mdf_pct, 1), req["min_mdf_utilization_pct"]),
    }
    gaps = {k: {"actual": a, "required": r} for k, (a, r) in checks.items() if a < r}
    return {"partner_id": partner_id, "current_tier": partner["tier"], "next_tier": next_tier,
            "eligible": not gaps, "gaps": gaps,
            "checks": {k: {"actual": a, "required": r, "met": a >= r} for k, (a, r) in checks.items()}}
