## Prototype: PACE — Partner Co-Marketing Campaign Engine
**Date:** 2026-06-29
**Type:** CLI Tool + MCP Server (co-marketing campaign lifecycle automation)
**Status:** Experimental

### What it does
PACE automates the full lifecycle of co-marketing campaigns between vendors and channel partners — from campaign proposal and MDF budget allocation through execution tracking, ROI measurement, and cross-campaign performance benchmarking.

### Why it matters
**68% of MDF budgets go unclaimed** (Forrester) because the administrative overhead of planning, approving, tracking, and measuring co-marketing campaigns is too high. Channel managers juggle spreadsheets, emails, and manual follow-ups for every campaign. PACE replaces this with a structured lifecycle that:

- **Guides partners** through proposal creation with clear fields and budget recommendations
- **Automates MDF allocation** with tier-based limits, reimbursement rates, and performance bonuses
- **Tracks campaign execution** with milestone activities and status transitions
- **Measures ROI** per campaign (MDF ROI, cost per lead, revenue per dollar)
- **Benchmarks performance** across campaign types to identify what works best

No existing tool in this repo handles the **end-to-end co-marketing campaign lifecycle** — existing tools cover MDF requests (partner-portal MCP, n8n approval workflow) and channel ROI (channel-mgmt MCP), but none connect proposal → approval → execution → ROI → benchmarking in a single workflow.

### Research context
- **Forrester**: "68% of MDF budgets go unclaimed due to administrative complexity"
- **ZINFI**: "Channel marketing automation reduces campaign cycle time by 40-60% and improves MDF utilization by 35%"
- **Impartner**: "Partners who run 3+ co-marketing campaigns per year have 2.4x higher lifetime value"
- **Allbound**: "AI-driven budget allocation recommendations are the #1 requested feature for 2026 partner portals"

### Quick Start

```bash
# 1. Load demo data (8 partners, 4 sample campaigns)
python3 pace.py demo

# 2. View the portfolio dashboard
python3 pace.py dashboard

# 3. Check campaign performance benchmarks
python3 pace.py benchmark

# 4. Create a new campaign
python3 pace.py campaign create \
  --title "Q3 Healthcare Webinar" \
  --partner "TechSolvers Inc" \
  --type webinar \
  --description "Joint webinar targeting healthcare IT decision-makers" \
  --goals "200 leads, 15 opportunities, $150K pipeline" \
  --audience "Healthcare IT Directors" \
  --cost 18000 \
  --requested 10000

# 5. Get budget recommendation before approving
python3 pace.py budget recommend \
  --partner "TechSolvers Inc" \
  --total-cost 18000

# 6. Approve and allocate MDF
python3 pace.py campaign approve CAMP-0005 --amount 10000

# 7. Record results when the campaign wraps up
python3 pace.py campaign results CAMP-0005 \
  --leads 225 \
  --opportunities 18 \
  --revenue 180000 \
  --impressions 50000 \
  --engagement 5.2

# 8. Calculate ROI
python3 pace.py roi CAMP-0005

# 9. Close and store benchmark data
python3 pace.py campaign close CAMP-0005

# 10. Re-run benchmarks to see updated performance
python3 pace.py benchmark

# 11. Start as MCP server for AI agent integration
pip install mcp && python3 pace.py serve
```

### Sample Data

8 partners with varying tiers and MDF budgets:

| Partner | Tier | Annual MDF | YTD Usage | Revenue YTD |
|---------|------|-----------|-----------|-------------|
| TechSolvers Inc | Platinum | $30K | $8.5K | $520K |
| EnterpriseOps Group | Platinum | $30K | $12K | $780K |
| DataBridge Partners | Gold | $15K | $3.2K | $210K |
| CloudSync Networks | Gold | $15K | $5.4K | $180K |
| Summit Global | Gold | $15K | $6.8K | $340K |
| Peak Performance Group | Platinum | $30K | $10.5K | $620K |
| Meridian Tech | Gold | $15K | $4.1K | $195K |
| NorthStar Solutions | Authorized | $5K | $0.5K | $45K |

4 sample campaigns in various stages (proposal, approved, in_progress, closed with ROI data).

### Architecture

```
sandbox/2026-06-29/
├── pace.py       # Main CLI tool + MCP server
└── README.md     # This file
```

Data stored at `~/.pace/` (JSON: campaigns, partners, benchmarks).

### Campaign Lifecycle

```
proposal → under_review → approved → in_progress → completed → closed
                              ↓
                          rejected
```

### MDF Budget Allocation Model

| Tier | Per-Campaign Limit | Reimbursement Rate | Performance Bonus |
|------|-------------------|-------------------|-------------------|
| Platinum | $15,000 | 60% | +20% (revenue/MDF > 20x) |
| Gold | $7,500 | 50% | +10% (revenue/MDF > 10x) |
| Authorized | $2,500 | 40% | None |

Recommendation algorithm considers: tier limit, reimbursement rate, MDF remaining, and partner performance (revenue-to-MDF ratio).

### MCP Server Mode

```bash
pip install mcp
python3 pace.py serve
```

Exposes 11 MCP tools for AI agents:

| Tool | Purpose |
|------|---------|
| `create_campaign` | Create new campaign proposal |
| `list_campaigns` | List with status/partner filters |
| `get_campaign` | Full campaign details |
| `update_campaign` | Update status, notes, activities |
| `approve_campaign` | Approve/reject + allocate MDF budget |
| `record_campaign_results` | Log leads, revenue, impressions |
| `calculate_roi` | MDF ROI, CPL, revenue per $ |
| `close_campaign` | Close + store benchmark data |
| `recommend_budget` | Smart MDF budget recommendation |
| `get_benchmarks` | Cross-campaign performance data |
| `get_dashboard` | Portfolio aggregate metrics |
| `load_demo_data` | Load sample partners + campaigns |

### Dependencies

- **CLI mode**: Python 3.10+ (stdlib only — no pip install needed)
- **MCP mode**: `mcp` package (`pip install mcp`)

### What's New / Innovative

1. **End-to-end campaign lifecycle** — not just MDF requests, but the full proposal→approval→execution→ROI→benchmarking pipeline in one tool
2. **Smart MDF budget recommendations** — tier-aware algorithm with performance bonuses based on partner revenue-to-MDF ratio
3. **ROI measurement per campaign** — MDF ROI, cost per lead, revenue per MDF dollar, lead-to-opportunity conversion
4. **Cross-campaign benchmarking** — compare ROI, CPL, and efficiency across campaign types to identify best-performing strategies
5. **Co-investment tracking** — tracks partner contribution vs. vendor MDF for true ROI perspective
6. **Activity tracking** — milestone-based execution tracking with completion status
7. **Portfolio dashboard** — aggregated view of all campaigns, MDF spend, revenue influenced, and overall ROI
8. **MCP-native** — AI agents can autonomously manage the full campaign lifecycle

### Next Steps

- [ ] Connect to CRM for real lead/revenue attribution data
- [ ] Add campaign type-specific templates (webinar briefing, event checklist, email sequence templates)
- [ ] Automated Slack/email notifications when campaigns change status
- [ ] Time-series analytics (campaign performance trends month-over-month)
- [ ] Approval routing based on amount thresholds (auto-approve under $5K for Platinum)
- [ ] Integration with n8n MDF approval workflow for human-in-the-loop budget approval
- [ ] Web dashboard with campaign performance charts
