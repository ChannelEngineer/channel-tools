# PCO — Partner Co-Sell Orchestrator

**Experimental prototype** — CLI tool + MCP server for orchestrating vendor-partner co-selling deals. Manages opportunity creation, partner matching, credit splits, deal progression, and automated routing.

> Built: 2026-06-23 — Cron job sandbox experiment

## Motivation

Research shows **49% of partnership leaders are prioritising AI-driven predictive co-sell** as their primary 2026 investment (Channel as Service, "Future of Channel Partnerships 2026"). Yet no existing tool in this repo handles co-sell orchestration:

| What exists | Gap |
|---|---|
| `channel-mgmt` MCP — deal registration, lead classification | Single-partner deals only, no co-sell credit splits |
| `partner-portal` MCP — deal pipeline management | Partner-side only, no vendor co-sell motion |
| PIRE (2026-06-21) — incentives, rebates | Financial only, no deal orchestration |
| Partner Health Scoring n8n (2026-06-22) | Performance monitoring, no deal routing |

**PCO fills this gap** — it's a lightweight co-sell orchestrator that manages the full lifecycle from opportunity intake to deal close, with credit splitting, partner matching, and automated routing.

## What it does

```
pco opportunity create     — Create a co-sell opportunity with partner & vendor details
pco opportunity list       — List all co-sell opportunities with status filters
pco opportunity show       — View a single opportunity in detail
pco opportunity update     — Update stage, notes, or credit split
pco match                  — Find the best partner match for an unassigned opportunity
pco credit split           — Set or modify revenue/commission credit percentages
pco dashboard              — Show pipeline summary: by stage, by partner, aging, totals
pco serve                  — Start as MCP server for AI agent integration
```

## Quick Start

```bash
# 1. Create a co-sell opportunity
python3 pco.py opportunity create \
  --title "Acme Corp Cloud Migration" \
  --vendor-rep "sarah@vendor.com" \
  --partner-name "TechSolvers Inc" \
  --partner-rep "jim@techsolvers.com" \
  --value 150000 \
  --vendor-split 60 \
  --partner-split 40

# 2. List open opportunities
python3 pco.py opportunity list

# 3. Show a specific opportunity
python3 pco.py opportunity show OPP-0001

# 4. Advance the deal stage
python3 pco.py opportunity update OPP-0001 --stage "demo_completed"

# 5. Find a partner match for an unassigned opp
python3 pco.py match --title "Midwest Healthcare Deal" --value 80000 --region "Midwest"

# 6. Update credit split
python3 pco.py credit split OPP-0001 --vendor 55 --partner 45 --reason "Negotiated rebalance"

# 7. Pipeline dashboard
python3 pco.py dashboard
```

## Sample Data

The prototype includes sample partner data in `sample_partners.json`:

```json
[
  {
    "name": "TechSolvers Inc",
    "tier": "platinum",
    "region": "West",
    "expertise": ["cloud", "saas", "security"],
    "active_deals": 3,
    "engagement_score": 88
  },
  ...
]
```

## Architecture

```
sandbox/2026-06-23/
├── pco.py                  # Main CLI tool + MCP server
├── sample_partners.json    # Sample partner directory for matching
└── README.md               # This file
```

Data is stored at `~/.pco/` (JSON: opportunities, partners, credit_splits, activity_log).

## Co-Sell Deal Model

Each opportunity has:
- **Parties**: vendor rep, partner company, partner rep
- **Credit Split**: vendor %, partner %, with change history and reasons
- **Stages**: `new → partner_accepted → demo_scheduled → demo_completed → proposal_sent → negotiation → closed_won / closed_lost`
- **Aging**: Tracks days in each stage with auto-escalation flags
- **Activity Log**: Every update, split change, and stage transition is recorded

## Partner Matching Algorithm

When an unassigned opportunity comes in, PCO scores potential partners on:
1. **Expertise fit** (weight 40%) — matching opportunity keywords against partner expertise tags
2. **Region match** (weight 30%) — geographic alignment
3. **Tier bonus** (weight 20%) — Platinum +15%, Gold +10%, Authorized +5%
4. **Engagement score** (weight 10%) — recent activity, training completion, MDF utilization

Returns top 3 matches with detailed scoring.

## MCP Server Mode

```bash
pip install mcp
python3 pco.py serve
```

Exposes these tools for AI agents:
- `create_co_sell_opportunity` — Create with full details + credit split
- `list_opportunities` — Filter by status/partner/stage
- `get_opportunity` — Full details with activity log
- `update_opportunity_stage` — Advance through pipeline
- `set_credit_split` — Adjust revenue share with audit trail
- `find_partner_match` — Score and suggest best-fit partners
- `get_pipeline_dashboard` — Aggregated pipeline metrics

## Dependencies

- **CLI mode**: Python 3.10+ (stdlib only — no pip install needed)
- **MCP mode**: `mcp` package (`pip install mcp`)

## What's New / Innovative

1. **Multi-party co-sell deal model** — not just partner deal registration, but true vendor+partner joint motion with explicit credit splits
2. **Audit-trailed credit split changes** — every rebalance is logged with reason and timestamp for dispute resolution
3. **Partner matching algorithm** — multi-factor scoring (expertise, region, tier, engagement) for deal routing
4. **Stage-based pipeline aging** — auto-identifies stale opportunities per stage
5. **Dashboard with actionable metrics** — aging buckets, stage distribution, partner pipeline value
6. **MCP-native** — AI agents can autonomously orchestrate co-sell workflows

## Next Steps

- [ ] Connect to CRM for live deal data ingestion
- [ ] Add automated notifications when deals stall at a stage
- [ ] Integrate with Slack for partner acceptance workflow
- [ ] Add revenue forecasting from co-sell pipeline
- [ ] Web dashboard (micro-app with real-time pipeline view)