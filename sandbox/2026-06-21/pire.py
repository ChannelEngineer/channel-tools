#!/usr/bin/env python3
"""
PIRE — Partner Incentive & Rebate Engine
=========================================
A CLI tool for designing, managing, and calculating
channel partner incentive programs, rebates, and MDF claims.

Usage:
  pire program create <name> [--tiers TIERS_JSON] [--rules RULES_JSON]
  pire program list
  pire program show <name>
  pire rebate calculate <program_name> <partner_name> <transactions_file>
  pire mdf submit <program_name> <partner_name> <amount> [--description ...]
  pire mdf list [--program <name>] [--partner <name>] [--status <status>]
  pire mdf approve <claim_id>
  pire mdf reject <claim_id>
  pire payout generate <program_name> [--period <period>]
  pire report program <name>
  pire report partner <name>
  pire serve            # Start MCP server mode

Exit codes:
  0 — success
  1 — validation/data error
  2 — argument error
"""

import argparse
import json
import csv
import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any

# ── State ────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".pire"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROGRAMS_FILE = DATA_DIR / "programs.json"
PARTNERS_FILE = DATA_DIR / "partners.json"
MDF_CLAIMS_FILE = DATA_DIR / "mdf_claims.json"
PAYOUTS_FILE = DATA_DIR / "payouts.json"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"

# ── Helpers ──────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | list:
    if path.exists() and path.stat().st_size > 0:
        with open(path) as f:
            return json.load(f)
    return [] if "claims" in path.name or "transactions" in path.name or "payouts" in path.name else {}

def _save_json(path: Path, data: Any) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def _ts() -> str:
    return datetime.now().isoformat()

def _find_item(items: list, key: str, value: str) -> dict | None:
    return next((i for i in items if i.get(key) == value), None)

def _validate_tiers(tiers: list) -> list:
    """Validate and normalize tier definitions."""
    required = {"name", "min_revenue", "rebate_pct"}
    for t in tiers:
        missing = required - set(t.keys())
        if missing:
            raise ValueError(f"Tier '{t.get('name', '?')}' missing: {', '.join(missing)}")
        t["rebate_pct"] = float(t["rebate_pct"])
        t["min_revenue"] = float(t["min_revenue"])
    return sorted(tiers, key=lambda x: x["min_revenue"])

# ── Core Logic ───────────────────────────────────────────────────────

def _get_program(name: str) -> dict:
    programs = _load_json(PROGRAMS_FILE)
    if name not in programs:
        print(f"Error: Program '{name}' not found.", file=sys.stderr)
        sys.exit(1)
    return programs[name]

def cmd_program_create(args) -> None:
    programs = _load_json(PROGRAMS_FILE)
    if args.name in programs:
        print(f"Error: Program '{args.name}' already exists.", file=sys.stderr)
        sys.exit(1)

    # Parse tiers
    if args.tiers:
        tiers = json.loads(args.tiers) if isinstance(args.tiers, str) else args.tiers
        tiers = _validate_tiers(tiers)
    else:
        # Default tier structure
        tiers = [
            {"name": "Silver", "min_revenue": 0, "rebate_pct": 2.0, "description": "Entry-level partner rebate"},
            {"name": "Gold", "min_revenue": 100000, "rebate_pct": 4.0, "description": "Mid-tier partner rebate"},
            {"name": "Platinum", "min_revenue": 500000, "rebate_pct": 7.0, "description": "Top-tier partner rebate"},
            {"name": "Elite", "min_revenue": 2000000, "rebate_pct": 10.0, "description": "Flagship partner rebate"},
        ]

    # Parse rules
    if args.rules:
        rules = json.loads(args.rules) if isinstance(args.rules, str) else args.rules
    else:
        rules = {
            "minimum_transaction": 1000,
            "deal_registration_bonus_pct": 2.0,
            "new_logo_bonus_pct": 3.0,
            "mdf_budget_pct_of_revenue": 4.0,
            "mdf_reimbursement_cap_pct": 75.0,
            "spiff_amount": 500,
            "accelerator_thresholds": [
                {"above_revenue": 1000000, "bonus_pct": 3.0},
                {"above_revenue": 3000000, "bonus_pct": 5.0},
            ],
            "quarterly_minimum_revenue": 25000,
            "payout_terms_days": 30,
            "program_currency": "USD",
            "allow_stacking": True,
        }

    program = {
        "name": args.name,
        "description": args.description or f"{args.name} partner incentive program",
        "created": _ts(),
        "updated": _ts(),
        "status": "active",
        "tiers": tiers,
        "rules": rules,
        "partner_count": 0,
    }
    programs[args.name] = program
    _save_json(PROGRAMS_FILE, programs)
    print(f"✅ Program '{args.name}' created with {len(tiers)} tiers.")
    for t in tiers:
        print(f"   {t['name']}: ≥${t['min_revenue']:,.0f} rev → {t['rebate_pct']}% rebate")
    print(f"   MDF budget: {rules['mdf_budget_pct_of_revenue']}% of revenue")
    print(f"   Deal reg bonus: +{rules['deal_registration_bonus_pct']}%")
    print(f"   New logo bonus: +{rules['new_logo_bonus_pct']}%")

def cmd_program_list(args) -> None:
    programs = _load_json(PROGRAMS_FILE)
    if not programs:
        print("No programs defined. Use 'pire program create' to add one.")
        return
    print(f"{'Program':<20} {'Tiers':<8} {'Partners':<10} {'Status':<10} {'Created'}")
    print("-" * 70)
    for name, p in sorted(programs.items()):
        print(f"{name:<20} {len(p['tiers']):<8} {p.get('partner_count', 0):<10} {p.get('status', 'active'):<10} {p.get('created', '?')[:10]}")

def cmd_program_show(args) -> None:
    program = _get_program(args.name)
    print(f"\n📋 Program: {program['name']}")
    print(f"   Status: {program.get('status', 'active')}")
    print(f"   Description: {program.get('description', '')}")
    print(f"   Created: {program.get('created', '?')[:10]}")
    print(f"\n   Tiers:")
    for t in program["tiers"]:
        desc = t.get("description", "")
        print(f"     {t['name']:<12} ≥${t['min_revenue']:>10,.0f}  → {t['rebate_pct']}%{'  ' + desc if desc else ''}")
    rules = program["rules"]
    print(f"\n   Rules:")
    print(f"     Min transaction:       ${rules.get('minimum_transaction', 0):,.0f}")
    print(f"     Deal reg bonus:        +{rules.get('deal_registration_bonus_pct', 0)}%")
    print(f"     New logo bonus:        +{rules.get('new_logo_bonus_pct', 0)}%")
    print(f"     MDF budget:            {rules.get('mdf_budget_pct_of_revenue', 0)}% of revenue")
    print(f"     MDF reimbursement cap: {rules.get('mdf_reimbursement_cap_pct', 0)}%")
    print(f"     SPIFF amount:          ${rules.get('spiff_amount', 0):,.0f}")
    print(f"     Payout terms:          {rules.get('payout_terms_days', 30)} days")
    accels = rules.get("accelerator_thresholds", [])
    if accels:
        print(f"     Accelerators:")
        for a in accels:
            print(f"       Revenue > ${a['above_revenue']:>10,.0f}: +{a['bonus_pct']}%")


def cmd_rebate_calculate(args) -> None:
    """Calculate earned rebates for a partner in a program."""
    program = _get_program(args.program_name)

    # Load transactions
    try:
        with open(args.transactions_file) as f:
            if args.transactions_file.endswith(".csv"):
                transactions = list(csv.DictReader(f))
            else:
                transactions = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{args.transactions_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not transactions:
        print("No transactions found.")
        return

    # Calculate metrics
    total_revenue = sum(float(t.get("revenue", t.get("value", 0))) for t in transactions)
    gross_revenue = total_revenue
    deal_reg_deals = [t for t in transactions if t.get("is_registered", "").lower() in ("yes", "true", "1")]
    new_logo_deals = [t for t in transactions if t.get("is_new_logo", "").lower() in ("yes", "true", "1")]
    registered_revenue = sum(float(t.get("revenue", t.get("value", 0))) for t in deal_reg_deals)
    new_logo_revenue = sum(float(t.get("revenue", t.get("value", 0))) for t in new_logo_deals)
    total_transactions = len(transactions)

    # Find applicable tier
    tiers = sorted(program["tiers"], key=lambda t: t["min_revenue"])
    selected_tier = tiers[0]
    for t in reversed(tiers):
        if total_revenue >= t["min_revenue"]:
            selected_tier = t
            break

    # Calculate base rebate
    base_rebate = total_revenue * (selected_tier["rebate_pct"] / 100)
    base_rate = selected_tier["rebate_pct"]

    # Calculate bonuses
    rules = program["rules"]
    deal_reg_bonus = registered_revenue * (rules.get("deal_registration_bonus_pct", 0) / 100)
    new_logo_bonus = new_logo_revenue * (rules.get("new_logo_bonus_pct", 0) / 100)

    # Accelerator check
    accel_bonus = 0
    accel_pct = 0
    for a in rules.get("accelerator_thresholds", []):
        if total_revenue >= a["above_revenue"]:
            accel_bonus = total_revenue * (a["bonus_pct"] / 100)
            accel_pct = a["bonus_pct"]

    # SPIFFs for new logos
    spiff_count = len(new_logo_deals)
    spiff_total = spiff_count * rules.get("spiff_amount", 0)

    total_payout = base_rebate + deal_reg_bonus + new_logo_bonus + accel_bonus + spiff_total
    effective_rate = (total_payout / total_revenue * 100) if total_revenue > 0 else 0

    # Save to transactions history
    all_txns = _load_json(TRANSACTIONS_FILE)
    calc = {
        "partner": args.partner_name,
        "program": args.program_name,
        "period": str(date.today()),
        "total_revenue": total_revenue,
        "tier": selected_tier["name"],
        "base_rate": base_rate,
        "base_rebate": base_rebate,
        "deal_reg_bonus": deal_reg_bonus,
        "new_logo_bonus": new_logo_bonus,
        "accel_bonus": accel_bonus,
        "spiff_total": spiff_total,
        "total_payout": total_payout,
        "effective_rate": round(effective_rate, 2),
        "transactions_count": total_transactions,
        "calculated_at": _ts(),
    }
    all_txns.append(calc)
    _save_json(TRANSACTIONS_FILE, all_txns)

    # Report
    print(f"\n{'='*60}")
    print(f"  REBATE CALCULATION")
    print(f"  Program: {args.program_name}")
    print(f"  Partner: {args.partner_name}")
    print(f"  Period:  {date.today()}")
    print(f"{'='*60}")
    print(f"  Total Revenue:           ${total_revenue:>12,.2f}")
    print(f"  Transactions:            {total_transactions:>12}")
    print(f"  Tier Applied:            {selected_tier['name']:>12}")
    print(f"  ─────────────────────────────────────────")
    print(f"  Base Rebate ({base_rate}%):         ${base_rebate:>12,.2f}")
    if deal_reg_bonus > 0:
        print(f"  + Deal Reg Bonus:         ${deal_reg_bonus:>12,.2f}")
    if new_logo_bonus > 0:
        print(f"  + New Logo Bonus:         ${new_logo_bonus:>12,.2f}")
    if accel_bonus > 0:
        print(f"  + Accelerator ({accel_pct}%):      ${accel_bonus:>12,.2f}")
    if spiff_total > 0:
        print(f"  + SPIFFs ({spiff_count} deals):     ${spiff_total:>12,.2f}")
    print(f"  ─────────────────────────────────────────")
    print(f"  TOTAL PAYOUT:            ${total_payout:>12,.2f}")
    print(f"  Effective Rate:          {effective_rate:>12.2f}%")
    print(f"{'='*60}")
    print(f"  (saved to {TRANSACTIONS_FILE})")


def cmd_mdf_submit(args) -> None:
    """Submit an MDF claim."""
    program = _get_program(args.program_name)
    claims = _load_json(MDF_CLAIMS_FILE)

    claim = {
        "id": f"MDF-{len(claims)+1:04d}",
        "program": args.program_name,
        "partner": args.partner_name,
        "amount": float(args.amount),
        "description": args.description or "MDF claim",
        "status": "pending",
        "submitted": _ts(),
        "updated": _ts(),
    }

    # Validate against program rules
    rules = program["rules"]
    mdf_budget_pct = rules.get("mdf_budget_pct_of_revenue", 0)
    reimbursement_cap = rules.get("mdf_reimbursement_cap_pct", 100)

    # Check if partner has transactions to estimate budget
    partner_txns = [t for t in _load_json(TRANSACTIONS_FILE) if t.get("partner") == args.partner_name and t.get("program") == args.program_name]
    est_revenue = sum(t.get("total_revenue", 0) for t in partner_txns)
    mdf_budget = est_revenue * (mdf_budget_pct / 100)

    # Check existing approved claims
    approved_claims = [c for c in claims if c.get("partner") == args.partner_name and c.get("program") == args.program_name and c.get("status") == "approved"]
    used_mdf = sum(c.get("amount", 0) for c in approved_claims)

    if mdf_budget > 0 and (used_mdf + claim["amount"]) > mdf_budget:
        overage = (used_mdf + claim["amount"]) - mdf_budget
        claim["over_budget"] = True
        claim["overage"] = round(overage, 2)
        claim["mdf_budget"] = round(mdf_budget, 2)
        claim["used_before"] = round(used_mdf, 2)

    claims.append(claim)
    _save_json(MDF_CLAIMS_FILE, claims)
    print(f"✅ MDF claim {claim['id']} submitted.")
    print(f"   Partner:     {args.partner_name}")
    print(f"   Amount:      ${float(args.amount):,.2f}")
    print(f"   Status:      pending")
    if claim.get("over_budget"):
        print(f"   ⚠️  OVER BUDGET: ${claim['overage']:,.2f} over allocated MDF ${mdf_budget:,.2f}")
    print(f"   Description: {claim['description']}")


def cmd_mdf_list(args) -> None:
    claims = _load_json(MDF_CLAIMS_FILE)
    if args.program:
        claims = [c for c in claims if c.get("program") == args.program]
    if args.partner:
        claims = [c for c in claims if c.get("partner") == args.partner]
    if args.status:
        claims = [c for c in claims if c.get("status") == args.status]

    if not claims:
        print("No MDF claims found matching criteria.")
        return

    print(f"{'ID':<12} {'Program':<15} {'Partner':<18} {'Amount':<12} {'Status':<12} {'Date':<12}")
    print("-" * 85)
    for c in claims:
        d = c.get("submitted", "")[:10]
        flag = " ⚠️" if c.get("over_budget") else ""
        print(f"{c['id']:<12} {c.get('program',''):<15} {c.get('partner',''):<18} ${c['amount']:<9,.2f}{flag} {c.get('status',''):<12} {d:<12}")


def cmd_mdf_approve(args) -> None:
    claims = _load_json(MDF_CLAIMS_FILE)
    claim = _find_item(claims, "id", args.claim_id)
    if not claim:
        print(f"Error: Claim '{args.claim_id}' not found.", file=sys.stderr)
        sys.exit(1)
    if claim["status"] != "pending":
        print(f"Error: Claim is already '{claim['status']}'.", file=sys.stderr)
        sys.exit(1)
    claim["status"] = "approved"
    claim["updated"] = _ts()
    claim["approved_at"] = _ts()
    _save_json(MDF_CLAIMS_FILE, claims)
    print(f"✅ MDF claim {args.claim_id} approved — ${claim['amount']:,.2f} released.")


def cmd_mdf_reject(args) -> None:
    claims = _load_json(MDF_CLAIMS_FILE)
    claim = _find_item(claims, "id", args.claim_id)
    if not claim:
        print(f"Error: Claim '{args.claim_id}' not found.", file=sys.stderr)
        sys.exit(1)
    if claim["status"] != "pending":
        print(f"Error: Claim is already '{claim['status']}'.", file=sys.stderr)
        sys.exit(1)
    claim["status"] = "rejected"
    claim["updated"] = _ts()
    _save_json(MDF_CLAIMS_FILE, claims)
    print(f"❌ MDF claim {args.claim_id} rejected.")


def cmd_payout_generate(args) -> None:
    """Generate a payout report for a program."""
    program = _get_program(args.program_name)
    txns = [t for t in _load_json(TRANSACTIONS_FILE) if t.get("program") == args.program_name]
    claims = [c for c in _load_json(MDF_CLAIMS_FILE) if c.get("program") == args.program_name and c.get("status") == "approved"]

    if args.partner:
        txns = [t for t in txns if t.get("partner") == args.partner]
        claims = [c for c in claims if c.get("partner") == args.partner]

    # Group by partner
    partners = set(t.get("partner") for t in txns)
    if args.partner:
        partners = {args.partner}

    period = args.period or str(date.today())

    payouts = []
    for partner in sorted(partners):
        p_txns = [t for t in txns if t.get("partner") == partner]
        if not p_txns:
            continue
        latest = p_txns[-1]
        p_claims = [c for c in claims if c.get("partner") == partner]
        mdf_total = sum(c["amount"] for c in p_claims) if claims else 0

        payout = {
            "partner": partner,
            "program": args.program_name,
            "period": period,
            "total_revenue": sum(t["total_revenue"] for t in p_txns),
            "rebate_payout": sum(t["total_payout"] for t in p_txns),
            "mdf_approved": mdf_total,
            "tier": latest.get("tier", "Unknown"),
            "effective_rate": latest.get("effective_rate", 0),
            "generated_at": _ts(),
        }
        payouts.append(payout)

    # Save
    all_payouts = _load_json(PAYOUTS_FILE)
    all_payouts.extend(payouts)
    _save_json(PAYOUTS_FILE, all_payouts)

    total_rebate = sum(p["rebate_payout"] for p in payouts)
    total_mdf = sum(p["mdf_approved"] for p in payouts)
    total_revenue = sum(p["total_revenue"] for p in payouts)

    print(f"\n{'='*70}")
    print(f"  PAYOUT REPORT — {args.program_name}")
    print(f"  Period: {period}")
    print(f"  Partners: {len(payouts)}")
    print(f"{'='*70}")
    print(f"  {'Partner':<20} {'Revenue':>12} {'Rebate':>12} {'MDF':>10} {'Rate':>8} {'Tier':>10}")
    print(f"  {'─'*70}")
    for p in payouts:
        print(f"  {p['partner']:<20} ${p['total_revenue']:>9,.0f} ${p['rebate_payout']:>9,.0f} ${p['mdf_approved']:>7,.0f} {p['effective_rate']:>6.1f}% {p['tier']:>10}")
    print(f"  {'─'*70}")
    print(f"  {'TOTAL':<20} ${total_revenue:>9,.0f} ${total_rebate:>9,.0f} ${total_mdf:>7,.0f}")
    print(f"{'='*70}")
    print(f"  (saved to {PAYOUTS_FILE})")


def cmd_report_program(args) -> None:
    """Generate comprehensive program report."""
    program = _get_program(args.name)
    txns = [t for t in _load_json(TRANSACTIONS_FILE) if t.get("program") == args.name]
    claims = [c for c in _load_json(MDF_CLAIMS_FILE) if c.get("program") == args.name]
    payouts = [p for p in _load_json(PAYOUTS_FILE) if p.get("program") == args.name]

    total_revenue = sum(t["total_revenue"] for t in txns)
    total_payout = sum(t["total_payout"] for t in txns)
    unique_partners = len(set(t["partner"] for t in txns))
    total_mdf_claimed = sum(c["amount"] for c in claims if c["status"] in ("pending", "approved"))
    total_mdf_approved = sum(c["amount"] for c in claims if c["status"] == "approved")
    roi = ((total_revenue - total_payout - total_mdf_approved) / (total_payout + total_mdf_approved) * 100) if (total_payout + total_mdf_approved) > 0 else 0

    print(f"\n{'='*60}")
    print(f"  📊 PROGRAM REPORT: {args.name}")
    print(f"{'='*60}")
    print(f"  Status:          {program.get('status', 'active')}")
    print(f"  Tiers:           {len(program['tiers'])}")
    print(f"  Active Partners: {unique_partners}")
    print(f"  ──────────────────────────────────────")
    print(f"  Total Revenue:         ${total_revenue:>12,.2f}")
    print(f"  Total Incentive Cost:  ${total_payout:>12,.2f}")
    print(f"  MDF Approved:          ${total_mdf_approved:>12,.2f}")
    print(f"  MDF Pending:           ${total_mdf_claimed - total_mdf_approved:>12,.2f}")
    print(f"  Combined Program Cost: ${total_payout + total_mdf_approved:>12,.2f}")
    print(f"  Program ROI:           {roi:>12.1f}%")
    print(f"  ──────────────────────────────────────")
    print(f"  Effective Cost/Rev:   {(total_payout + total_mdf_approved) / total_revenue * 100:.1f}%" if total_revenue > 0 else "  N/A")
    print(f"  Payouts Generated:    {len(payouts)}")
    print(f"  MDF Claims Filed:     {len(claims)}")
    print(f"{'='*60}")


def cmd_report_partner(args) -> None:
    """Report on a single partner across all programs."""
    txns = [t for t in _load_json(TRANSACTIONS_FILE) if t.get("partner") == args.name]
    claims = [c for c in _load_json(MDF_CLAIMS_FILE) if c.get("partner") == args.name]
    payouts = [p for p in _load_json(PAYOUTS_FILE) if p.get("partner") == args.name]

    if not txns and not claims:
        print(f"No data found for partner '{args.name}'.")
        return

    total_revenue = sum(t["total_revenue"] for t in txns)
    total_payout = sum(t["total_payout"] for t in txns)
    total_mdf_approved = sum(c["amount"] for c in claims if c["status"] == "approved")
    total_mdf_pending = sum(c["amount"] for c in claims if c["status"] == "pending")

    print(f"\n{'='*60}")
    print(f"  👤 PARTNER REPORT: {args.name}")
    print(f"{'='*60}")
    print(f"  Programs:        {', '.join(set(t.get('program','?') for t in txns)) or 'None'}")
    print(f"  Revenue Generated:  ${total_revenue:>12,.2f}")
    print(f"  Rebates Earned:     ${total_payout:>12,.2f}")
    print(f"  MDF Approved:       ${total_mdf_approved:>12,.2f}")
    print(f"  MDF Pending:        ${total_mdf_pending:>12,.2f}")
    print(f"  Total Compensation: ${total_payout + total_mdf_approved:>12,.2f}")
    print(f"  Effective Rate:     {total_payout / total_revenue * 100:.1f}%" if total_revenue > 0 else "  N/A")
    print(f"  Transactions:      {len(txns)}")
    print(f"  MDF Claims:        {len(claims)}")
    last_tier = txns[-1].get("tier", "N/A") if txns else "N/A"
    print(f"  Current Tier:      {last_tier}")
    print(f"{'='*60}")


def cmd_serve(args) -> None:
    """Start MCP server mode for integration with AI tools."""
    try:
        from mcp.server import Server, NotificationOptions
        from mcp.server.models import InitializationOptions
        import mcp.server.stdio
        import mcp.types as types
    except ImportError:
        print("MCP server mode requires 'mcp' package. Install with: pip install mcp")
        sys.exit(1)

    server = Server("partner-incentives")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="design_incentive_program",
                description="Design a tiered partner incentive/rebate program with rules",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Program name"},
                        "tiers": {"type": "string", "description": "JSON array of tiers with name, min_revenue, rebate_pct, description"},
                        "rules": {"type": "string", "description": "JSON object with program rules"},
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="calculate_partner_rebate",
                description="Calculate earned rebates and incentives for a partner",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "program": {"type": "string", "description": "Program name"},
                        "partner": {"type": "string", "description": "Partner name"},
                        "transactions_json": {"type": "string", "description": "JSON array of transactions with revenue, is_registered, is_new_logo fields"},
                    },
                    "required": ["program", "partner", "transactions_json"],
                },
            ),
            types.Tool(
                name="submit_mdf_claim",
                description="Submit a Market Development Fund (MDF) claim",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "program": {"type": "string", "description": "Program name"},
                        "partner": {"type": "string", "description": "Partner name"},
                        "amount": {"type": "number", "description": "Claim amount in USD"},
                        "description": {"type": "string", "description": "Purpose/description"},
                    },
                    "required": ["program", "partner", "amount"],
                },
            ),
            types.Tool(
                name="approve_mdf_claim",
                description="Approve a pending MDF claim",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string"},
                    },
                    "required": ["claim_id"],
                },
            ),
            types.Tool(
                name="generate_payout_report",
                description="Generate payout report for a program period",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "program": {"type": "string"},
                        "partner": {"type": "string", "description": "Optional: filter to one partner"},
                        "period": {"type": "string", "description": "Period label (e.g. Q2-2026)"},
                    },
                    "required": ["program"],
                },
            ),
            types.Tool(
                name="get_program_report",
                description="Get comprehensive report on program effectiveness",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "program": {"type": "string"},
                    },
                    "required": ["program"],
                },
            ),
            types.Tool(
                name="get_partner_report",
                description="Get comprehensive report on a partner's performance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "partner": {"type": "string"},
                    },
                    "required": ["partner"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        try:
            if name == "design_incentive_program":
                tiers = json.loads(arguments.get("tiers", "[]")) if arguments.get("tiers") else None
                rules = json.loads(arguments.get("rules", "{}")) if arguments.get("rules") else None
                cmd_program_create(argparse.Namespace(
                    name=arguments["name"],
                    description=arguments.get("description", ""),
                    tiers=tiers,
                    rules=rules,
                ))
                return [types.TextContent(type="text", text=f"Program '{arguments['name']}' created successfully.")]

            elif name == "calculate_partner_rebate":
                # Write transactions to temp file
                txn_file = DATA_DIR / f"_tmp_txns_{arguments['partner']}.json"
                txn_data = json.loads(arguments["transactions_json"]) if isinstance(arguments["transactions_json"], str) else arguments["transactions_json"]
                with open(txn_file, "w") as f:
                    json.dump(txn_data, f)
                cmd_rebate_calculate(argparse.Namespace(
                    program_name=arguments["program"],
                    partner_name=arguments["partner"],
                    transactions_file=str(txn_file),
                ))
                return [types.TextContent(type="text", text=f"Rebate calculated for {arguments['partner']} in {arguments['program']}.")]

            elif name == "submit_mdf_claim":
                cmd_mdf_submit(argparse.Namespace(
                    program_name=arguments["program"],
                    partner_name=arguments["partner"],
                    amount=arguments["amount"],
                    description=arguments.get("description", ""),
                ))
                return [types.TextContent(type="text", text=f"MDF claim submitted for {arguments['partner']} in {arguments['program']}.")]

            elif name == "approve_mdf_claim":
                cmd_mdf_approve(argparse.Namespace(claim_id=arguments["claim_id"]))
                return [types.TextContent(type="text", text=f"Claim {arguments['claim_id']} approved.")]

            elif name == "generate_payout_report":
                cmd_payout_generate(argparse.Namespace(
                    program_name=arguments["program"],
                    partner=arguments.get("partner"),
                    period=arguments.get("period"),
                ))
                return [types.TextContent(type="text", text=f"Payout report generated for {arguments['program']}.")]

            elif name == "get_program_report":
                cmd_report_program(argparse.Namespace(name=arguments["program"]))
                return [types.TextContent(type="text", text=f"Report for {arguments['program']}.")]

            elif name == "get_partner_report":
                cmd_report_partner(argparse.Namespace(name=arguments["partner"]))
                return [types.TextContent(type="text", text=f"Report for {arguments['partner']}.")]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    import asyncio
    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, InitializationOptions(
                server_name="partner-incentives",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ))
    asyncio.run(main())


# ── CLI Entry ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PIRE — Partner Incentive & Rebate Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # program
    p_prog = sub.add_parser("program", help="Manage incentive programs")
    p_prog_sub = p_prog.add_subparsers(dest="action", required=True)
    p_prog_create = p_prog_sub.add_parser("create", help="Create a new incentive program")
    p_prog_create.add_argument("name")
    p_prog_create.add_argument("--description", "-d", default="")
    p_prog_create.add_argument("--tiers", type=json.loads, help="JSON array of tier definitions")
    p_prog_create.add_argument("--rules", type=json.loads, help="JSON object of program rules")
    p_prog_create.set_defaults(func=cmd_program_create)
    p_prog_list = p_prog_sub.add_parser("list", help="List all programs")
    p_prog_list.set_defaults(func=cmd_program_list)
    p_prog_show = p_prog_sub.add_parser("show", help="Show program details")
    p_prog_show.add_argument("name")
    p_prog_show.set_defaults(func=cmd_program_show)

    # rebate
    p_reb = sub.add_parser("rebate", help="Calculate partner rebates")
    p_reb_sub = p_reb.add_subparsers(dest="action", required=True)
    p_reb_calc = p_reb_sub.add_parser("calculate", help="Calculate earned rebates")
    p_reb_calc.add_argument("program_name")
    p_reb_calc.add_argument("partner_name")
    p_reb_calc.add_argument("transactions_file", help="JSON or CSV file with transaction data")
    p_reb_calc.set_defaults(func=cmd_rebate_calculate)

    # mdf
    p_mdf = sub.add_parser("mdf", help="Manage MDF claims")
    p_mdf_sub = p_mdf.add_subparsers(dest="action", required=True)
    p_mdf_submit = p_mdf_sub.add_parser("submit", help="Submit an MDF claim")
    p_mdf_submit.add_argument("program_name")
    p_mdf_submit.add_argument("partner_name")
    p_mdf_submit.add_argument("amount", type=float)
    p_mdf_submit.add_argument("--description", "-d", default="")
    p_mdf_submit.set_defaults(func=cmd_mdf_submit)
    p_mdf_list = p_mdf_sub.add_parser("list", help="List MDF claims")
    p_mdf_list.add_argument("--program", help="Filter by program")
    p_mdf_list.add_argument("--partner", help="Filter by partner")
    p_mdf_list.add_argument("--status", help="Filter by status")
    p_mdf_list.set_defaults(func=cmd_mdf_list)
    p_mdf_approve = p_mdf_sub.add_parser("approve", help="Approve an MDF claim")
    p_mdf_approve.add_argument("claim_id")
    p_mdf_approve.set_defaults(func=cmd_mdf_approve)
    p_mdf_reject = p_mdf_sub.add_parser("reject", help="Reject an MDF claim")
    p_mdf_reject.add_argument("claim_id")
    p_mdf_reject.set_defaults(func=cmd_mdf_reject)

    # payout
    p_pay = sub.add_parser("payout", help="Generate payout reports")
    p_pay_sub = p_pay.add_subparsers(dest="action", required=True)
    p_pay_gen = p_pay_sub.add_parser("generate", help="Generate payout report for a program")
    p_pay_gen.add_argument("program_name")
    p_pay_gen.add_argument("--partner", help="Filter to one partner")
    p_pay_gen.add_argument("--period", help="Period label (e.g. Q2-2026)")
    p_pay_gen.set_defaults(func=cmd_payout_generate)

    # report
    p_rep = sub.add_parser("report", help="Generate reports")
    p_rep_sub = p_rep.add_subparsers(dest="action", required=True)
    p_rep_prog = p_rep_sub.add_parser("program", help="Program summary report")
    p_rep_prog.add_argument("name")
    p_rep_prog.set_defaults(func=cmd_report_program)
    p_rep_part = p_rep_sub.add_parser("partner", help="Partner performance report")
    p_rep_part.add_argument("name")
    p_rep_part.set_defaults(func=cmd_report_partner)

    # serve
    p_serve = sub.add_parser("serve", help="Start MCP server mode")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
