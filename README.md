# Channel Platform

Consolidated, deployable channel partner management platform. This is the refactor of `channel-tools`: 15 standalone sandbox prototypes merged into 4 modules on a shared SQLite data layer, plus the original MCP servers and n8n workflow library, packaged for Docker deployment.

## What Changed From channel-tools

| Before | After |
|---|---|
| 15 sandbox CLIs, each with its own JSON files and partner schema | 4 modules (`health`, `incentives`, `growth`, `velocity`) on one SQLite schema |
| CHAMP, PRISM, PEDRA, PULSE | `modules/health.py` (health score, churn risk, portfolio concentration) |
| PIRE, PROMOTE, SPARK | `modules/incentives.py` (rebate engine, MDF/SPIF claims, promo ROI, leaderboard) |
| REFER, BRIDGE, PCO | `modules/growth.py` (referral lifecycle, fee calc, partner matching, engagement) |
| CHRONOS, PACE, ASCEND | `modules/velocity.py` (milestone velocity, tier advancement checks) |
| *(new)* Team diagnostics | `modules/team.py` (CAM cadence variance, QBR rubric scoring — manual or AI via Anthropic API, action-item follow-through, rep-vs-baseline coaching views) |
| SYNAPSE, POCUS | Retired (simulator/demo tools; algorithms not carried forward) |
| Hardcoded Apollo API key in lead-dashboard | Env var only (`APOLLO_API_KEY`) — **rotate the old key** |
| Hardcoded infrastructure hostnames in workflows | `example-channel.com` placeholders |
| No packaging | `pip install -e .` gives you `channelctl`; Dockerfile + compose included |

The original scoring weights, tier requirements, benchmarks, and fee rules were ported verbatim from the prototypes, so results match the originals.

## Quick Start

```bash
pip install -e .
channelctl demo                          # seed sample partners
channelctl health score                  # score everyone
channelctl health portfolio              # concentration risk
channelctl growth fee --value 100000 --tier platinum --type enterprise
channelctl velocity advance --partner P002
channelctl team report                   # CAM cadence/QBR/follow-through vs team baseline
channelctl team coach --cam CAM1         # one rep's coaching view
channelctl team score-qbr --cam CAM1 --partner P001 --quarter Q3-2026 --deck-file qbr.txt  # AI rubric scoring (needs ANTHROPIC_API_KEY)
channelctl --help                        # full command list
```

Data lives in a single SQLite file (default `data/channel.db`, override with `CHANNEL_DB`).

## Web Console

`channel_platform/web.py` is a FastAPI dashboard over all modules: portfolio overview with concentration risk, partner book with health/churn ribbons and tier-advancement gap checks, team coaching report (reps vs baseline with flags), referral submission and pipeline, and a claims queue with approve/reject. Single file, no build step.

```bash
pip install -e ".[dashboard]"
uvicorn channel_platform.web:app --host 0.0.0.0 --port 8090
```

Then open http://localhost:8090 (or http://<charlie-tailscale-ip>:8090 once deployed). JSON API lives under `/api/*` for n8n or Hermes to call.

## Deploy (Docker)

```bash
cp .env.example .env    # add your Apollo key
docker compose up -d console        # web console on :8090
docker compose up -d dashboard      # legacy Apollo lead dashboard on :8080 (optional)
```

The compose file also defines the two MCP servers as services sharing the same data volume. For MCP use with Claude/Hermes, run them via stdio config instead:

```yaml
mcp_servers:
  channel-mgmt:
    command: python3
    args: ["src/main.py"]
    cwd: "/path/to/channel-platform/mcp-servers/channel-mgmt"
  partner-portal:
    command: python3
    args: ["src/main.py"]
    cwd: "/path/to/channel-platform/mcp-servers/partner-portal"
```

## Layout

```
channel-platform/
├── channel_platform/        # the consolidated package
│   ├── db.py                # shared SQLite layer, unified partner schema
│   ├── cli.py               # channelctl entrypoint
│   └── modules/             # health, incentives, growth, velocity
├── mcp-servers/             # channel-mgmt (8 tools), partner-portal (5 tools) — unchanged
├── micro-apps/lead-dashboard/  # FastAPI UI (key now env-only)
├── n8n-workflows/           # 16 importable workflows (hostnames now placeholders)
├── Dockerfile / docker-compose.yml
└── pyproject.toml
```

## n8n Workflows

Import the JSON files into your n8n instance, then find-and-replace `example-channel.com` with your domain and update credential IDs. Full catalog in `n8n-workflows/README.md`.

## Security Notes

- The Apollo API key formerly committed to the public repo should be rotated in the Apollo dashboard. It remains in the old repo's git history until that history is rewritten or the repo is replaced.
- Never commit `.env`.
