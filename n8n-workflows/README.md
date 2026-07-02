# ⚡ n8n Workflows — Channel Management Automation

> Importable JSON workflow files ready to drop into your n8n instance at `navitools.net`.

Workflows here automate partner program operations that are better done as **event-driven multi-step processes** than MCP tool calls — human approval chains, Slack notifications, CRM sync, email sequences, etc.

## How to Use

1. Open your n8n instance at https://n8n.navitools.net
2. Workflows → Import from File → Select the `.json` file
3. Update credential IDs and webhook URLs to match your setup
4. Activate

## Workflow Catalog

||| Workflow | Nodes | What It Does |
|||----------|-------|-------------|
||| `deal-registration-auto-approval.json` | 11 | Auto-approve deal registrations for Gold/Platinum partners under $50K; manual review otherwise |
||| `mdf-request-budget-approval.json` | 16 | MDF budget check with tier-based auto-approval (Platinum ≤$10K) or manual review |
||| `partner-onboarding-automation.json` | 21 | Full partner onboarding lifecycle: welcome email, portal credentials, Day 3/7/30 follow-ups, Slack notifications, escalation to channel director |
||| `2026-06-22-partner-health-scoring.json` | 17 | Partner Health Score & Early Warning System — multi-factor health scoring (deals, MDF, engagement, training) with Green/Yellow/Red routing, Slack alerts, email escalation |
||| `2026-06-24-partner-recruiting-pipeline.json` | 17 | Partner recruiting pipeline — application intake, AI scoring/qualification, auto-approval (≥60pts) with onboarding, manual review with Slack escalation for lower scores, Google Sheets audit logging |
|||| `2026-06-26-partner-agreement-renewal.json` | 24 | Partner Agreement Renewal & Lifecycle Automation — contract expiry tracking with 90/60/30 day notification cadence, multi-factor renewal scoring (revenue, deals, training, certs, engagement), auto-renewal for strong performers (≥70pts), manual review with performance warnings for below-threshold partners, Slack alerts, email notifications, Google Sheets audit trail |
|||| `2026-06-28-partner-lead-routing.json` | 14 | Partner Lead Routing & Distribution Automation — webhook-based lead intake, lead classification (high-value ≥$50K or Enterprise → manual review, standard → auto-route), tier/geography-based partner matching, Slack alerts to channel managers and partners, email confirmations to lead sources and assigned partners, Google Sheets audit trail |
|||||| `2026-06-30-deal-conflict-resolution.json` | 26 | Deal registration conflict detection — auto-approves clean registrations, resolves conflicts by tier priority (Platinum > Gold > Authorized), and escalates same-tier conflicts to channel managers with Slack + email notifications. |
||||| `2026-07-02-partner-certification-lifecycle.json` | 21 | Partner Certification Lifecycle Management — new certification issuance, automated renewal for strong performers (score ≥70%), manual review escalation for below-threshold partners, expiry monitoring with Slack alerts and email notifications, Google Sheets audit trail. |

## Design Principles

- **Credential placeholders** — Use `YOUR_N8N_CREDENTIAL_ID` style placeholders so you can find-and-replace
- **Webhook-first** — Each workflow has a webhook trigger so your MCP servers or external systems can fire it
- **Slack notifications** — Partner ops events route to relevant channels
- **Error handling** — Every workflow includes error branches where possible

## N8N Credentials You'll Need

- Salesforce / HubSpot (CRM)
- Google Sheets (lightweight partner DB)
- Slack (notifications)
- Email (SMTP credentials from your Gmail app password)
- HTTP Request (for hitting your own MCP servers or APIs)

## Integration Points

- **channel-mgmt MCP** — n8n workflows can call `POST http://localhost:8000/tools/call` with tool names
- **Resonate-IQ** — Trigger outreach sequences when deals hit specific stages
- **Crossbeam** — webhook receiver for new ecosystem overlaps