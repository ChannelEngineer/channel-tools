# Channel Tools

MCP-driven tools for **partner program management, deal registration, and channel operations.**
Grounded in the Chanimal Channel Kit — a production-proven channel framework from 200+ program launches.

**Note:** Lead sourcing, enrichment, and outreach belong in [Resonate-IQ](https://github.com/ChannelEngineer/resonate-iq) (the AI communications platform). This repo focuses on the partner ecosystem.

## Architecture

```
channel-tools/
├── mcp-servers/
│   ├── channel-mgmt/      # Partner program design, deal registration, lead classification, policies, onboarding
│   └── partner-portal/     # Partner locator, MDF requests, NFR quiz, orientation, deal management
├── micro-apps/             # Frontend UIs and dashboards
├── scripts/                # Automation helpers
└── docs/                   # Setup and deployment guides
```

## MCP Servers

| Server | Tools | What it does |
|--------|-------|-------------|
| **channel-mgmt** | `design_partner_program` | Generate 3-tier program (Authorized/Gold/Platinum) with benefits grid and margin structure |
| | `register_deal` | Register partner deals with margin bumps, exclusivity, and rules of engagement |
| | `classify_lead` | A/B/C lead classification with SLA enforcement and auto-reassign |
| | `generate_policy` | 6 policy documents: lead policy, deal registration, MDF, NFR, program overview, onboarding |
| | `onboard_partner` | Full partner onboarding plan (Weeks 1-4 + 90-day check-in) |
| **partner-portal** | `find_partners` | Search partner locator by zip/region, prioritized by tier |
| | `request_mdf` | Submit MDF requests with policy guidance and reimbursement calc |
| | `nfr_quiz` | Generate and grade the 10-question NFR quiz for free software |
| | `portal_orientation` | Partner getting-started checklist covering setup, training, locator |
| | `manage_deals` | List, renew, close, and summarize deal registrations |

## Quick Start

```bash
# Clone
git clone https://github.com/ChannelEngineer/channel-tools.git
cd channel-tools

# Set up
cd mcp-servers/channel-mgmt
pip install mcp

# Run
python3 src/main.py
```

## Running with Hermes Agent

Add to your `config.yaml`:

```yaml
mcp_servers:
  channel-mgmt:
    command: python3
    args: ["src/main.py"]
    cwd: "/path/to/channel-tools/mcp-servers/channel-mgmt"
```

## Roadmap

- [ ] **channel-analytics** MCP server (program health, partner performance, pipeline analysis)
- [ ] Micro-app dashboards
- [ ] Docker deployment
- [ ] CI/CD pipeline