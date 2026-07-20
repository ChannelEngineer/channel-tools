"""Incentives module.

Consolidates: PIRE (rebates/MDF), PROMOTE (promo ROI), SPARK (recognition/SPIFs).
Rebate math ported from PIRE; claim workflow unified on incentive_claims table.
"""
import uuid
from datetime import datetime
from .. import db

DEFAULT_REBATE_PROGRAM = {
    "tiers": [
        {"name": "Base", "min_revenue": 0, "rebate_pct": 1.0},
        {"name": "Growth", "min_revenue": 100000, "rebate_pct": 2.0},
        {"name": "Elite", "min_revenue": 500000, "rebate_pct": 3.5},
    ],
    "rules": {
        "deal_registration_bonus_pct": 1.0,
        "new_logo_bonus_pct": 1.5,
        "accelerator_thresholds": [{"above_revenue": 1000000, "bonus_pct": 0.5}],
        "spiff_amount": 250,
    },
}

MDF_POLICY = {"coop_pct": 50, "claim_window_days": 90, "auto_approve_max": {"platinum": 10000, "gold": 5000, "authorized": 0}}
SPIF_AUTO_APPROVE_MAX = 500


def calculate_rebate(transactions: list[dict], program: dict | None = None) -> dict:
    """PIRE rebate calculation: tiered base + deal-reg bonus + new-logo bonus + accelerators + SPIFFs."""
    prog = program or DEFAULT_REBATE_PROGRAM
    def rev(t):
        return float(t.get("revenue", t.get("value", 0)))
    def flag(t, k):
        return str(t.get(k, "")).lower() in ("yes", "true", "1")

    total_revenue = sum(rev(t) for t in transactions)
    registered_revenue = sum(rev(t) for t in transactions if flag(t, "is_registered"))
    new_logo_deals = [t for t in transactions if flag(t, "is_new_logo")]
    new_logo_revenue = sum(rev(t) for t in new_logo_deals)

    tiers = sorted(prog["tiers"], key=lambda t: t["min_revenue"])
    selected = tiers[0]
    for t in reversed(tiers):
        if total_revenue >= t["min_revenue"]:
            selected = t
            break

    rules = prog["rules"]
    base_rebate = total_revenue * selected["rebate_pct"] / 100
    deal_reg_bonus = registered_revenue * rules.get("deal_registration_bonus_pct", 0) / 100
    new_logo_bonus = new_logo_revenue * rules.get("new_logo_bonus_pct", 0) / 100
    accel_bonus = 0.0
    for a in rules.get("accelerator_thresholds", []):
        if total_revenue >= a["above_revenue"]:
            accel_bonus = total_revenue * a["bonus_pct"] / 100
    spiff_total = len(new_logo_deals) * rules.get("spiff_amount", 0)

    return {
        "total_revenue": round(total_revenue, 2),
        "tier": selected["name"],
        "base_rebate": round(base_rebate, 2),
        "deal_registration_bonus": round(deal_reg_bonus, 2),
        "new_logo_bonus": round(new_logo_bonus, 2),
        "accelerator_bonus": round(accel_bonus, 2),
        "spiff_total": round(spiff_total, 2),
        "total_payout": round(base_rebate + deal_reg_bonus + new_logo_bonus + accel_bonus + spiff_total, 2),
    }


def submit_claim(partner_id: str, kind: str, amount: float, program: str = "") -> dict:
    """Unified claim submission for mdf|spif|rebate with tier-based auto-approval."""
    partner = db.get_partner(partner_id)
    if not partner:
        raise ValueError(f"Unknown partner: {partner_id}")

    status = "pending"
    if kind == "mdf" and amount <= MDF_POLICY["auto_approve_max"].get(partner["tier"], 0):
        status = "approved"
    elif kind == "spif" and amount <= SPIF_AUTO_APPROVE_MAX:
        status = "approved"

    claim = {
        "id": f"CLM-{uuid.uuid4().hex[:8].upper()}",
        "partner_id": partner_id,
        "kind": kind,
        "amount": amount,
        "status": status,
        "program": program,
        "submitted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "resolved_at": datetime.utcnow().isoformat(timespec="seconds") + "Z" if status == "approved" else None,
    }
    db.insert("incentive_claims", claim)
    if kind == "mdf":
        claim["reimbursement_note"] = f"{MDF_POLICY['coop_pct']}% co-op; claim within {MDF_POLICY['claim_window_days']} days"
    return claim


def promo_roi(spend: float, attributed_revenue: float, deals_influenced: int = 0) -> dict:
    """PROMOTE-style promotional ROI."""
    roi = (attributed_revenue - spend) / spend if spend else 0
    return {
        "spend": spend,
        "attributed_revenue": attributed_revenue,
        "deals_influenced": deals_influenced,
        "roi_multiple": round(attributed_revenue / spend, 2) if spend else None,
        "roi_pct": round(roi * 100, 1),
        "verdict": "strong" if roi >= 3 else "positive" if roi > 0 else "negative",
    }


def leaderboard(limit: int = 10) -> list[dict]:
    """SPARK-style recognition leaderboard by revenue + wins."""
    rows = db.query(
        "SELECT id, name, tier, annual_revenue, deals_won FROM partners "
        "ORDER BY annual_revenue DESC, deals_won DESC LIMIT ?", (limit,))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows
