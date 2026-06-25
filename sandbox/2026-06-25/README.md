## Prototype: CHAMP — Channel Health & Audit Monitoring Platform
**Date:** 2026-06-25
**Type:** CLI Tool + MCP Server
**Status:** Experimental

### What it does
CHAMP automates partner program compliance auditing and tier management — tracking whether partners meet program requirements (certifications, quotas, training, MDF utilization, deal registration activity), surfacing compliance gaps, and generating tier promotion/demotion recommendations. Think of it as a continuous compliance auditor for your channel program.

### Why it matters
Channel managers spend an estimated **20-30% of their time** manually checking partner compliance against program requirements — chasing certification renewals, verifying quota attainment, reviewing MDF proof-of-performance, and deciding tier assignments. Existing tools (channel-mgmt MCP, PIRE, partner-health-scoring n8n) handle program design, incentives, and deal health, but none automate **program compliance auditing**. CHAMP fills this gap with a data-driven compliance engine that surfaces actionable audit findings and tier change recommendations.

### Research context
The channel docs (Partner Program & Portal Checklists, Program Level Grids, Benefits & Requirements) reveal the complexity of multi-tier program compliance. The tier grids define specific requirements per level (Authorized → Gold → Platinum), but there's no automated way to verify partners meet them. Meanwhile, industry trends point to **AI-driven partner program management** and **continuous compliance monitoring** as key 2025-2026 innovations (ZINFI, Impartner, Channel Mechanics all investing in compliance automation).

### Quick Start

```bash
# 1. Define your program tiers with requirements
python3 champ.py program define \
  --name "Partner-2026" \
  --tiers authorized,gold,platinum \
  --requirements '{"authorized":{"min_revenue":0,"certifications":0,"min_deals":0,"training_hours":2},"gold":{"min_revenue":50000,"certifications":1,"min_deals":5,"training_hours":10,"mdf_utilization_pct":30},"platinum":{"min_revenue":200000,"certifications":2,"min_deals":15,"training_hours":20,"mdf_utilization_pct":50}}'

# 2. Add partner performance data
python3 champ.py partner add \
  --name "TechSolvers Inc" \
  --tier gold \
  --revenue 72000 \
  --deals 8 \
  --certifications 1 \
  --training-hours 12 \
  --mdf-used 3500 \
  --mdf-allocated 10000 \
  --portal-logins 24 \
  --days-since-last-deal 15

# 3. Run compliance audit for a partner
python3 champ.py audit partner --name "TechSolvers Inc"

# 4. Run full program audit
python3 champ.py audit program --program "Partner-2026"

# 5. Get tier promotion/demotion recommendations
python3 champ.py tier recommend

# 6. Generate compliance report
python3 champ.py report --format json --output report.json

# 7. Start as MCP server
pip install mcp && python3 champ.py serve
```

### Sample Data
The tool auto-creates sample partners and a default program. Run `python3 champ.py demo` to load 5 sample partners with varying compliance profiles.

### Architecture

```
sandbox/2026-06-25/
├── champ.py              # Main CLI tool + MCP server
├── sample_partners.json   # 5 sample partners for testing
└── README.md              # This file
```

Data is stored at `~/.champ/` (JSON: program, partners, audit_results, tier_changes, compliance_reports).

### Compliance Scoring Model

Each partner gets a **Compliance Score (0-100%)** based on weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Revenue attainment | 25% | Actual vs tier minimum revenue |
| Deal registration activity | 20% | Actual deals vs tier minimum required |
| Certification status | 20% | Certifications held vs tier requirement |
| Training completion | 15% | Training hours completed vs required |
| MDF utilization | 10% | MDF claimed vs allocated (not too little, not too much) |
| Portal engagement | 5% | Portal logins vs expected baseline |
| Deal recency | 5% | Days since last deal registered |

### Tier Change Logic

- **Promotion eligible**: Score ≥ 80% AND meets ALL hard requirements (revenue, certifications, deals) of the NEXT tier
- **At risk (demotion warning)**: Score < 60% OR misses 2+ hard requirements of CURRENT tier
- **Demotion recommended**: Score < 40% OR misses 3+ hard requirements for > 90 days
- **Stable**: Everything in between

### MCP Server Mode

```bash
pip install mcp
python3 champ.py serve
```

Exposes these tools for AI agents:
- `define_program` — Create/update tier requirements
- `add_partner` — Add partner performance data
- `audit_partner` — Run compliance check for one partner
- `audit_program` — Full program compliance audit
- `get_tier_recommendations` — Promotion/demotion suggestions
- `generate_compliance_report` — Structured compliance report

### Dependencies

- **CLI mode**: Python 3.10+ (stdlib only — no pip install needed)
- **MCP mode**: `mcp` package (`pip install mcp`)

### What's New / Innovative

1. **Multi-factor compliance scoring** — combines revenue, certifications, deals, training, MDF, engagement into a single score
2. **Tier promotion/demotion automation** — data-driven recommendations based on trailing performance, not calendar cycles
3. **Continuous audit engine** — not a one-time check, designed for regular (weekly/monthly) automated runs
4. **Program-level aggregated compliance** — see at a glance which partners are compliant, at risk, or non-compliant
5. **MDF utilization as compliance metric** — both under-utilization and over-utilization are flagged (under = low engagement, over = risk of fund exhaustion)
6. **MCP-native** — AI agents can autonomously run compliance audits and recommend tier changes

### Next Steps

- [ ] Connect to CRM for live revenue/deal data
- [ ] Add automated Slack alerts for tier changes
- [ ] Integrate with learning platform for live certification data
- [ ] Web dashboard with compliance heatmap
- [ ] Add trend analysis (score change over time)