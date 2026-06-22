# PIRE — Partner Incentive & Rebate Engine

**Experimental prototype** — A CLI tool + MCP server for designing, managing, and calculating channel partner incentive programs, rebates, and MDF (Market Development Fund) claims.

> Built: 2026-06-21 — Cron job sandbox experiment

## Motivation

Existing tools in `mcp-servers/channel-mgmt/` cover partner onboarding, deal registration, lead classification, and ROI calculation — but none handle the **incentive program design**, **rebate computation**, and **MDF claims processing** that channel managers spend most of their time on. This prototype fills that gap.

**Research sources:** Futurum 5 Key Predictions (2025), Channelscaler State of Partnering 2025, ZINFI MDF automation, LinkedIn AI partner marketing trends, production channel program docs.

## What it does

```
pire program create            — Design a tiered incentive program with rebate rates, accelerators, SPIFFs
pire program list/show         — Browse and inspect programs
pire rebate calculate          — Compute earned rebates from transaction data (JSON/CSV)
pire mdf submit/list/approve   — Full MDF claim lifecycle
pire payout generate           — Generate payout reports by program or partner
pire report program/partner    — ROI analysis and performance summaries
pire serve                     — Start as MCP server for AI tool integration
```

## Quick Start

```bash
# 1. Create an incentive program
python3 pire.py program create "Partner-2026" \
  --description "2026 partner incentive program"

# 2. Calculate rebates from transaction data
python3 pire.py rebate calculate "Partner-2026" "AcmeCorp" sample_transactions.json

# 3. Submit and approve an MDF claim
python3 pire.py mdf submit "Partner-2026" "AcmeCorp" 12000 --description "Joint webinar"
python3 pire.py mdf approve MDF-0001

# 4. Generate a payout report
python3 pire.py payout generate "Partner-2026" --period "Q2-2026"

# 5. View program ROI
python3 pire.py report program "Partner-2026"
```

## Sample Data

`sample_transactions.json` contains 7 deals for testing:
```json
[
  {"deal": "D-001", "revenue": 150000, "is_registered": "yes", "is_new_logo": "yes"},
  ...
]
```

## Architecture

```
sandbox/2026-06-21/
├── pire.py                  # Main CLI tool + MCP server
├── sample_transactions.json # Test data
└── README.md                # This file
```

Data is stored at `~/.pire/` (JSON files for programs, transactions, MDF claims, payouts).

## Incentive Program Model

Each program has:
- **Tiers** (Silver → Elite) with revenue thresholds and rebate percentages
- **Rules**: minimum transactions, deal registration bonuses, new logo bonuses, SPIFFs, accelerators, MDF budget percentages
- **MDF**: claims with approval workflow, budget tracking, over-budget alerts

## MCP Server Mode

```bash
pip install mcp
python3 pire.py serve
```

Exposes these tools for AI agents:
- `design_incentive_program` — Create program with tiers/rules
- `calculate_partner_rebate` — Compute rebate from transactions
- `submit_mdf_claim` / `approve_mdf_claim` — MDF lifecycle
- `generate_payout_report` / `get_program_report` / `get_partner_report` — Analytics

## Dependencies

- **CLI mode**: Python 3.10+ (stdlib only — no pip install needed)
- **MCP mode**: `mcp` package (`pip install mcp`)

## What's New / Innovative

1. **Unified incentive + MDF management** in a single tool (no PRM vendor lock-in)
2. **Budget-aware MDF claims** — warns when claims exceed partner's allocated MDF budget
3. **Accelerator thresholds** — automatic bonus when partners exceed revenue targets
4. **Deal registration + new logo bonuses** stack together for top performers
5. **Program ROI reporting** — combines rebate costs + MDF spend against revenue
6. **MCP-native** — designed to be used by AI agents for autonomous channel program management

## Next Steps

- [ ] Connect to CRM data via API for live transaction feeds
- [ ] Add tier promotion/demotion rules based on trailing performance
- [ ] Auto-generate partner-facing incentive program PDFs
- [ ] Add audit log for MDF claims and rebate calculations
- [ ] Web dashboard (micro-app)