#!/usr/bin/env python3
"""
PACE — Partner Co-Marketing Campaign Engine
============================================
Automates the lifecycle of co-marketing campaigns between vendors and channel partners.
From proposal & budget allocation through execution tracking to ROI measurement & benchmarking.

Usage:
  # Campaign lifecycle
  pace campaign create --title "Q3 Cloud Webinar" --partner "TechSolvers" --type webinar ...
  pace campaign list [--status active|completed|proposal]
  pace campaign show CAMP-0001
  pace campaign update CAMP-0001 --status in_progress --notes "Kicked off"

  # Budget & approval
  pace campaign approve CAMP-0001 --amount 5000
  pace budget recommend --partner "TechSolvers" --total-cost 15000

  # Results & ROI
  pace campaign results CAMP-0001 --leads 45 --revenue 120000
  pace roi CAMP-0001
  pace campaign close CAMP-0001

  # Analytics
  pace dashboard
  pace benchmark

  # MCP server mode
  pip install mcp && pace serve

Data stored at ~/.pace/ (JSON files).
"""

import argparse
import json
import os
import random
import shutil
import string
import sys
import textwrap
from datetime import datetime, date, timedelta

# ── Constants ────────────────────────────────────────────────────────────────

DATA_DIR = os.path.expanduser("~/.pace")
CAMPAIGNS_FILE = os.path.join(DATA_DIR, "campaigns.json")
PARTNERS_FILE = os.path.join(DATA_DIR, "partners.json")
BENCHMARKS_FILE = os.path.join(DATA_DIR, "benchmarks.json")

CAMPAIGN_TYPES = {
    "email": "Joint Email Campaign",
    "event": "Regional Event / Tradeshow",
    "webinar": "Webinar / Online Event",
    "digital_ad": "Digital Advertising",
    "direct_mail": "Direct Mail Campaign",
    "content": "Content / Case Study Development",
    "social": "Social Media Campaign",
    "other": "Other (specify)",
}

CAMPAIGN_STATUSES = [
    "proposal", "under_review", "approved", "rejected",
    "in_progress", "completed", "closed", "cancelled",
]

TIER_ALLOCATION_LIMITS = {
    "platinum": 15000,
    "gold": 7500,
    "authorized": 2500,
}

TIER_REIMBURSEMENT_RATES = {
    "platinum": 0.60,
    "gold": 0.50,
    "authorized": 0.40,
}

DEFAULT_PARTNERS = [
    {"name": "TechSolvers Inc", "tier": "platinum", "region": "West", "mdf_ytd": 8500, "mdf_annual": 30000, "revenue_ytd": 520000},
    {"name": "DataBridge Partners", "tier": "gold", "region": "Northeast", "mdf_ytd": 3200, "mdf_annual": 15000, "revenue_ytd": 210000},
    {"name": "CloudSync Networks", "tier": "gold", "region": "South", "mdf_ytd": 5400, "mdf_annual": 15000, "revenue_ytd": 180000},
    {"name": "EnterpriseOps Group", "tier": "platinum", "region": "Midwest", "mdf_ytd": 12000, "mdf_annual": 30000, "revenue_ytd": 780000},
    {"name": "NorthStar Solutions", "tier": "authorized", "region": "Southwest", "mdf_ytd": 500, "mdf_annual": 5000, "revenue_ytd": 45000},
    {"name": "Summit Global", "tier": "gold", "region": "West", "mdf_ytd": 6800, "mdf_annual": 15000, "revenue_ytd": 340000},
    {"name": "Peak Performance Group", "tier": "platinum", "region": "Pacific Northwest", "mdf_ytd": 10500, "mdf_annual": 30000, "revenue_ytd": 620000},
    {"name": "Meridian Tech", "tier": "gold", "region": "Mid-Atlantic", "mdf_ytd": 4100, "mdf_annual": 15000, "revenue_ytd": 195000},
]

# ── Data Helpers ─────────────────────────────────────────────────────────────

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else {}


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_campaigns():
    return _load_json(CAMPAIGNS_FILE, [])


def _save_campaigns(campaigns):
    _save_json(CAMPAIGNS_FILE, campaigns)


def _load_partners():
    return _load_json(PARTNERS_FILE, [])


def _save_partners(partners):
    _save_json(PARTNERS_FILE, partners)


def _load_benchmarks():
    return _load_json(BENCHMARKS_FILE, [])


def _save_benchmarks(benchmarks):
    _save_json(BENCHMARKS_FILE, benchmarks)


def _gen_id():
    num = len(_load_campaigns()) + 1
    return f"CAMP-{num:04d}"


def _find_campaign(campaigns, cid):
    for c in campaigns:
        if c["id"] == cid:
            return c
    return None


def _find_partner(partners, name):
    for p in partners:
        if p["name"].lower() == name.lower():
            return p
    return None


def _today():
    return date.today().isoformat()


def _fmt_date(d):
    if not d:
        return "—"
    try:
        dt = datetime.fromisoformat(d) if isinstance(d, str) else d
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(d)


def _fmt_currency(v):
    return f"${v:,.2f}" if v else "$0.00"


def _pct(v):
    return f"{v:.1f}%" if v else "0.0%"


# ── Campaign Model ────────────────────────────────────────────────────────────

def _create_campaign(args):
    campaigns = _load_campaigns()
    partners = _load_partners()

    if len(partners) == 0:
        print("⚠️  No partners loaded. Run 'pace demo' first.")
        return

    cid = _gen_id()
    partner = _find_partner(partners, args.partner)
    if not partner:
        print(f"✗ Partner '{args.partner}' not found. Available: {', '.join(p['name'] for p in partners)}")
        return

    campaign = {
        "id": cid,
        "title": args.title,
        "partner_name": partner["name"],
        "partner_tier": partner["tier"],
        "region": partner.get("region", "Unknown"),
        "channel_manager": args.manager or "Unassigned",
        "campaign_type": args.type,
        "campaign_type_label": CAMPAIGN_TYPES.get(args.type, args.type),
        "description": args.description or "",
        "goals": args.goals or "",
        "target_audience": args.audience or "",
        "start_date": args.start or _today(),
        "end_date": args.end or "",
        "total_cost": args.cost or 0,
        "requested_mdf_amount": args.requested or 0,
        "approved_mdf_amount": 0,
        "status": "proposal",
        "leads_generated": 0,
        "opportunities_created": 0,
        "revenue_influenced": 0,
        "impressions": 0,
        "engagement_rate": 0,
        "notes": "",
        "activities": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    campaigns.append(campaign)
    _save_campaigns(campaigns)

    print(f"✅ Campaign {cid} created — '{args.title}'")
    print(f"   Partner: {partner['name']} ({partner['tier'].title()})")
    print(f"   Type: {CAMPAIGN_TYPES.get(args.type, args.type)}")
    print(f"   Budget Requested: {_fmt_currency(args.requested)}")
    print(f"   Status: proposal")
    print(f"\n   Next: pace campaign approve {cid} --amount N  (or)")
    print(f"         pace campaign update {cid} --status under_review")


def _list_campaigns(args):
    campaigns = _load_campaigns()
    if not campaigns:
        print("📭 No campaigns yet. Create one with 'pace campaign create'")
        return

    status_filter = args.status
    partner_filter = args.partner

    filtered = campaigns
    if status_filter:
        filtered = [c for c in filtered if c["status"] == status_filter]
    if partner_filter:
        filtered = [c for c in filtered if c["partner_name"].lower() == partner_filter.lower()]

    if not filtered:
        print("📭 No campaigns match your filters.")
        return

    # Summary stats
    total_budget = sum(c.get("approved_mdf_amount", 0) for c in filtered)
    total_revenue = sum(c.get("revenue_influenced", 0) for c in filtered)
    total_cost = sum(c.get("total_cost", 0) for c in filtered)

    print(f"{'ID':<12} {'Title':<35} {'Partner':<22} {'Type':<14} {'Status':<14} {'Budget':<12} {'Revenue':<12}")
    print("-" * 121)
    for c in filtered:
        budget = _fmt_currency(c.get("approved_mdf_amount", 0) or 0)
        rev = _fmt_currency(c.get("revenue_influenced", 0) or 0)
        print(f"{c['id']:<12} {c['title'][:34]:<35} {c['partner_name'][:21]:<22} {c['campaign_type']:<14} {c['status']:<14} {budget:<12} {rev:<12}")

    print(f"\n{'Summary:':<12} {len(filtered)} campaigns | Approved MDF: {_fmt_currency(total_budget)} | Revenue Influenced: {_fmt_currency(total_revenue)}")


def _show_campaign(args):
    campaigns = _load_campaigns()
    c = _find_campaign(campaigns, args.campaign_id)
    if not c:
        print(f"✗ Campaign '{args.campaign_id}' not found.")
        return

    print(f"""
{'='*60}
  {c['id']}: {c['title']}
{'='*60}

  Partner:       {c['partner_name']} ({c['partner_tier'].title()})
  Region:        {c.get('region', '—')}
  Channel Mgr:   {c.get('channel_manager', '—')}
  Campaign Type: {c.get('campaign_type_label', c['campaign_type'])}
  Status:        {c['status'].upper()}
  {'='*30}
  Dates:         {_fmt_date(c.get('start_date'))} → {_fmt_date(c.get('end_date'))}
  Total Cost:    {_fmt_currency(c.get('total_cost', 0))}
  Requested MDF: {_fmt_currency(c.get('requested_mdf_amount', 0))}
  Approved MDF:  {_fmt_currency(c.get('approved_mdf_amount', 0))}
  {'='*30}
  Description:   {c.get('description', '—')}
  Goals:         {c.get('goals', '—')}
  Target:        {c.get('target_audience', '—')}
  {'='*30}
  Results:
    Leads Generated:     {c.get('leads_generated', 0)}
    Opportunities:       {c.get('opportunities_created', 0)}
    Revenue Influenced:  {_fmt_currency(c.get('revenue_influenced', 0))}
    Impressions:         {c.get('impressions', 0):,}
    Engagement Rate:     {_pct(c.get('engagement_rate', 0))}
  {'='*30}
  Created: {_fmt_date(c.get('created_at'))}
  Updated: {_fmt_date(c.get('updated_at'))}
  Notes:   {c.get('notes', '—')}
""")

    activities = c.get("activities", [])
    if activities:
        print("  Activities / Milestones:")
        for a in activities:
            done = "✓" if a.get("completed") else "○"
            print(f"    {done} {a.get('date','')} — {a.get('description','')}")


def _update_campaign(args):
    campaigns = _load_campaigns()
    c = _find_campaign(campaigns, args.campaign_id)
    if not c:
        print(f"✗ Campaign '{args.campaign_id}' not found.")
        return

    changed = []
    if args.status:
        if args.status not in CAMPAIGN_STATUSES:
            print(f"✗ Invalid status '{args.status}'. Valid: {', '.join(CAMPAIGN_STATUSES)}")
            return
        old = c["status"]
        c["status"] = args.status
        changed.append(f"status: {old} → {args.status}")
    if args.notes:
        c["notes"] = (c.get("notes", "") + "\n" + args.notes).strip()
        changed.append("notes updated")

    if args.activity:
        activities = c.setdefault("activities", [])
        activities.append({
            "date": _today(),
            "description": args.activity,
            "completed": False,
        })
        changed.append(f"activity added: {args.activity}")

    if args.complete_activity:
        activities = c.get("activities", [])
        for a in activities:
            if a["description"] == args.complete_activity:
                a["completed"] = True
                changed.append(f"activity completed: {args.complete_activity}")
                break

    c["updated_at"] = datetime.now().isoformat()
    _save_campaigns(campaigns)

    if changed:
        print(f"✅ {args.campaign_id} updated:")
        for ch in changed:
            print(f"   • {ch}")
    else:
        print("ℹ️  No changes made.")


def _approve_campaign(args):
    campaigns = _load_campaigns()
    c = _find_campaign(campaigns, args.campaign_id)
    if not c:
        print(f"✗ Campaign '{args.campaign_id}' not found.")
        return

    partners = _load_partners()
    partner = _find_partner(partners, c["partner_name"])
    if not partner:
        print(f"✗ Partner '{c['partner_name']}' not found in partner database.")
        return

    # Check MDF remaining
    mdf_remaining = partner.get("mdf_annual", 0) - partner.get("mdf_ytd", 0)
    tier_limit = TIER_ALLOCATION_LIMITS.get(c["partner_tier"], 5000)

    if args.amount > mdf_remaining:
        print(f"✗ Insufficient MDF remaining for {c['partner_name']}:")
        print(f"   Remaining: {_fmt_currency(mdf_remaining)}")
        print(f"   Requested: {_fmt_currency(args.amount)}")
        print(f"   Annual Max: {_fmt_currency(partner.get('mdf_annual', 0))}")
        return

    if args.amount > tier_limit:
        print(f"⚠️  Amount {_fmt_currency(args.amount)} exceeds tier limit of {_fmt_currency(tier_limit)} for {c['partner_tier'].title()}.")
        print(f"   Consider {_fmt_currency(tier_limit)} or flag for executive approval.")
        return

    if args.reject:
        c["status"] = "rejected"
        c["notes"] = (c.get("notes", "") + "\n" + f"Rejected: {args.reason or 'No reason given'}").strip()
        print(f"❌ {args.campaign_id} rejected.")
    else:
        c["status"] = "approved"
        c["approved_mdf_amount"] = args.amount
        rate = TIER_REIMBURSEMENT_RATES.get(c["partner_tier"], 0.50)
        max_reimbursable = args.amount / rate if rate > 0 else args.amount

        # Update partner MDF YTD
        partner["mdf_ytd"] = partner.get("mdf_ytd", 0) + args.amount

        notes = f"Approved: ${args.amount:,.2f} MDF allocated (rate: {_pct(rate*100)})."
        if args.reason:
            notes += f" Reason: {args.reason}"
        c["notes"] = (c.get("notes", "") + "\n" + notes).strip()

        print(f"✅ {args.campaign_id} APPROVED — {_fmt_currency(args.amount)} MDF allocated")
        print(f"   Reimbursement rate: {_pct(rate*100)}")
        print(f"   Max reimbursable: {_fmt_currency(max_reimbursable)}")
        print(f"   Partner MDF remaining: {_fmt_currency(mdf_remaining - args.amount)}")

    c["updated_at"] = datetime.now().isoformat()
    _save_campaigns(campaigns)
    _save_partners(partners)


def _record_results(args):
    campaigns = _load_campaigns()
    c = _find_campaign(campaigns, args.campaign_id)
    if not c:
        print(f"✗ Campaign '{args.campaign_id}' not found.")
        return

    changed = []
    if args.leads is not None:
        c["leads_generated"] = args.leads
        changed.append(f"leads: {args.leads}")
    if args.opportunities is not None:
        c["opportunities_created"] = args.opportunities
        changed.append(f"opportunities: {args.opportunities}")
    if args.revenue is not None:
        c["revenue_influenced"] = args.revenue
        changed.append(f"revenue: {_fmt_currency(args.revenue)}")
    if args.impressions is not None:
        c["impressions"] = args.impressions
        changed.append(f"impressions: {args.impressions:,}")
    if args.engagement is not None:
        c["engagement_rate"] = args.engagement
        changed.append(f"engagement rate: {_pct(args.engagement)}")

    if args.notes:
        c["notes"] = (c.get("notes", "") + "\n" + args.notes).strip()
        changed.append("notes updated")

    if c["status"] in ("approved", "in_progress") and args.leads is not None:
        c["status"] = "completed"

    c["updated_at"] = datetime.now().isoformat()
    _save_campaigns(campaigns)

    if changed:
        print(f"✅ {args.campaign_id} results recorded:")
        for ch in changed:
            print(f"   • {ch}")
        print(f"\n   Now calculate ROI: pace roi {args.campaign_id}")
    else:
        print("ℹ️  No results recorded.")


def _close_campaign(args):
    campaigns = _load_campaigns()
    c = _find_campaign(campaigns, args.campaign_id)
    if not c:
        print(f"✗ Campaign '{args.campaign_id}' not found.")
        return

    # Auto-calculate ROI before closing
    if c.get("revenue_influenced", 0) > 0 and c.get("approved_mdf_amount", 0) > 0:
        roi = (c["revenue_influenced"] - c["approved_mdf_amount"]) / c["approved_mdf_amount"] * 100
        mdf_efficiency = c["revenue_influenced"] / c["approved_mdf_amount"] if c["approved_mdf_amount"] > 0 else 0
        c["roi_pct"] = round(roi, 1)
        c["mdf_efficiency_ratio"] = round(mdf_efficiency, 2)

        # Store in benchmarks
        benchmarks = _load_benchmarks()
        benchmarks.append({
            "campaign_id": c["id"],
            "title": c["title"],
            "partner_name": c["partner_name"],
            "partner_tier": c["partner_tier"],
            "campaign_type": c["campaign_type"],
            "total_cost": c.get("total_cost", 0),
            "mdf_spent": c.get("approved_mdf_amount", 0),
            "leads_generated": c.get("leads_generated", 0),
            "revenue_influenced": c.get("revenue_influenced", 0),
            "roi_pct": c.get("roi_pct", 0),
            "cost_per_lead": round(c.get("approved_mdf_amount", 0) / c.get("leads_generated", 1), 2) if c.get("leads_generated", 0) > 0 else 0,
            "revenue_per_dollar_mdf": round(c.get("revenue_influenced", 0) / c.get("approved_mdf_amount", 1), 2) if c.get("approved_mdf_amount", 0) > 0 else 0,
            "closed_at": _today(),
        })
        _save_benchmarks(benchmarks)

    c["status"] = "closed"
    c["updated_at"] = datetime.now().isoformat()
    _save_campaigns(campaigns)

    roi_str = f" | ROI: {_pct(c.get('roi_pct', 0))}" if c.get("roi_pct") else ""
    print(f"✅ {args.campaign_id} CLOSED{roi_str}")


# ── Budget & Recommendation ──────────────────────────────────────────────────

def _budget_recommend(args):
    partners = _load_partners()
    if not partners:
        print("⚠️  No partners loaded. Run 'pace demo' first.")
        return

    p = _find_partner(partners, args.partner)
    if not p:
        print(f"✗ Partner '{args.partner}' not found.")
        return

    tier = p["tier"]
    limit = TIER_ALLOCATION_LIMITS.get(tier, 5000)
    rate = TIER_REIMBURSEMENT_RATES.get(tier, 0.50)
    mdf_remaining = p.get("mdf_annual", 0) - p.get("mdf_ytd", 0)
    total_cost = args.total_cost

    # Recommendation algorithm
    base_recommendation = min(total_cost * rate, limit, mdf_remaining)

    # Bonus factors
    revenue_ratio = p.get("revenue_ytd", 0) / max(p.get("mdf_annual", 1), 1)
    performance_bonus = 0
    if revenue_ratio > 20:  # Top performers get higher allocation
        performance_bonus = base_recommendation * 0.2
    elif revenue_ratio > 10:
        performance_bonus = base_recommendation * 0.1

    recommended = min(base_recommendation + performance_bonus, limit, mdf_remaining)
    partner_share = total_cost - recommended

    print(f"""
{'='*60}
  Budget Recommendation — {p['name']}
{'='*60}

  Partner Tier:    {tier.title()}
  Campaign Cost:   {_fmt_currency(total_cost)}
  Revenue/MDF:     {revenue_ratio:.1f}x  {'★ High performer' if revenue_ratio > 15 else ''}
  {'='*30}
  Recommended Vendor Investment:  {_fmt_currency(round(recommended))}
  Recommended Partner Share:      {_fmt_currency(round(partner_share))}
  {'='*30}
  Constraints:
    Tier Limit:          {_fmt_currency(limit)} per campaign
    Reimbursement Rate:  {_pct(rate*100)}
    MDF Remaining:       {_fmt_currency(round(mdf_remaining))}
    Performance Bonus:   {'Yes (+20%)' if revenue_ratio > 20 else 'Yes (+10%)' if revenue_ratio > 10 else 'No'}
  {'='*30}
  Suggestion: Upload this recommendation with: pace campaign create ... --requested {round(recommended):,}
""")

    return round(recommended)


# ── ROI Calculation ──────────────────────────────────────────────────────────

def _calculate_roi(args):
    campaigns = _load_campaigns()
    c = _find_campaign(campaigns, args.campaign_id)
    if not c:
        print(f"✗ Campaign '{args.campaign_id}' not found.")
        return

    mdf_spent = c.get("approved_mdf_amount", 0) or 0
    total_cost = c.get("total_cost", 0) or 0
    revenue = c.get("revenue_influenced", 0) or 0
    leads = c.get("leads_generated", 0) or 0
    opps = c.get("opportunities_created", 0) or 0
    impressions = c.get("impressions", 0) or 0

    # Calculations
    mdf_roi = ((revenue - mdf_spent) / mdf_spent * 100) if mdf_spent > 0 else 0
    total_roi = ((revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
    cost_per_lead = mdf_spent / leads if leads > 0 else 0
    revenue_per_dollar = revenue / mdf_spent if mdf_spent > 0 else 0
    conversion_rate = (opps / leads * 100) if leads > 0 else 0
    cpl_value = total_cost / leads if leads > 0 else 0

    print(f"""
{'='*60}
  ROI Analysis — {c['id']}: {c['title']}
{'='*60}

  Partner: {c['partner_name']} | Type: {c.get('campaign_type_label', c['campaign_type'])}
  Status: {c['status'].upper()}
  {'='*30}
  Investment:
    Total Campaign Cost:     {_fmt_currency(total_cost)}
    Vendor MDF Allocation:   {_fmt_currency(mdf_spent)}
    Partner Contribution:    {_fmt_currency(total_cost - mdf_spent)}
  {'='*30}
  Results:
    Leads Generated:         {leads:,}
    Opportunities Created:   {opps:,}
    Revenue Influenced:      {_fmt_currency(revenue)}
    Impressions:             {impressions:,}
  {'='*30}
  Metrics:
    MDF ROI:                 {_pct(mdf_roi)}
    Total Campaign ROI:      {_pct(total_roi)}
    Revenue per MDF Dollar:  {_fmt_currency(revenue_per_dollar)}
    Cost per Lead (MDF):     {_fmt_currency(cost_per_lead)}
    Total Cost per Lead:     {_fmt_currency(cpl_value)}
    Lead-to-Opportunity:     {_pct(conversion_rate)}
  {'='*30}
  {'⚠️  Partner contributed MORE than vendor' if total_cost > mdf_spent * 2 else '✓ Good co-investment ratio' if total_cost > mdf_spent else '⚠️  Vendor covering most of cost — consider partner co-investment'}
""")

    c["roi_pct"] = round(mdf_roi, 1)
    c["mdf_efficiency_ratio"] = round(revenue_per_dollar, 2)
    c["updated_at"] = datetime.now().isoformat()
    _save_campaigns(campaigns)


# ── Benchmarking ──────────────────────────────────────────────────────────────

def _benchmark(args):
    benchmarks = _load_benchmarks()
    campaigns = _load_campaigns()

    if not benchmarks:
        # Generate from closed campaigns
        closed = [c for c in campaigns if c.get("status") == "closed" and c.get("revenue_influenced", 0) > 0]
        if not closed:
            print("📊 No completed campaigns to benchmark against.")
            print("   Complete a campaign first: pace campaign results <id> ... && pace campaign close <id>")
            return
        for c in closed:
            mdf = c.get("approved_mdf_amount", 0) or 0
            rev = c.get("revenue_influenced", 0) or 0
            leads = c.get("leads_generated", 0) or 0
            benchmarks.append({
                "campaign_id": c["id"],
                "title": c["title"],
                "partner_name": c["partner_name"],
                "partner_tier": c["partner_tier"],
                "campaign_type": c["campaign_type"],
                "total_cost": c.get("total_cost", 0) or 0,
                "mdf_spent": mdf,
                "leads_generated": leads,
                "revenue_influenced": rev,
                "roi_pct": ((rev - mdf) / mdf * 100) if mdf > 0 else 0,
                "cost_per_lead": round(mdf / leads, 2) if leads > 0 else 0,
                "revenue_per_dollar_mdf": round(rev / mdf, 2) if mdf > 0 else 0,
                "closed_at": _today(),
            })
        _save_benchmarks(benchmarks)

    if not benchmarks:
        print("📊 No benchmarks available yet.")
        return

    # Aggregate by type
    by_type = {}
    for b in benchmarks:
        t = b["campaign_type"]
        by_type.setdefault(t, []).append(b)

    print(f"""
{'='*60}
  PACE Benchmark — Campaign Performance
{'='*60}
  Total campaigns benchmarked: {len(benchmarks)}
""")

    print(f"{'Campaign Type':<20} {'Count':<7} {'Avg ROI':<12} {'Avg Rev/$MDF':<16} {'Avg CPL':<12}")
    print("-" * 67)
    for t, items in sorted(by_type.items()):
        avg_roi = sum(b["roi_pct"] for b in items) / len(items)
        avg_rev_per_dollar = sum(b["revenue_per_dollar_mdf"] for b in items) / len(items)
        avg_cpl = sum(b["cost_per_lead"] for b in items) / len(items)
        label = CAMPAIGN_TYPES.get(t, t)[:18]
        print(f"{label:<20} {len(items):<7} {_pct(avg_roi):<12} {_fmt_currency(avg_rev_per_dollar):<16} {_fmt_currency(avg_cpl):<12}")

    # Top performers
    if benchmarks:
        sorted_benchmarks = sorted(benchmarks, key=lambda b: b["roi_pct"], reverse=True)
        print(f"\n{'='*60}")
        print(f"  Top Performing Campaigns")
        print(f"{'='*60}")
        print(f"{'Campaign':<14} {'Title':<28} {'Type':<12} {'ROI':<10} {'Revenue':<14}")
        print("-" * 78)
        for b in sorted_benchmarks[:5]:
            print(f"{b['campaign_id']:<14} {b['title'][:27]:<28} {b['campaign_type']:<12} {_pct(b['roi_pct']):<10} {_fmt_currency(b['revenue_influenced']):<14}")


# ── Dashboard ────────────────────────────────────────────────────────────────

def _dashboard(args):
    campaigns = _load_campaigns()
    if not campaigns:
        print("📭 No campaigns. Run 'pace demo' first.")
        return

    by_status = {}
    by_type = {}
    by_partner = {}
    total_mdf_approved = 0
    total_revenue = 0
    total_spent = 0

    for c in campaigns:
        s = c["status"]
        by_status[s] = by_status.get(s, 0) + 1

        t = c["campaign_type"]
        by_type[t] = by_type.get(t, 0) + 1

        pn = c["partner_name"]
        by_partner.setdefault(pn, {"count": 0, "mdf": 0, "revenue": 0, "roi": 0})
        by_partner[pn]["count"] += 1
        by_partner[pn]["mdf"] += c.get("approved_mdf_amount", 0) or 0
        by_partner[pn]["revenue"] += c.get("revenue_influenced", 0) or 0

        total_mdf_approved += c.get("approved_mdf_amount", 0) or 0
        total_revenue += c.get("revenue_influenced", 0) or 0
        total_spent += c.get("total_cost", 0) or 0

    overall_roi = ((total_revenue - total_mdf_approved) / total_mdf_approved * 100) if total_mdf_approved > 0 else 0

    print(f"""
{'='*60}
  📊 PACE Dashboard — Partner Co-Marketing Campaigns
{'='*60}

  Portfolio Overview:
    Total Campaigns:         {len(campaigns)}
    Total MDF Approved:      {_fmt_currency(total_mdf_approved)}
    Total Revenue Influenced: {_fmt_currency(total_revenue)}
    Overall MDF ROI:         {_pct(overall_roi)}
    Revenue per MDF Dollar:  {_fmt_currency(total_revenue / total_mdf_approved) if total_mdf_approved > 0 else '—'}
  {'='*30}
""")

    print("  Campaigns by Status:")
    for s in CAMPAIGN_STATUSES:
        if by_status.get(s):
            print(f"    {s.replace('_',' ').title():<20} {by_status[s]:>3}")
    print()

    print(f"  Campaigns by Type:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        label = CAMPAIGN_TYPES.get(t, t)[:25]
        print(f"    {label:<25} {n:>3}")

    print(f"\n  Partner Activity:")
    print(f"  {'Partner':<25} {'Campaigns':<11} {'MDF Used':<14} {'Revenue':<14}")
    print("  " + "-" * 64)
    for pn, d in sorted(by_partner.items(), key=lambda x: -x[1]["revenue"]):
        p_roi = ((d["revenue"] - d["mdf"]) / d["mdf"] * 100) if d["mdf"] > 0 else 0
        print(f"  {pn[:24]:<25} {d['count']:<3} {'':>8} {_fmt_currency(d['mdf']):<14} {_fmt_currency(d['revenue']):<14}")

    active = sum(1 for c in campaigns if c["status"] == "in_progress")
    proposals = sum(1 for c in campaigns if c["status"] == "proposal" or c["status"] == "under_review")
    print(f"\n  ⚡ {active} active campaigns  |  {proposals} pending review")


# ── Demo Data ────────────────────────────────────────────────────────────────

def _load_demo(args):
    campaigns = _load_campaigns()
    if campaigns:
        print("⚠️  Campaigns already exist. Delete ~/.pace/ to reload demo data.")
        return

    partners = _load_partners()
    if not partners:
        _save_partners(DEFAULT_PARTNERS)
        partners = DEFAULT_PARTNERS
        print(f"✅ Loaded {len(partners)} sample partners.")

    # Create sample campaigns
    sample_campaigns = [
        {
            "id": "CAMP-0001",
            "title": "Q3 Cloud Migration Webinar Series",
            "partner_name": "TechSolvers Inc",
            "partner_tier": "platinum",
            "region": "West",
            "channel_manager": "Sarah Chen",
            "campaign_type": "webinar",
            "campaign_type_label": "Webinar / Online Event",
            "description": "3-part webinar series targeting enterprise IT leaders exploring cloud migration strategies.",
            "goals": "Generate 200+ qualified leads, 15+ opportunities",
            "target_audience": "Enterprise IT Directors, CTOs, Cloud Architects",
            "start_date": "2026-07-15",
            "end_date": "2026-09-15",
            "total_cost": 18000,
            "requested_mdf_amount": 10000,
            "approved_mdf_amount": 8000,
            "status": "in_progress",
            "leads_generated": 65,
            "opportunities_created": 4,
            "revenue_influenced": 0,
            "impressions": 12500,
            "engagement_rate": 3.2,
            "notes": "Webinar 1 completed with strong attendance (85 registrants, 62 attendees). Webinar 2 scheduled for Aug 1.",
            "activities": [
                {"date": "2026-07-01", "description": "Campaign brief finalized", "completed": True},
                {"date": "2026-07-10", "description": "Webinar 1: Cloud Strategy 101", "completed": True},
                {"date": "2026-08-01", "description": "Webinar 2: Migration Best Practices", "completed": False},
                {"date": "2026-09-01", "description": "Webinar 3: Post-Migration Optimization", "completed": False},
            ],
            "created_at": "2026-06-20T10:00:00",
            "updated_at": "2026-06-28T14:30:00",
        },
        {
            "id": "CAMP-0002",
            "title": "East Coast Partner Summit",
            "partner_name": "EnterpriseOps Group",
            "partner_tier": "platinum",
            "region": "Midwest",
            "channel_manager": "Mike Torres",
            "campaign_type": "event",
            "campaign_type_label": "Regional Event / Tradeshow",
            "description": "One-day partner summit in Chicago featuring product demos, networking, and partner awards.",
            "goals": "Strengthen partner relationships, generate 50+ leads, showcase new products",
            "target_audience": "Existing partners, prospective partners in Midwest region",
            "start_date": "2026-09-20",
            "end_date": "2026-09-20",
            "total_cost": 35000,
            "requested_mdf_amount": 12000,
            "approved_mdf_amount": 12000,
            "status": "approved",
            "leads_generated": 0,
            "opportunities_created": 0,
            "revenue_influenced": 0,
            "impressions": 0,
            "engagement_rate": 0,
            "notes": "Venue secured at Chicago Lakeside Center. Speaker lineup confirmed. Registration opening next week.",
            "activities": [
                {"date": "2026-07-01", "description": "Venue booked", "completed": True},
                {"date": "2026-07-15", "description": "Speaker confirmations due", "completed": False},
                {"date": "2026-08-01", "description": "Registration opens", "completed": False},
                {"date": "2026-09-20", "description": "Event day", "completed": False},
            ],
            "created_at": "2026-06-18T09:00:00",
            "updated_at": "2026-06-25T11:00:00",
        },
        {
            "id": "CAMP-0003",
            "title": "Q2 Email Nurture — Security Bundle",
            "partner_name": "DataBridge Partners",
            "partner_tier": "gold",
            "region": "Northeast",
            "channel_manager": "Sarah Chen",
            "campaign_type": "email",
            "campaign_type_label": "Joint Email Campaign",
            "description": "4-touch email nurture campaign promoting the new Security Bundle to SMB customers.",
            "goals": "Generate 100+ leads, 10 opportunities, $50K pipeline",
            "target_audience": "SMB IT Managers (500-2000 employees)",
            "start_date": "2026-05-01",
            "end_date": "2026-06-15",
            "total_cost": 5500,
            "requested_mdf_amount": 3000,
            "approved_mdf_amount": 2750,
            "status": "closed",
            "leads_generated": 128,
            "opportunities_created": 12,
            "revenue_influenced": 95000,
            "impressions": 45000,
            "engagement_rate": 5.8,
            "notes": "Strongest performing email was #3 (case study). Overall ROI excellent.",
            "activities": [
                {"date": "2026-05-01", "description": "Email 1: Problem awareness", "completed": True},
                {"date": "2026-05-15", "description": "Email 2: Solution overview", "completed": True},
                {"date": "2026-06-01", "description": "Email 3: Customer case study", "completed": True},
                {"date": "2026-06-15", "description": "Email 4: Offer + CTA", "completed": True},
            ],
            "created_at": "2026-04-25T08:00:00",
            "updated_at": "2026-06-20T16:00:00",
            "roi_pct": 3354.5,
            "mdf_efficiency_ratio": 34.55,
        },
        {
            "id": "CAMP-0004",
            "title": "Summer Digital Ad Campaign",
            "partner_name": "CloudSync Networks",
            "partner_tier": "gold",
            "region": "South",
            "channel_manager": "Mike Torres",
            "campaign_type": "digital_ad",
            "campaign_type_label": "Digital Advertising",
            "description": "LinkedIn and Google Ads campaign targeting healthcare IT decision-makers.",
            "goals": "50+ leads, 500K impressions, 3% CTR",
            "target_audience": "Healthcare IT Directors, CIOs",
            "start_date": "2026-08-01",
            "end_date": "2026-09-30",
            "total_cost": 12000,
            "requested_mdf_amount": 6000,
            "approved_mdf_amount": 5000,
            "status": "proposal",
            "leads_generated": 0,
            "opportunities_created": 0,
            "revenue_influenced": 0,
            "impressions": 0,
            "engagement_rate": 0,
            "notes": "Awaiting creative assets from partner marketing team.",
            "activities": [],
            "created_at": "2026-06-28T15:00:00",
            "updated_at": "2026-06-28T15:00:00",
        },
    ]

    _save_campaigns(sample_campaigns)
    print(f"✅ Loaded {len(sample_campaigns)} sample campaigns.")
    print(f"\n   Try:")
    print(f"     pace dashboard")
    print(f"     pace benchmark")
    print(f"     pace campaign show CAMP-0003  (completed, with ROI)")
    print(f"     pace roi CAMP-0003")
    print(f"     pace budget recommend --partner 'TechSolvers Inc' --total-cost 20000")
    print(f"     pace campaign create --title 'My Campaign' --partner 'TechSolvers Inc' --type webinar ...")


# ── MCP Server Mode ──────────────────────────────────────────────────────────

def _serve(args):
    """Start as MCP server for AI agent integration."""
    try:
        from mcp.server import Server
        from mcp.server.models import InitializationOptions
        import mcp.server.stdio
        import mcp.types as types
    except ImportError:
        print("✗ MCP package not installed. Run: pip install mcp")
        return

    server = Server("pace")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="create_campaign",
                description="Create a new co-marketing campaign proposal for a partner.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Campaign title"},
                        "partner_name": {"type": "string", "description": "Partner company name"},
                        "channel_manager": {"type": "string", "description": "Assigned channel manager"},
                        "campaign_type": {"type": "string", "enum": list(CAMPAIGN_TYPES.keys()), "description": "Type of campaign"},
                        "description": {"type": "string", "description": "Campaign description"},
                        "goals": {"type": "string", "description": "Campaign goals"},
                        "target_audience": {"type": "string", "description": "Target audience"},
                        "start_date": {"type": "string", "description": "Start date (ISO format)"},
                        "end_date": {"type": "string", "description": "End date (ISO format)"},
                        "total_cost": {"type": "number", "description": "Total campaign cost"},
                        "requested_mdf_amount": {"type": "number", "description": "MDF amount requested from vendor"},
                    },
                    "required": ["title", "partner_name", "campaign_type", "total_cost"],
                },
            ),
            types.Tool(
                name="list_campaigns",
                description="List campaigns with optional status and partner filters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": CAMPAIGN_STATUSES, "description": "Filter by status"},
                        "partner_name": {"type": "string", "description": "Filter by partner name"},
                    },
                },
            ),
            types.Tool(
                name="get_campaign",
                description="View full details of a specific campaign.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign ID (e.g., CAMP-0001)"},
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="update_campaign",
                description="Update campaign status, notes, or add activities.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign ID"},
                        "status": {"type": "string", "enum": CAMPAIGN_STATUSES, "description": "New status"},
                        "notes": {"type": "string", "description": "Additional notes"},
                        "activity": {"type": "string", "description": "Add a milestone/activity"},
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="approve_campaign",
                description="Approve campaign and allocate MDF budget. Can also reject.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign ID"},
                        "amount": {"type": "number", "description": "MDF amount to allocate"},
                        "reject": {"type": "boolean", "description": "Set to true to reject instead of approve"},
                        "reason": {"type": "string", "description": "Reason for approval or rejection"},
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="record_campaign_results",
                description="Record campaign performance results (leads, revenue, impressions).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign ID"},
                        "leads_generated": {"type": "integer", "description": "Number of leads generated"},
                        "opportunities_created": {"type": "integer", "description": "Number of opportunities created"},
                        "revenue_influenced": {"type": "number", "description": "Revenue influenced ($)"},
                        "impressions": {"type": "integer", "description": "Total impressions"},
                        "engagement_rate": {"type": "number", "description": "Engagement rate (%)"},
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="calculate_roi",
                description="Calculate ROI for a campaign based on recorded results.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign ID"},
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="close_campaign",
                description="Close a campaign, storing benchmark data for future comparison.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign ID"},
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="recommend_budget",
                description="Recommend optimal MDF budget allocation for a partner campaign.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "partner_name": {"type": "string", "description": "Partner company name"},
                        "total_cost": {"type": "number", "description": "Total campaign cost"},
                    },
                    "required": ["partner_name", "total_cost"],
                },
            ),
            types.Tool(
                name="get_benchmarks",
                description="View campaign performance benchmarks across campaign types.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="get_dashboard",
                description="Get portfolio dashboard with aggregated metrics.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="load_demo_data",
                description="Load sample partners and campaigns for testing.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        result = _handle_mcp_tool(name, arguments)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    async def run():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, InitializationOptions(
                server_name="pace",
                server_version="1.0.0",
            ))

    import asyncio
    asyncio.run(run())


def _handle_mcp_tool(name: str, args: dict) -> dict:
    """Handle MCP tool calls and return structured results."""
    class MockArgs:
        pass

    p = MockArgs()

    if name == "create_campaign":
        p.title = args.get("title", "Untitled Campaign")
        p.partner = args.get("partner_name", "")
        p.manager = args.get("channel_manager", "")
        p.type = args.get("campaign_type", "other")
        p.description = args.get("description", "")
        p.goals = args.get("goals", "")
        p.audience = args.get("target_audience", "")
        p.start = args.get("start_date", "")
        p.end = args.get("end_date", "")
        p.cost = args.get("total_cost", 0)
        p.requested = args.get("requested_mdf_amount", 0)
        _create_campaign(p)
        campaigns = _load_campaigns()
        return {"success": True, "campaign": campaigns[-1] if campaigns else None}

    elif name == "list_campaigns":
        p.status = args.get("status")
        p.partner = args.get("partner_name")
        campaigns = _load_campaigns()
        filtered = campaigns
        if p.status:
            filtered = [c for c in filtered if c["status"] == p.status]
        if p.partner:
            filtered = [c for c in filtered if c["partner_name"].lower() == p.partner.lower()]
        return {"success": True, "count": len(filtered), "campaigns": filtered}

    elif name == "get_campaign":
        p.campaign_id = args["campaign_id"]
        campaigns = _load_campaigns()
        c = _find_campaign(campaigns, p.campaign_id)
        return {"success": c is not None, "campaign": c}

    elif name == "update_campaign":
        p.campaign_id = args["campaign_id"]
        p.status = args.get("status")
        p.notes = args.get("notes")
        p.activity = args.get("activity")
        p.complete_activity = args.get("complete_activity")
        _update_campaign(p)
        campaigns = _load_campaigns()
        c = _find_campaign(campaigns, p.campaign_id)
        return {"success": True, "campaign": c}

    elif name == "approve_campaign":
        p.campaign_id = args["campaign_id"]
        p.amount = args.get("amount", 0)
        p.reject = args.get("reject", False)
        p.reason = args.get("reason")
        _approve_campaign(p)
        campaigns = _load_campaigns()
        c = _find_campaign(campaigns, p.campaign_id)
        return {"success": True, "campaign": c}

    elif name == "record_campaign_results":
        p.campaign_id = args["campaign_id"]
        p.leads = args.get("leads_generated")
        p.opportunities = args.get("opportunities_created")
        p.revenue = args.get("revenue_influenced")
        p.impressions = args.get("impressions")
        p.engagement = args.get("engagement_rate")
        p.notes = args.get("notes")
        _record_results(p)
        campaigns = _load_campaigns()
        c = _find_campaign(campaigns, p.campaign_id)
        return {"success": True, "campaign": c}

    elif name == "calculate_roi":
        p.campaign_id = args["campaign_id"]
        campaigns = _load_campaigns()
        c = _find_campaign(campaigns, p.campaign_id)
        if not c:
            return {"success": False, "error": "Campaign not found"}
        mdf_spent = c.get("approved_mdf_amount", 0) or 0
        total_cost = c.get("total_cost", 0) or 0
        revenue = c.get("revenue_influenced", 0) or 0
        leads = c.get("leads_generated", 0) or 0
        mdf_roi = ((revenue - mdf_spent) / mdf_spent * 100) if mdf_spent > 0 else 0
        cost_per_lead = mdf_spent / leads if leads > 0 else 0
        return {
            "success": True,
            "campaign_id": p.campaign_id,
            "mdf_roi_pct": round(mdf_roi, 1),
            "cost_per_lead": round(cost_per_lead, 2),
            "revenue_per_mdf_dollar": round(revenue / mdf_spent, 2) if mdf_spent > 0 else 0,
        }

    elif name == "close_campaign":
        p.campaign_id = args["campaign_id"]
        _close_campaign(p)
        return {"success": True}

    elif name == "recommend_budget":
        p.partner = args["partner_name"]
        p.total_cost = args["total_cost"]
        recommended = _budget_recommend(p)
        return {"success": True, "recommended_amount": recommended}

    elif name == "get_benchmarks":
        benchmarks = _load_benchmarks()
        campaigns = _load_campaigns()
        if not benchmarks:
            closed = [c for c in campaigns if c.get("status") == "closed" and c.get("revenue_influenced", 0) > 0]
            if closed:
                for c in closed:
                    mdf = c.get("approved_mdf_amount", 0) or 0
                    rev = c.get("revenue_influenced", 0) or 0
                    leads = c.get("leads_generated", 0) or 0
                    benchmarks.append({
                        "campaign_id": c["id"],
                        "title": c["title"],
                        "partner_name": c["partner_name"],
                        "campaign_type": c["campaign_type"],
                        "roi_pct": ((rev - mdf) / mdf * 100) if mdf > 0 else 0,
                        "cost_per_lead": round(mdf / leads, 2) if leads > 0 else 0,
                    })
                _save_benchmarks(benchmarks)
        return {"success": True, "benchmarks": benchmarks}

    elif name == "get_dashboard":
        campaigns = _load_campaigns()
        by_status = {}
        for c in campaigns:
            s = c["status"]
            by_status[s] = by_status.get(s, 0) + 1
        total_mdf = sum(c.get("approved_mdf_amount", 0) or 0 for c in campaigns)
        total_rev = sum(c.get("revenue_influenced", 0) or 0 for c in campaigns)
        return {
            "success": True,
            "total_campaigns": len(campaigns),
            "by_status": by_status,
            "total_mdf_approved": total_mdf,
            "total_revenue_influenced": total_rev,
        }

    elif name == "load_demo_data":
        class DemoArgs:
            pass
        _load_demand(DemoArgs())
        return {"success": True, "message": "Demo data loaded"}

    return {"success": False, "error": f"Unknown tool: {name}"}


# ── CLI Parser ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="pace",
        description="PACE — Partner Co-Marketing Campaign Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(__doc__),
    )

    sub = parser.add_subparsers(dest="command", help="Command")

    # demo
    sub.add_parser("demo", help="Load sample partners and campaigns")

    # campaign
    cp = sub.add_parser("campaign", help="Manage campaigns")
    csub = cp.add_subparsers(dest="action", help="Campaign action")

    # campaign create
    cc = csub.add_parser("create", help="Create a new campaign")
    cc.add_argument("--title", required=True)
    cc.add_argument("--partner", required=True)
    cc.add_argument("--manager", default="")
    cc.add_argument("--type", required=True, choices=list(CAMPAIGN_TYPES.keys()))
    cc.add_argument("--description", default="")
    cc.add_argument("--goals", default="")
    cc.add_argument("--audience", default="")
    cc.add_argument("--start", default="")
    cc.add_argument("--end", default="")
    cc.add_argument("--cost", type=float, default=0)
    cc.add_argument("--requested", type=float, default=0)

    # campaign list
    cl = csub.add_parser("list", help="List campaigns")
    cl.add_argument("--status", choices=CAMPAIGN_STATUSES, default="")
    cl.add_argument("--partner", default="")

    # campaign show
    cs = csub.add_parser("show", help="Show campaign details")
    cs.add_argument("campaign_id")

    # campaign update
    cu = csub.add_parser("update", help="Update campaign")
    cu.add_argument("campaign_id")
    cu.add_argument("--status", choices=CAMPAIGN_STATUSES)
    cu.add_argument("--notes")
    cu.add_argument("--activity")
    cu.add_argument("--complete-activity")

    # campaign approve
    ca = csub.add_parser("approve", help="Approve campaign & allocate budget")
    ca.add_argument("campaign_id")
    ca.add_argument("--amount", type=float, default=0)
    ca.add_argument("--reject", action="store_true")
    ca.add_argument("--reason", default="")

    # campaign results
    cr = csub.add_parser("results", help="Record campaign results")
    cr.add_argument("campaign_id")
    cr.add_argument("--leads", type=int, default=None)
    cr.add_argument("--opportunities", type=int, default=None)
    cr.add_argument("--revenue", type=float, default=None)
    cr.add_argument("--impressions", type=int, default=None)
    cr.add_argument("--engagement", type=float, default=None)
    cr.add_argument("--notes", default="")

    # campaign close
    ccl = csub.add_parser("close", help="Close campaign (stores benchmark data)")
    ccl.add_argument("campaign_id")

    # roi
    roi = sub.add_parser("roi", help="Calculate campaign ROI")
    roi.add_argument("campaign_id")

    # budget recommend
    br = sub.add_parser("budget", help="Budget recommendations")
    bsub = br.add_subparsers(dest="action")
    brc = bsub.add_parser("recommend", help="Recommend budget allocation")
    brc.add_argument("--partner", required=True)
    brc.add_argument("--total-cost", type=float, required=True)

    # benchmark
    sub.add_parser("benchmark", help="View campaign performance benchmarks")

    # dashboard
    sub.add_parser("dashboard", help="View portfolio dashboard")

    # serve
    serve_p = sub.add_parser("serve", help="Start MCP server for AI agent integration")

    args = parser.parse_args()

    _ensure_data_dir()

    if args.command == "demo":
        _load_demo(args)
    elif args.command == "campaign":
        if not args.action:
            cp.print_help()
            return
        if args.action == "create":
            _create_campaign(args)
        elif args.action == "list":
            _list_campaigns(args)
        elif args.action == "show":
            _show_campaign(args)
        elif args.action == "update":
            _update_campaign(args)
        elif args.action == "approve":
            _approve_campaign(args)
        elif args.action == "results":
            _record_results(args)
        elif args.action == "close":
            _close_campaign(args)
        else:
            cp.print_help()
    elif args.command == "roi":
        _calculate_roi(args)
    elif args.command == "budget":
        if not args.action:
            br.print_help()
            return
        if args.action == "recommend":
            _budget_recommend(args)
    elif args.command == "benchmark":
        _benchmark(args)
    elif args.command == "dashboard":
        _dashboard(args)
    elif args.command == "serve":
        _serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
