#!/usr/bin/env python3
"""
PCO — Partner Co-Sell Orchestrator
CLI tool + MCP server for orchestrating vendor-partner co-selling deals.

Usage:
    pco.py opportunity create ...       Create a co-sell opportunity
    pco.py opportunity list             List opportunities
    pco.py opportunity show <id>        Show opportunity details
    pco.py opportunity update <id>      Update stage/split/notes
    pco.py match ...                    Find best partner match
    pco.py credit split <id> ...        Set/modify credit split
    pco.py dashboard                    Pipeline summary
    pco.py serve                        MCP server mode
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".pco"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
PARTNERS_FILE = DATA_DIR / "partners.json"
ACTIVITY_LOG = DATA_DIR / "activity.json"

# Default partner data (loaded from sample_partners.json if no local file)
DEFAULT_PARTNERS_PATH = Path(__file__).parent / "sample_partners.json"

# ── Stage definitions ──────────────────────────────────────────────────────
STAGES = [
    "new",
    "partner_accepted",
    "demo_scheduled",
    "demo_completed",
    "proposal_sent",
    "negotiation",
    "closed_won",
    "closed_lost",
]

STAGE_ORDER = {s: i for i, s in enumerate(STAGES)}

STAGE_DISPLAY = {
    "new": "🆕 New",
    "partner_accepted": "✅ Partner Accepted",
    "demo_scheduled": "📅 Demo Scheduled",
    "demo_completed": "🎥 Demo Completed",
    "proposal_sent": "📄 Proposal Sent",
    "negotiation": "🤝 Negotiation",
    "closed_won": "🏆 Closed Won",
    "closed_lost": "❌ Closed Lost",
}

TIER_PRIORITY = {"platinum": 15, "gold": 10, "authorized": 5}

# ── Data helpers ───────────────────────────────────────────────────────────


def _load_json(path, default=None):
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default if default is not None else []
    return default if default is not None else []


def _save_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_partners():
    partners = _load_json(PARTNERS_FILE)
    if not partners and DEFAULT_PARTNERS_PATH.exists():
        with open(DEFAULT_PARTNERS_PATH) as f:
            partners = json.load(f)
        _save_json(PARTNERS_FILE, partners)
    return partners


def _load_opportunities():
    return _load_json(OPPORTUNITIES_FILE, [])


def _next_id(opps):
    existing = [o.get("id", "") for o in opps]
    nums = [int(o[4:]) for o in existing if o.startswith("OPP-") and o[4:].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"OPP-{next_num:04d}"


def _log_activity(opp_id, action, details):
    activities = _load_json(ACTIVITY_LOG, [])
    activities.append({
        "timestamp": datetime.now().isoformat(),
        "opportunity_id": opp_id,
        "action": action,
        "details": details,
    })
    _save_json(ACTIVITY_LOG, activities)


def _find_opportunity(opps, opp_id):
    for o in opps:
        if o["id"].lower() == opp_id.lower():
            return o
    return None


# ── CLI Handlers ───────────────────────────────────────────────────────────


def cmd_opportunity_create(args):
    opps = _load_opportunities()
    opp_id = _next_id(opps)

    stages_list = [s for s in STAGES if s not in ("closed_won", "closed_lost")]

    opportunity = {
        "id": opp_id,
        "title": args.title,
        "stage": "new",
        "vendor_rep": args.vendor_rep,
        "partner_name": args.partner_name,
        "partner_rep": args.partner_rep or "",
        "deal_value": args.value,
        "vendor_split_pct": args.vendor_split,
        "partner_split_pct": args.partner_split,
        "region": args.region or "",
        "notes": args.notes or "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "stage_history": [{
            "stage": "new",
            "timestamp": datetime.now().isoformat(),
            "note": "Opportunity created"
        }],
        "split_history": [{
            "vendor_split": args.vendor_split,
            "partner_split": args.partner_split,
            "reason": "Initial split",
            "timestamp": datetime.now().isoformat(),
        }],
    }

    opps.append(opportunity)
    _save_json(OPPORTUNITIES_FILE, opps)
    _log_activity(opp_id, "created", f"Co-sell opportunity '{args.title}' created (${args.value:,})")

    print(f"\n✅ Co-Sell Opportunity Created: {opp_id}")
    print(f"   Title:    {args.title}")
    print(f"   Partner:  {args.partner_name}")
    print(f"   Value:    ${args.value:,}")
    print(f"   Split:    Vendor {args.vendor_split}% / Partner {args.partner_split}%")
    print(f"   Stage:    New (awaiting partner acceptance)")
    return opportunity


def cmd_opportunity_list(args):
    opps = _load_opportunities()
    if not opps:
        print("No co-sell opportunities found.")
        return

    # Filter
    if args.status:
        status = args.status.lower()
        if status == "open":
            opps = [o for o in opps if o["stage"] not in ("closed_won", "closed_lost")]
        elif status in STAGES:
            opps = [o for o in opps if o["stage"] == status]

    if args.partner:
        opps = [o for o in opps if args.partner.lower() in o.get("partner_name", "").lower()]

    if not opps:
        print("No matching opportunities.")
        return

    # Header
    print(f"\n{'ID':<12} {'Title':<32} {'Partner':<22} {'Value':<12} {'Stage':<22} {'Split':<16} {'Aging'}")
    print("-" * 130)

    now = datetime.now()
    for o in sorted(opps, key=lambda x: x.get("created_at", ""), reverse=True):
        sid = o["id"]
        title = (o.get("title", "?")[:30] + "..") if len(o.get("title", "")) > 30 else o.get("title", "?").ljust(30)
        partner = (o.get("partner_name", "?")[:20] + "..") if len(o.get("partner_name", "")) > 20 else o.get("partner_name", "?").ljust(20)
        value = f"${o.get('deal_value', 0):,}"
        stage = STAGE_DISPLAY.get(o.get("stage", "new"), o.get("stage", "?"))

        vs = o.get("vendor_split_pct", 50)
        ps = o.get("partner_split_pct", 50)
        split = f"V{vs}%/P{ps}%"

        # Aging
        created = o.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created)
            days = (now - dt).days
            aging = f"{days}d"
        except (ValueError, TypeError):
            aging = "?"

        print(f"{sid:<12} {title:<32} {partner:<22} {value:<12} {stage:<22} {split:<16} {aging}")

    total = sum(o.get("deal_value", 0) for o in opps if o.get("stage") not in ("closed_lost",))
    closed_won = sum(o.get("deal_value", 0) for o in opps if o.get("stage") == "closed_won")
    print(f"\n{'─' * 130}")
    print(f"Open pipeline: ${total:,}  |  Closed Won: ${closed_won:,}  |  Total opps: {len(opps)}")


def cmd_opportunity_show(args):
    opps = _load_opportunities()
    opp = _find_opportunity(opps, args.opp_id)
    if not opp:
        print(f"Opportunity '{args.opp_id}' not found.")
        return

    print(f"""
╔═══ PCO Opportunity: {opp['id']} ═══╗

{'Title:':<20} {opp.get('title', '?')}
{'Stage:':<20} {STAGE_DISPLAY.get(opp.get('stage', '?'), opp.get('stage', '?'))}
{'Value:':<20} ${opp.get('deal_value', 0):,}
{'Region:':<20} {opp.get('region', 'N/A')}

─── Parties ──────────────────────────────────
{'Vendor Rep:':<20} {opp.get('vendor_rep', '?')}
{'Partner:':<20} {opp.get('partner_name', '?')}
{'Partner Rep:':<20} {opp.get('partner_rep', 'N/A')}

─── Credit Split ─────────────────────────────
{'Vendor:':<20} {opp.get('vendor_split_pct', 50)}%
{'Partner:':<20} {opp.get('partner_split_pct', 50)}%

─── Timeline ─────────────────────────────────
{'Created:':<20} {opp.get('created_at', '?')[:19]}
{'Updated:':<20} {opp.get('updated_at', '?')[:19]}

─── Notes ────────────────────────────────────
{opp.get('notes', 'N/A')}

─── Stage History ────────────────────────────""")

    for entry in opp.get("stage_history", []):
        ts = entry.get("timestamp", "")[:19]
        stage = STAGE_DISPLAY.get(entry.get("stage", "?"), entry.get("stage", "?"))
        note = entry.get("note", "")
        print(f"  {ts}  {stage:22}  {note}")

    print("\n─── Split History ────────────────────────────")
    for entry in opp.get("split_history", []):
        ts = entry.get("timestamp", "")[:19]
        v = entry.get("vendor_split", "?")
        p = entry.get("partner_split", "?")
        r = entry.get("reason", "")
        print(f"  {ts}  V{v}%/P{p}%  —  {r}")

    # Aging
    now = datetime.now()
    created = opp.get("created_at", "")
    try:
        age = (now - datetime.fromisoformat(created)).days
        print(f"\nAging: {age} days in pipeline")
    except (ValueError, TypeError):
        pass

    print("╚" + "═" * 50 + "╝")


def cmd_opportunity_update(args):
    opps = _load_opportunities()
    opp = _find_opportunity(opps, args.opp_id)
    if not opp:
        print(f"Opportunity '{args.opp_id}' not found.")
        return

    updated = False

    if args.stage:
        new_stage = args.stage.lower()
        if new_stage not in STAGES:
            print(f"Invalid stage. Valid: {', '.join(STAGES)}")
            return
        current_idx = STAGE_ORDER.get(opp.get("stage", "new"), 0)
        new_idx = STAGE_ORDER.get(new_stage, 0)
        if new_idx < current_idx:
            print(f"Warning: Moving backward from {opp['stage']} to {new_stage}")
        opp["stage"] = new_stage
        if "stage_history" not in opp:
            opp["stage_history"] = []
        note = args.notes or getattr(args, 'note', None) or f"Updated to {new_stage}"
        opp["stage_history"].append({
            "stage": new_stage,
            "timestamp": datetime.now().isoformat(),
            "note": note,
        })
        updated = True
        _log_activity(args.opp_id, "stage_update", f"Moved to {new_stage}")

    if args.notes is not None:
        opp["notes"] = args.notes
        updated = True

    if args.partner_rep:
        opp["partner_rep"] = args.partner_rep
        updated = True

    if updated:
        opp["updated_at"] = datetime.now().isoformat()
        _save_json(OPPORTUNITIES_FILE, opps)
        print(f"✅ Opportunity {args.opp_id} updated.")
    else:
        print("No changes specified. Use --stage, --notes, or --partner-rep.")


def cmd_match(args):
    partners = _load_partners()
    if not partners:
        print("No partner data available for matching.")
        return

    title = (args.title or "").lower()
    region = (args.region or "").lower()
    value = args.value or 0

    # Extract keywords from title
    title_words = set(title.split())

    # Expertise keyword map
    expertise_map = {
        "cloud": ["cloud", "aws", "azure", "gcp", "migration", "infrastructure"],
        "saas": ["saas", "software", "subscription", "platform"],
        "security": ["security", "secure", "compliance", "gdpr", "hipaa", "cyber"],
        "data": ["data", "analytics", "database", "big-data", "etl", "warehouse"],
        "ai-ml": ["ai", "ml", "machine-learning", "deep-learning", "llm", "gpt"],
        "devops": ["devops", "ci/cd", "kubernetes", "docker", "terraform"],
        "network": ["network", "connectivity", "vpn", "sd-wan"],
        "iot": ["iot", "edge", "sensors"],
        "crm": ["crm", "salesforce", "customer-relationship"],
        "marketing": ["marketing", "automation", "campaign"],
        "managed-services": ["managed", "msp", "outsource", "support"],
        "it-support": ["it-support", "helpdesk", "desktop", "infrastructure"],
        "analytics": ["analytics", "bi", "dashboard", "reporting"],
    }

    scored = []
    for p in partners:
        score = 0
        breakdown = []

        # 1. Expertise fit (weight: 40 points)
        expertise_fit = 0
        partner_expertise = set(p.get("expertise", []))
        for word in title_words:
            for domain, keywords in expertise_map.items():
                if word in keywords and domain in partner_expertise:
                    expertise_fit += 10
                    break
        # Also check direct keyword-in-title matches for expertise tags
        for exp in partner_expertise:
            exp_lower = exp.lower()
            if exp_lower in title or any(w == exp_lower for w in title_words):
                expertise_fit += 15

        expertise_fit = min(expertise_fit, 40)
        score += expertise_fit
        breakdown.append(f"Expertise: +{expertise_fit}/40")

        # 2. Region match (weight: 30 points)
        partner_region = p.get("region", "").lower()
        region_match = 30 if partner_region == region else 0
        # Partial match (e.g., "Midwest" matches "Midwest")
        if region and region in partner_region:
            region_match = 25
        score += region_match
        breakdown.append(f"Region: +{region_match}/30")

        # 3. Tier bonus (weight: 20 points)
        tier_bonus = TIER_PRIORITY.get(p.get("tier", "").lower(), 0)
        score += tier_bonus
        breakdown.append(f"Tier ({p.get('tier', '')}): +{tier_bonus}/20")

        # 4. Engagement (weight: 10 points)
        engagement = p.get("engagement_score", 0)
        engagement_pts = min(int(engagement * 0.1), 10)  # 88 → 8
        score += engagement_pts
        breakdown.append(f"Engagement: +{engagement_pts}/10")

        total_possible = 100
        scored.append({
            "partner": p["name"],
            "tier": p.get("tier", ""),
            "region": p.get("region", ""),
            "expertise": p.get("expertise", []),
            "score": score,
            "max_score": total_possible,
            "confidence_pct": round(score / total_possible * 100),
            "breakdown": breakdown,
        })

    # Sort by score desc
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:5]

    print(f"\n═══ Partner Match Results ═══")
    print(f"Opportunity: {args.title}")
    if region:
        print(f"Region:      {args.region}")
    print(f"Value:       ${value:,}" if value else "")
    print()

    if not top:
        print("No partners matched your criteria.")
        return

    for i, m in enumerate(top, 1):
        bar_len = int(m["confidence_pct"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  #{i}  {m['partner']:<24} {bar}  {m['confidence_pct']:2d}%")
        print(f"      Tier: {m['tier']:<12} Region: {m['region']:<18} Expertise: {', '.join(m['expertise'])}")
        for b in m["breakdown"]:
            print(f"      {b}")
        print()

    print("─" * 60)


def cmd_credit_split(args):
    opps = _load_opportunities()
    opp = _find_opportunity(opps, args.opp_id)
    if not opp:
        print(f"Opportunity '{args.opp_id}' not found.")
        return

    total = args.vendor + args.partner
    if total != 100:
        print(f"Error: Vendor + Partner split must equal 100 (got {total})")
        return

    old_v = opp["vendor_split_pct"]
    old_p = opp["partner_split_pct"]

    if "split_history" not in opp:
        opp["split_history"] = []

    opp["vendor_split_pct"] = args.vendor
    opp["partner_split_pct"] = args.partner
    opp["split_history"].append({
        "vendor_split": args.vendor,
        "partner_split": args.partner,
        "reason": args.reason or "Adjusted",
        "timestamp": datetime.now().isoformat(),
    })
    opp["updated_at"] = datetime.now().isoformat()

    _save_json(OPPORTUNITIES_FILE, opps)
    _log_activity(args.opp_id, "split_change",
                  f"Vendor {old_v}%→{args.vendor}%, Partner {old_p}%→{args.partner}% — {args.reason or 'N/A'}")

    print(f"✅ {args.opp_id} credit split updated:")
    print(f"   Vendor:  {old_v}% → {args.vendor}%")
    print(f"   Partner: {old_p}% → {args.partner}%")
    print(f"   Reason:  {args.reason or 'N/A'}")


def cmd_dashboard(args):
    opps = _load_opportunities()
    partners = _load_partners()

    if not opps:
        print("No co-sell opportunities in pipeline.")
        return

    now = datetime.now()

    # Stage distribution
    stage_counts = {}
    stage_values = {}
    for o in opps:
        s = o.get("stage", "unknown")
        stage_counts[s] = stage_counts.get(s, 0) + 1
        stage_values[s] = stage_values.get(s, 0) + o.get("deal_value", 0)

    # Open vs closed
    open_opps = [o for o in opps if o.get("stage") not in ("closed_won", "closed_lost")]
    closed_won = [o for o in opps if o.get("stage") == "closed_won"]
    closed_lost = [o for o in opps if o.get("stage") == "closed_lost"]

    open_value = sum(o.get("deal_value", 0) for o in open_opps)
    won_value = sum(o.get("deal_value", 0) for o in closed_won)
    lost_value = sum(o.get("deal_value", 0) for o in closed_lost)

    print(f"""
╔═══ PCO Pipeline Dashboard ═══════════════════════════════╗

─── Summary ───────────────────────────────────────────────
Open Opportunities:     {len(open_opps)}
Closed Won:             {len(closed_won)}
Closed Lost:            {len(closed_lost)}
Total Pipeline Value:   ${open_value:,}
Revenue Closed Won:     ${won_value:,}
Revenue Lost:           ${lost_value:,}
Win Rate:               {len(closed_won) / max(len(closed_won) + len(closed_lost), 1) * 100:.0f}%

─── By Stage ──────────────────────────────────────────────""")

    for stage in STAGES:
        count = stage_counts.get(stage, 0)
        value = stage_values.get(stage, 0)
        if count > 0:
            bar = "█" * min(count, 30)
            print(f"  {STAGE_DISPLAY.get(stage, stage):<22} {bar} {count} opps  ${value:,}")

    # Aging
    print("\n─── Aging (days in pipeline) ─────────────────────")
    age_buckets = {"0-30d": 0, "31-60d": 0, "61-90d": 0, "90+d": 0}
    for o in open_opps:
        created = o.get("created_at", "")
        try:
            days = (now - datetime.fromisoformat(created)).days
            if days <= 30:
                age_buckets["0-30d"] += 1
            elif days <= 60:
                age_buckets["31-60d"] += 1
            elif days <= 90:
                age_buckets["61-90d"] += 1
            else:
                age_buckets["90+d"] += 1
        except (ValueError, TypeError):
            pass

    for bucket, count in age_buckets.items():
        if count > 0:
            bar = "█" * count
            print(f"  {bucket:<12} {bar} {count}")

    # By partner
    print("\n─── Pipeline by Partner ──────────────────────────")
    partner_values = {}
    for o in open_opps:
        pname = o.get("partner_name", "Unassigned")
        partner_values[pname] = partner_values.get(pname, 0) + o.get("deal_value", 0)

    for pname, val in sorted(partner_values.items(), key=lambda x: -x[1]):
        bar = "█" * max(1, int(val / max(partner_values.values()) * 20))
        print(f"  {pname:<24} {bar} ${val:,}")

    print("\n╚" + "═" * 58 + "╝")


# ── MCP Server Mode ────────────────────────────────────────────────────────


def cmd_serve(args):
    """Start MCP server for AI agent integration."""
    try:
        from mcp.server import Server, NotificationOptions
        from mcp.server.models import InitializationOptions
        import mcp.server.stdio
        import mcp.types as types
    except ImportError:
        print("MCP mode requires the 'mcp' package. Install with: pip install mcp")
        sys.exit(1)

    server = Server("pco-partner-co-sell")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="create_co_sell_opportunity",
                description="Create a co-sell opportunity where a vendor and partner collaborate on a deal. Includes credit split.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Opportunity title"},
                        "vendor_rep": {"type": "string", "description": "Vendor representative email"},
                        "partner_name": {"type": "string", "description": "Partner company name"},
                        "partner_rep": {"type": "string", "description": "Partner rep email"},
                        "deal_value": {"type": "number", "description": "Total deal value in dollars"},
                        "vendor_split": {"type": "integer", "description": "Vendor revenue share %", "minimum": 0, "maximum": 100},
                        "partner_split": {"type": "integer", "description": "Partner revenue share %", "minimum": 0, "maximum": 100},
                        "region": {"type": "string", "description": "Geographic region"},
                        "notes": {"type": "string", "description": "Additional notes"},
                    },
                    "required": ["title", "vendor_rep", "partner_name", "deal_value"],
                },
            ),
            types.Tool(
                name="list_opportunities",
                description="List co-sell opportunities with optional filters for status, partner, or stage.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["open", "closed_won", "closed_lost", "new", "partner_accepted", "demo_scheduled", "demo_completed", "proposal_sent", "negotiation"], "description": "Filter by status"},
                        "partner": {"type": "string", "description": "Filter by partner name (partial match)"},
                    },
                },
            ),
            types.Tool(
                name="get_opportunity",
                description="Get full details of a co-sell opportunity including stage history and split history.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "opp_id": {"type": "string", "description": "Opportunity ID (e.g., OPP-0001)"},
                    },
                    "required": ["opp_id"],
                },
            ),
            types.Tool(
                name="update_opportunity_stage",
                description="Advance or change the stage of a co-sell opportunity.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "opp_id": {"type": "string", "description": "Opportunity ID"},
                        "stage": {"type": "string", "enum": STAGES, "description": "New stage"},
                        "note": {"type": "string", "description": "Note about this stage change"},
                    },
                    "required": ["opp_id", "stage"],
                },
            ),
            types.Tool(
                name="set_credit_split",
                description="Set or modify the revenue/commission credit split between vendor and partner. Audit trail maintained.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "opp_id": {"type": "string", "description": "Opportunity ID"},
                        "vendor_pct": {"type": "integer", "description": "Vendor percentage", "minimum": 0, "maximum": 100},
                        "partner_pct": {"type": "integer", "description": "Partner percentage", "minimum": 0, "maximum": 100},
                        "reason": {"type": "string", "description": "Reason for the split change"},
                    },
                    "required": ["opp_id", "vendor_pct", "partner_pct"],
                },
            ),
            types.Tool(
                name="find_partner_match",
                description="Score and suggest best-fit partners for an unassigned co-sell opportunity. Uses expertise, region, tier, and engagement scoring.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Opportunity title or description"},
                        "region": {"type": "string", "description": "Target region for partner matching"},
                        "deal_value": {"type": "number", "description": "Estimated deal value"},
                    },
                    "required": ["title"],
                },
            ),
            types.Tool(
                name="get_pipeline_dashboard",
                description="Get aggregated pipeline metrics: stage distribution, aging, partner pipeline value, win rate.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        class Args:
            pass

        a = Args()
        try:
            if name == "create_co_sell_opportunity":
                for k in ("title", "vendor_rep", "partner_name", "deal_value", "vendor_split", "partner_split", "partner_rep", "region", "notes"):
                    setattr(a, k.replace("-", "_"), arguments.get(k, 0 if k in ("vendor_split", "partner_split") else ""))
                if not a.vendor_split:
                    a.vendor_split = 50
                if not a.partner_split:
                    a.partner_split = 50
                result = cmd_opportunity_create(a)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            elif name == "list_opportunities":
                a.status = arguments.get("status", "")
                a.partner = arguments.get("partner", "")
                # Capture output via string buffer
                import io
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                cmd_opportunity_list(a)
                sys.stdout = old_stdout
                return [types.TextContent(type="text", text=buf.getvalue())]

            elif name == "get_opportunity":
                a.opp_id = arguments["opp_id"]
                import io
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                cmd_opportunity_show(a)
                sys.stdout = old_stdout
                return [types.TextContent(type="text", text=buf.getvalue())]

            elif name == "update_opportunity_stage":
                a.opp_id = arguments["opp_id"]
                a.stage = arguments["stage"]
                a.notes = arguments.get("note", "")
                a.partner_rep = None
                import io
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                cmd_opportunity_update(a)
                sys.stdout = old_stdout
                return [types.TextContent(type="text", text=buf.getvalue())]

            elif name == "set_credit_split":
                a.opp_id = arguments["opp_id"]
                a.vendor = arguments["vendor_pct"]
                a.partner = arguments["partner_pct"]
                a.reason = arguments.get("reason", "MCP adjustment")
                import io
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                cmd_credit_split(a)
                sys.stdout = old_stdout
                return [types.TextContent(type="text", text=buf.getvalue())]

            elif name == "find_partner_match":
                a.title = arguments["title"]
                a.region = arguments.get("region", "")
                a.value = arguments.get("deal_value", 0)
                import io
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                cmd_match(a)
                sys.stdout = old_stdout
                return [types.TextContent(type="text", text=buf.getvalue())]

            elif name == "get_pipeline_dashboard":
                class ArgsEmpty:
                    pass
                a = ArgsEmpty()
                import io
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                cmd_dashboard(a)
                sys.stdout = old_stdout
                return [types.TextContent(type="text", text=buf.getvalue())]

            raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # Run MCP server (blocking)
    import anyio
    async def run():
        async with mcp.server.stdio.stdio_server() as (read, write):
            await server.run(
                read, write,
                InitializationOptions(
                    server_name="pco-partner-co-sell",
                    server_version="0.1.0",
                )
            )
    anyio.run(run)


# ── CLI Parser ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="PCO — Partner Co-Sell Orchestrator")
    sub = parser.add_subparsers(dest="command")

    # ── opportunity ──
    opp = sub.add_parser("opportunity", help="Manage co-sell opportunities")
    opp_sub = opp.add_subparsers(dest="action")

    # opportunity create
    opp_create = opp_sub.add_parser("create", help="Create a co-sell opportunity")
    opp_create.add_argument("--title", required=True)
    opp_create.add_argument("--vendor-rep", required=True)
    opp_create.add_argument("--partner-name", required=True)
    opp_create.add_argument("--partner-rep", default="")
    opp_create.add_argument("--value", type=float, required=True)
    opp_create.add_argument("--vendor-split", type=int, default=50)
    opp_create.add_argument("--partner-split", type=int, default=50)
    opp_create.add_argument("--region", default="")
    opp_create.add_argument("--notes", default="")

    # opportunity list
    opp_list = opp_sub.add_parser("list", help="List co-sell opportunities")
    opp_list.add_argument("--status", choices=["open"] + STAGES, default="open", help="Filter by status")
    opp_list.add_argument("--partner", default="", help="Filter by partner name")

    # opportunity show
    opp_show = opp_sub.add_parser("show", help="Show opportunity details")
    opp_show.add_argument("opp_id", help="Opportunity ID (e.g., OPP-0001)")

    # opportunity update
    opp_update = opp_sub.add_parser("update", help="Update an opportunity")
    opp_update.add_argument("opp_id", help="Opportunity ID")
    opp_update.add_argument("--stage", choices=STAGES, help="New stage")
    opp_update.add_argument("--notes", help="Update notes")
    opp_update.add_argument("--partner-rep", help="Update partner rep")

    # ── match ──
    match = sub.add_parser("match", help="Find best partner match")
    match.add_argument("--title", required=True)
    match.add_argument("--region", default="")
    match.add_argument("--value", type=float, default=0)

    # ── credit split ──
    credit = sub.add_parser("credit", help="Manage credit splits")
    credit_sub = credit.add_subparsers(dest="action")
    cs = credit_sub.add_parser("split", help="Set credit split for an opportunity")
    cs.add_argument("opp_id", help="Opportunity ID")
    cs.add_argument("--vendor", type=int, required=True)
    cs.add_argument("--partner", type=int, required=True)
    cs.add_argument("--reason", default="Adjusted")

    # ── dashboard ──
    sub.add_parser("dashboard", help="Show pipeline dashboard")

    # ── serve ──
    sub.add_parser("serve", help="Start MCP server mode")

    args = parser.parse_args()

    if args.command == "opportunity":
        if args.action == "create":
            cmd_opportunity_create(args)
        elif args.action == "list":
            cmd_opportunity_list(args)
        elif args.action == "show":
            cmd_opportunity_show(args)
        elif args.action == "update":
            cmd_opportunity_update(args)
        else:
            parser.print_help()
    elif args.command == "match":
        cmd_match(args)
    elif args.command == "credit":
        if args.action == "split":
            cmd_credit_split(args)
        else:
            parser.print_help()
    elif args.command == "dashboard":
        cmd_dashboard(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()