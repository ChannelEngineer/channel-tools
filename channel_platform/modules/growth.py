"""Growth module.

Consolidates: REFER (referral lifecycle + fees), PCO (co-sell matching),
BRIDGE (social selling engagement). Fee rules ported verbatim from REFER.
"""
import json
import uuid
from datetime import datetime
from .. import db

# ── Ported from REFER ────────────────────────────────────────────────────────
FEE_RULES = {
    "tier_base_pcts": {"platinum": 15, "gold": 12, "authorized": 10},
    "deal_type_multipliers": {"standard": 1.0, "enterprise": 1.2, "strategic": 1.5},
    "tier_bonus": {"platinum": 0.05, "gold": 0.03, "authorized": 0.0},
    "min_fee": 100,
    "max_fee_pct": 25,
    "payment_terms_days": 30,
    "retention_pct": 10,
    "clawback_period_months": 12,
    "fast_pay_discount": 0.02,
}


def calculate_fee(deal_value: float, sender_tier: str, deal_type: str = "standard", fast_pay: bool = False) -> dict:
    r = FEE_RULES
    base_pct = r["tier_base_pcts"].get(sender_tier, 10)
    multiplier = r["deal_type_multipliers"].get(deal_type, 1.0)
    tier_bonus = r["tier_bonus"].get(sender_tier, 0)
    effective_pct = min(base_pct * multiplier + tier_bonus * 100, r["max_fee_pct"])
    gross = deal_value * effective_pct / 100
    retention = gross * r["retention_pct"] / 100
    net = gross - retention
    out = {
        "deal_value": deal_value, "sender_tier": sender_tier, "deal_type": deal_type,
        "effective_pct": round(effective_pct, 1), "gross_fee": round(gross, 2),
        "retention_amount": round(retention, 2), "net_fee": round(net, 2),
        "payment_terms_days": 15 if fast_pay else r["payment_terms_days"],
        "clawback_period_months": r["clawback_period_months"],
    }
    if fast_pay:
        disc = net * r["fast_pay_discount"]
        out["fast_pay_discount_amount"] = round(disc, 2)
        out["net_fee_fast_pay"] = round(net - disc, 2)
    return out


def match_partner(referral: dict, exclude_id: str | None = None) -> list[dict]:
    """Score partners as referral/co-sell recipients (REFER + PCO matching).

    Weights: expertise overlap 40, region match 25, tier 20, capacity 15.
    """
    tier_pts = {"platinum": 20, "gold": 13, "authorized": 7}
    want_expertise = set(referral.get("expertise", []))
    want_region = referral.get("region")
    scored = []
    for p in db.list_partners():
        if exclude_id and p["id"] == exclude_id:
            continue
        expertise = set(json.loads(p.get("expertise") or "[]"))
        meta = json.loads(p.get("metadata") or "{}")
        capacity, active = meta.get("capacity", 10), meta.get("active_deals", 0)
        exp_score = 40 * (len(want_expertise & expertise) / len(want_expertise)) if want_expertise else 20
        region_score = 25 if (want_region and p.get("region") == want_region) else 0
        cap_score = 15 * max(0, (capacity - active) / capacity) if capacity else 0
        total = round(exp_score + region_score + tier_pts.get(p["tier"], 0) + cap_score, 1)
        scored.append({"partner_id": p["id"], "name": p["name"], "tier": p["tier"],
                       "region": p.get("region"), "match_score": total})
    return sorted(scored, key=lambda x: -x["match_score"])[:5]


def submit_referral(sender_id: str, customer: str, deal_value: float,
                    expertise: list[str] | None = None, region: str | None = None) -> dict:
    matches = match_partner({"expertise": expertise or [], "region": region}, exclude_id=sender_id)
    receiver = matches[0]["partner_id"] if matches else None
    ref = {
        "id": f"REF-{datetime.utcnow():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:3].upper()}",
        "sender_partner_id": sender_id,
        "receiver_partner_id": receiver,
        "customer": customer,
        "deal_value": deal_value,
        "status": "matched" if receiver else "submitted",
        "submitted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    db.insert("referrals", ref)
    return {**ref, "top_matches": matches}


def convert_referral(referral_id: str, won: bool) -> dict:
    rows = db.query("SELECT * FROM referrals WHERE id=?", (referral_id,))
    if not rows:
        raise ValueError(f"Unknown referral: {referral_id}")
    ref = rows[0]
    sender = db.get_partner(ref["sender_partner_id"])
    fee = calculate_fee(ref["deal_value"], sender["tier"]) if won and sender else None
    ref.update({
        "status": "won" if won else "lost",
        "converted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "fee_gross": fee["gross_fee"] if fee else None,
        "fee_net": fee["net_fee"] if fee else None,
    })
    db.insert("referrals", ref)
    return {**ref, "fee_detail": fee}


def engagement_report(inactive_days: int = 7) -> dict:
    """BRIDGE-style social-selling engagement: active vs inactive sharers via metadata."""
    active, inactive = [], []
    for p in db.list_partners():
        meta = json.loads(p.get("metadata") or "{}")
        days = meta.get("days_since_last_share")
        if days is None:
            continue
        (inactive if days >= inactive_days else active).append(
            {"partner_id": p["id"], "name": p["name"], "days_since_last_share": days})
    return {"active_sharers": active, "inactive_sharers": inactive,
            "reengagement_needed": len(inactive)}
