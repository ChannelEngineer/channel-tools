# Channel Tools

> MCP-driven tools for **partner program management, deal registration, and channel operations.**
>
> *Built by a channel professional, for channel professionals.*

## What This Is

This repository demonstrates a complete, production-grade channel management framework encoded as composable MCP (Model Context Protocol) servers. Every tool is grounded in the **Chanimal Channel Kit** — a collection of 75 documents, templates, and policies refined across **over 200 channel program launches**.

This isn't theory. These are the actual mechanics of running a world-class partner program.

## What It Demonstrates

**1. Partner Program Architecture** — The three-tier model (Authorized → Gold → Platinum) with progressive benefits, margin structures, and requirements. Every tier has clearly defined lead access, deal registration privileges, MDF eligibility, and certification paths.

**2. Deal Registration** — Domain of the most mature channel programs. Accounts-based (not territory-based) deal registration with margin bumps, exclusivity periods, rules of engagement, and Jump Start incentives for new partners. Includes conflict detection, loyalty mechanics, and first-come-first-serve arbitration.

**3. Lead Management** — A/B/C lead classification with hard SLA enforcement (2-day claim window, 5-day follow-up, auto-reassignment on breach). Priority routing by partner tier and certification level.

**4. Partner Enablement** — Structured onboarding (Weeks 1-4 + 90-day check-in), NFR quiz for free software access, orientation checklists, and portfolio portal setup.

**5. Channel Policies** — Complete policy library: lead distribution, deal registration terms, MDF reimbursement (50% co-op, 90-day claim window), NFR access, partner locator requirements.

## Architecture

```
channel-tools/
├── mcp-servers/
│   ├── channel-mgmt/        # Program design, deal reg, lead mgmt, policies, onboarding
│   └── partner-portal/       # Locator, MDF, NFR quiz, orientation, deal pipeline
├── micro-apps/               # Frontend UIs and dashboards (in progress)
├── scripts/                  # Automation helpers
└── docs/                     # Setup and deployment guides
```

### MCP Servers (13 tools)

| Server | Tool | Function |
|---|---|---|
| **channel-mgmt** | `design_partner_program` | Generate 3-tier program (Authorized/Gold/Platinum) with benefits grid and margin structure |
| | `register_deal` | Register partner deals with margin bumps, exclusivity, and rules of engagement |
| | `classify_lead` | A/B/C lead classification with SLA enforcement and auto-reassign |
| | `generate_policy` | 6 policy documents: lead policy, deal registration, MDF, NFR, program overview, onboarding |
| | `onboard_partner` | Full partner onboarding plan (Weeks 1-4 + 90-day check-in) |
| | `design_distribution_model` | 10 distribution types: referral, VAR, white label, distributor, VAD, SaaS distributor, consultant, rep firm |
| | `calculate_channel_roi` | Reseller lifetime value, recruitment ROI, promotional budget returns |
| | `forecast_channel_sales` | 12-month channel sales forecast with ramp-up and cash flow projections |
| **partner-portal** | `find_partners` | Search partner locator by zip/region, prioritized by tier and certification |
| | `request_mdf` | Submit MDF requests with policy guidance and reimbursement calculation |
| | `nfr_quiz` | Generate and grade the 10-question NFR quiz for free software access |
| | `portal_orientation` | Partner getting-started checklist covering setup, training, locator listing |
| | `manage_deals` | List, renew, close, and summarize deal registrations |

## Quick Start

```bash
git clone https://github.com/ChannelEngineer/channel-tools.git
cd channel-tools/mcp-servers/channel-mgmt
pip install mcp
python3 src/main.py
```

## Running with Hermes Agent

```yaml
mcp_servers:
  channel-mgmt:
    command: python3
    args: ["src/main.py"]
    cwd: "/path/to/channel-tools/mcp-servers/channel-mgmt"
  partner-portal:
    command: python3
    args: ["src/main.py"]
    cwd: "/path/to/channel-tools/mcp-servers/partner-portal"
```

## Domain Knowledge

The Chanimal Channel Kit (106 documents — 2026 edition) covers every aspect of channel program execution:

- **Program design** — Tier structures, level grids, competitive analysis templates, **CRM margin comparisons** (23 vendor programs analyzed)
- **Recruiting** — Phone scripts, email sequences, application forms, qualification criteria, **affiliate/referral templates**
- **Onboarding** — Orientation checklists, portal setup, training paths, NFR enablement, **referral approval emails**
- **Policy** — Deal registration, lead distribution, MDF/co-op, NFR, pricing guidelines, **referral program terms**
- **Marketing** — Product introduction templates, SEO guides, plan of action templates, 25/50/100 word product descriptions
- **Sales enablement** — Demo scripts, competitive matrix, presentations, ROI analysis, **channel ROI calculator**
- **Operations** — Partner locator, portal content, webinar guidelines, order processing, **distribution models**, **sales forecasting**
- **Channel strategy** — Direct vs indirect analysis, **channel ROI presentation** (712x ROI case study), **distribution model decision framework**

## Roadmap

- [ ] **channel-analytics** MCP server (program health, partner performance, pipeline analysis)
- [ ] Micro-app dashboards
- [ ] Docker deployment
- [ ] CI/CD pipeline

---

*Built by ChannelEngineer. Grounded in real channel practice, not generic templates.*