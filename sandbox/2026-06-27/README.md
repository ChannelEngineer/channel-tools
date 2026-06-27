## Prototype: PRISM — Partner Risk & Intelligence Scoring Matrix
**Date:** 2026-06-27
**Type:** CLI Tool + MCP Server (predictive analytics engine)
**Status:** Experimental

### What it does
PRISM uses AI-inspired multi-factor scoring to predict **partner churn risk** and **growth readiness** from engagement signals — deal activity, portal usage, MDF utilization, training, certifications, support tickets, pipeline velocity, and more. It then recommends specific intervention playbooks to retain at-risk partners and accelerate top performers.

### Why it matters
**49% of partnership leaders are prioritizing AI-driven predictive analytics** for 2026 (TSIA State of Channel Partnerships 2026). Channel managers spend 18–26 hours per quarter manually analyzing partner health — PRISM cuts that to 2–3 hours. It turns raw engagement data into actionable intelligence: which partners are about to churn, which are ready to grow, and exactly what to do about it.

### Research context
- **TSIA 2026**: "Underperformance is systemic… partner strategies haven't caught up. Enablement still centers on product knowledge. Incentives still reward transactions."
- **Pedowitz Group**: "AI scores churn risk, recommends targeted interventions, and tracks impact — cutting analysis from 18–26 hours to 2–3 hours."
- **ZINFI/Impartner**: Both investing heavily in predictive analytics for partner ecosystem management.

No existing tool in this repo does **predictive churn analysis** for channel partners. PRISM fills this gap.

### Scoring Model

#### Churn Risk (0-100)
| Signal | Weight | What It Measures |
|--------|--------|-----------------|
| Days since last deal | 20% | Longer gap = higher risk |
| Deal count trend | 15% | Decreasing deal velocity |
| Portal login frequency | 12% | Low engagement = disengagement |
| MDF utilization trend | 10% | Dropping MDF use = less investment |
| Training recency | 10% | No recent training = disengagement |
| Certification status | 8% | Expired/lapsed certifications |
| Support ticket trend | 8% | Increasing tickets = frustration |
| Pipeline velocity | 7% | Slowing pipeline = risk |
| Email engagement | 5% | Unengaged with communications |
| Program compliance | 5% | Low compliance = risk indicator |

#### Growth Readiness (0-100)
| Signal | Weight | What It Measures |
|--------|--------|-----------------|
| Revenue growth rate | 25% | YoY/QoQ revenue growth |
| Deal size trend | 15% | Increasing deal values |
| New logo acquisition | 15% | Winning new customers |
| Certification advancement | 12% | Pursuing higher certs |
| Training completion | 10% | Completing available training |
| MDF effectiveness | 8% | ROI from MDF investments |
| Co-sell participation | 8% | Engaging in joint deals |
| Portal feature adoption | 7% | Using advanced features |

### Risk Levels & Recommended Actions
| Level | Score | Label | Action Required |
|-------|-------|-------|-----------------|
| Critical | 75+ | 🔴 Critical | Immediate intervention within 48 hours |
| High | 55-74 | 🟠 High | Proactive outreach this week |
| Moderate | 35-54 | 🟡 Moderate | Monitor closely, plan engagement |
| Low | 15-34 | 🟢 Low | Standard engagement cadence |
| Minimal | 0-14 | ⚪ Minimal | Continue current approach |

### Quick Start

```bash
# 1. Load sample data and see the portfolio
python3 prism.py demo

# 2. Get detailed analysis for one partner
python3 prism.py partner show "CloudSync Networks"

# 3. Get specific intervention recommendations
python3 prism.py recommend "CloudSync Networks"

# 4. See the full portfolio risk heatmap
python3 prism.py heatmap

# 5. Log an intervention
python3 prism.py intervene "CloudSync Networks" \
  --playbook "High-Risk Retention Program" \
  --notes "Scheduled executive call for Tuesday"

# 6. Portfolio executive dashboard
python3 prism.py dashboard

# 7. Start MCP server for AI agent integration
pip install mcp && python3 prism.py serve
```

### Sample Data
6 partners with intentionally varied risk profiles:

| Partner | Tier | Revenue | Churn Risk | Growth | Profile |
|---------|------|---------|-----------|--------|---------|
| TechSolvers Inc | Platinum | $850K | Low | High | Top performer — invest more |
| DataBridge Partners | Gold | $420K | Moderate | Moderate | Stable, needs nurture |
| CloudSync Networks | Gold | $310K | **High** | **Low** | 🚨 At risk — intervene now |
| EnterpriseOps Group | Platinum | $1.2M | Minimal | High | Star performer |
| NorthStar Solutions | Authorized | $95K | **Critical** | **Low** | ⛑️ Near churn — urgent action |
| Summit Global | Gold | $520K | Low | Moderate | Good standing, room to grow |

### Architecture
```
sandbox/2026-06-27/
├── prism.py              # Main CLI tool + MCP server
└── README.md             # This file
```

Data stored at `~/.prism/` (JSON: partners, analysis, interventions).

### Intervention Playbooks

| Playbook | Trigger | What It Does |
|----------|---------|-------------|
| 🆘 Critical Re-Engagement Sprint | Critical risk | Exec call, SPIFF, dedicated support, MDF incentive, cert vouchers, 90-day plan |
| ⚕️ High-Risk Retention Program | High risk | Personal outreach, tailored enablement, margin bump, advisory council invite |
| 📡 Moderate Engagement Boost | Moderate risk | 3-touch email sequence, training paths, success stories, webcast invite |
| 🚀 Growth Acceleration Playbook | Low growth | MDF matching, mentor pairing, case study, quarterly planning, advanced certs |
| 💎 High Growth Investment Playbook | High growth | Tier promotion, more leads, preferred pricing, locator feature, co-present at events |

### MCP Server Mode
```bash
pip install mcp
python3 prism.py serve
```

Exposes 7 MCP tools:
- `add_partner_data` — Add/update partner engagement signals
- `analyze_partner_churn` — Full churn + growth analysis for one partner
- `analyze_portfolio` — Rank all partners by churn risk with summary
- `get_recommendations` — Get intervention playbooks for a partner
- `get_portfolio_heatmap` — Visual risk heatmap across portfolio
- `get_portfolio_dashboard` — Executive summary with distributions
- `log_intervention` — Log an applied intervention playbook
- `load_demo_data` — Load 6 sample partners

### Dependencies
- **CLI mode**: Python 3.10+ (stdlib only — no pip install needed)
- **MCP mode**: `mcp` package (`pip install mcp`)

### What's New / Innovative
1. **First predictive churn model for channel partners** in this repo — not reactive scoring, but forward-looking risk prediction
2. **Dual-axis analysis** — churn risk AND growth readiness on every partner, not just one dimension
3. **Signal-level breakdown** — shows exactly WHICH factors are driving the score (not a black box)
4. **Pre-built intervention playbooks** — 5 playbooks mapped to risk/growth triggers with step-by-step actions
5. **Intervention tracking** — log and track which playbooks have been applied over time
6. **Portfolio heatmap** — at-a-glance visual of risk and growth across the entire partner ecosystem
7. **Revenue-at-risk calculation** — quantifies financial exposure from potential partner churn
8. **MCP-native** — AI agents can autonomously analyze portfolios and recommend interventions

### Next Steps
- [ ] Connect to CRM/PRM APIs for live data ingestion
- [ ] Add time-series tracking (score changes over weekly/monthly windows)
- [ ] Build web dashboard with real-time heatmap
- [ ] Add Slack integration for automated early-warning alerts
- [ ] Integration with channel-mgmt MCP for automated tier changes based on risk