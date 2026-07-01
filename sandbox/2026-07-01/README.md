## Prototype: SYNAPSE — Partner Synergy & Ecosystem Intelligence Platform
**Date:** 2026-07-01
**Type:** CLI Tool + MCP Server (ecosystem network analysis engine)
**Status:** Experimental

### What it does
SYNAPSE maps the partner ecosystem as an **interconnected graph** — not as a flat list of partners — and applies network science to reveal hidden structure: **who the true influencers are**, **which partners bridge otherwise disconnected clusters**, **where ecosystem coverage is thin**, and **which partners would create the most value by connecting**.

Think of it as **LinkedIn's "People You May Know" + network analytics for your channel partner ecosystem.**

### Why it matters
Every channel program talks about "partner ecosystem orchestration" — but the tools to actually *analyze* the ecosystem as a network don't exist in this repo. Existing tools answer "how is Partner X doing?" (PRISM, CHAMP, partner health scoring) but **none answer "how is the ecosystem connected as a whole?"**

Key insight: **The network itself has value.** A partner with few direct deals but high betweenness centrality connects clusters that would otherwise be silos — and that partner is more strategically valuable than their raw deal count suggests. Conversely, a partner with high revenue but zero ecosystem connections is a single point of failure.

### Research context
- **WorkSpan & Impartner**: Both investing heavily in "ecosystem orchestration" features — partner-to-partner connections, co-sell matching, ecosystem discovery — but these are portal features, not analytical tools
- **TSIA State of Channel Partnerships 2026**: "Ecosystem management is the #1 capability gap for channel organizations"
- **Industry trend**: Partner ecosystem analytics is an emerging category — Gartner's "Ecosystem Operating Model" identifies network analysis as a key capability for 2026+
- **No existing tool in this repo** analyzes the partner ecosystem as a network graph

### Quick Start

```bash
# 1. Load demo ecosystem data (12 partners, 20 co-sell edges, 9 referral edges)
python3 synapse.py demo

# 2. View the partner network graph (ASCII)
python3 synapse.py graph

# 3. Show network centrality metrics (influence, degree, betweenness)
python3 synapse.py metrics

# 4. Detect partner communities/clusters
python3 synapse.py clusters

# 5. Identify coverage gaps by region, vertical, capability
python3 synapse.py gaps

# 6. Get strategic pairing recommendations
python3 synapse.py recommend

# 7. Calculate synergy between two specific partners
python3 synapse.py pair --p1 "CloudSync Networks" --p2 "TechSolvers Inc"

# 8. Drill into a specific partner's intelligence report
python3 synapse.py partner "EnterpriseOps Group"

# 9. Executive ecosystem dashboard
python3 synapse.py dashboard

# 10. Start as MCP server for AI agent integration
pip install mcp && python3 synapse.py serve
```

### Sample Data
12 partners with varying tiers, regions, and verticals:

| Partner | Tier | Region | Revenue | Verticals |
|---------|------|--------|---------|-----------|
| TechSolvers Inc | Platinum | West | $850K | healthcare, fintech |
| EnterpriseOps Group | Platinum | Northeast | $1.2M | enterprise, manufacturing, healthcare |
| DataBridge Partners | Gold | Midwest | $420K | finance, insurance |
| CloudSync Networks | Gold | West | $310K | saas, tech, healthcare |
| Summit Global | Gold | Southeast | $520K | retail, manufacturing, logistics |
| Peak Performance Group | Platinum | Southwest | $620K | energy, utilities |
| Meridian Tech | Gold | Mid-Atlantic | $195K | education, government, nonprofit |
| NorthStar Solutions | Authorized | West | $95K | small_business, tech |
| Velocity Systems | Gold | Northeast | $480K | fintech, healthcare, enterprise |
| Equinox Partners | Authorized | Southeast | $78K | retail, hospitality |
| Titan Cloud Group | Platinum | Midwest | $980K | manufacturing, logistics, energy |
| NexGen Solutions | Gold | Pacific NW | $350K | tech, saas, gaming |

20 co-sell relationships and 9 referral edges connect these partners in a realistic ecosystem network.

### Architecture

```
sandbox/2026-07-01/
├── synapse.py       # Main CLI tool + MCP server
└── README.md        # This file
```

Data stored at `~/.synapse/ecosystem.json` (JSON: partners, co-sell edges, referral edges).

### How It Works

#### Network Model
SYNAPSE builds a **multi-relational graph** with:
- **Partners** as nodes (with attributes: tier, region, verticals, capabilities, certifications, revenue, deals)
- **Co-sell relationships** as undirected edges (weighted by joint deal count)
- **Referral relationships** as directed edges (weighted by referral count)

#### Synergy Scoring (0-100)
For any two partners, SYNAPSE calculates a multi-factor synergy score:

| Factor | Max | What It Measures |
|--------|-----|-----------------|
| Direct relationship | 40 | Existing co-sell deals + referrals exchanged |
| Vertical overlap | 15 | Shared industry verticals |
| Capability complementarity | 15 | Unique capabilities each brings (not duplicate) |
| Region proximity | 10 | Same geographic region |
| Mutual connections | 10 | Common partners in network |
| Tier compatibility | 10 | Same or adjacent tier levels |

#### Network Metrics
- **Degree Centrality**: How many connections a partner has (raw network reach)
- **Betweenness Centrality**: How often a partner sits on the shortest path between others (bridging power)
- **Composite Influence Score**: Weighted combination of network position + deals + revenue

#### Cluster Detection
Uses **label propagation** to detect natural partner communities based on relationship density.

#### Coverage Gap Analysis
Identifies:
- **Uncovered regions** — regions with zero partner presence
- **Under-served regions** — only authorized-level partners, no Gold/Platinum
- **Thin vertical coverage** — verticals served by only one partner
- **Scarce capabilities** — capabilities held by < 3 partners

### Commands

| Command | Purpose |
|---------|---------|
| `demo` | Load demo ecosystem data |
| `graph` | ASCII network graph visualization |
| `metrics` | Centrality & influence scores |
| `clusters` | Community detection |
| `gaps` | Coverage gap analysis |
| `recommend` | Strategic pairing recommendations |
| `pair --p1 X --p2 Y` | Synergy score for two partners |
| `partner NAME` | Full intelligence report for a partner |
| `dashboard` | Executive ecosystem summary |
| `serve` | Start as MCP server |

### MCP Server Mode

```bash
pip install mcp
python3 synapse.py serve
```

Exposes 9 MCP tools for AI agents:

| Tool | Purpose |
|------|---------|
| `load_demo_ecosystem` | Load demo data with 12 partners |
| `get_ecosystem_summary` | Executive ecosystem overview |
| `get_partner_intel` | Full network intelligence for a partner |
| `calculate_synergy` | Synergy score between two partners |
| `get_top_influencers` | Top N ecosystem influencers |
| `detect_clusters` | Detect partner communities |
| `get_coverage_gaps` | Coverage gap analysis |
| `get_pairing_recommendations` | Strategic pairing suggestions |
| `get_network_metrics` | Network centrality metrics for all partners |

### Dependencies
- **CLI mode**: Python 3.10+ (stdlib only — no pip install needed)
- **MCP mode**: `mcp` package (`pip install mcp`)

### What's New / Innovative

1. **First ecosystem network analysis tool in this repo** — not a flat list or individual partner score, but a relational graph model of the entire partner ecosystem
2. **Multi-factor synergy scoring** — combines relationship history, vertical overlap, capability complementarity, region proximity, mutual connections, and tier compatibility into a single actionable score
3. **Network centrality metrics** — identifies partners whose strategic value exceeds their raw deal count (high betweenness bridges, ecosystem influencers)
4. **Community detection** — reveals natural partner clusters that might not be obvious from individual partner data
5. **Coverage gap analysis** — multi-dimensional (region, vertical, capability) ecosystem coverage with actionable recommendations
6. **Strategic pairing recommendations** — "People You May Know" for channel partners, suggesting connections that would create the most ecosystem value
7. **Partner intelligence reports** — full drill-down showing a partner's network position, co-sell partners, referral patterns, and suggested new connections
8. **MCP-native** — AI agents can autonomously analyze the entire partner ecosystem network

### Next Steps
- [ ] Connect to real CRM/PRM data to build live ecosystem graphs
- [ ] Add partner-to-partner referral program tracking
- [ ] Add time-series network analysis (ecosystem evolution over time)
- [ ] Web dashboard with interactive network visualization (D3.js force-directed graph)
- [ ] Automated Slack alerts for ecosystem anomalies (bridge partner churning, cluster fragmentation)
- [ ] Export network metrics for integration with PRISM (risk scoring) and PACE (co-marketing)
- [ ] Integration with channel-mgmt MCP for automated program design based on ecosystem gaps