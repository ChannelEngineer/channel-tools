# ⚡ n8n Workflows — Channel Management Automation

> Importable JSON workflow files ready to drop into your n8n instance at `YOUR_N8N_HOST`.

Workflows here automate partner program operations that are better done as **event-driven multi-step processes** than MCP tool calls — human approval chains, Slack notifications, CRM sync, email sequences, etc.

## How to Use

1. Open your n8n instance at https://YOUR_N8N_HOST
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
||||||| `2026-07-04-partner-program-compliance.json` | 23 | Partner Program Compliance Monitoring System — tier-specific compliance scoring (Platinum/Gold/Authorized), 6-dimension score (revenue, certs, training, POA, deals, MDF), 3-way routing (Compliant ✅ / At Risk ⚠️ / Non-Compliant 🚨), Slack alerts, email notifications with remediation plan, channel director escalation, Google Sheets audit logging |
|| `2026-07-06-partner-poa-lifecycle.json` | 35 | Partner Plan of Action (POA) Lifecycle Management — 4-action webhook (submit/review/score/check_overdue), POA completeness validation, CM review with 3-way routing (approved/revision/rejected), quarterly POA scoring (5-dimension weighted: revenue 35%, deals 25%, MDF 10%, training 15%, initiatives 15%), 3-tier score thresholds (PASS ≥70 / In Progress ≥40 / FAIL <40), PIP auto-generation for failures, channel director escalation, overdue POA reminders with critical/warning/reminder severity, Slack notifications at every stage, email notifications for partners and CMs |
|| `2026-07-08-partner-qbr-automation.json` | 25 | Partner Quarterly Business Review (QBR) Automation — 3-action webhook (generate_qbr/review_qbr/complete_qbr), tier-based scorecards (Full for Gold/Platinum, Simplified for Authorized), 6-dimension QBR scoring (revenue 30pts, deals 20pts, MDF 15pts, training 15pts, engagement 10pts, referrals 10pts), 3-way routing (Strong ≥80 / Needs Discussion ≥50 / Requires Attention <50), Slack notifications to CMs, email scheduling requests to partners, CM approval workflow (approve_schedule/flag_issues), post-QBR action item capture, Google Sheets audit logging, channel director escalation for low scores |
||| `2026-07-10-partner-promotions-spif.json` | 43 | Partner Promotions & SPIF (Sales Performance Incentive Fund) Automation — 5-action webhook (create_campaign, register_promotion_deal, submit_claim, check_budget, list_active_campaigns), auto-approve claims ≤$500 with manager escalation for larger claims, budget burn rate tracking with Slack warnings at 80% utilization, Slack notifications to CMs, email confirmations to partners, Google Sheets audit trail for campaigns, deal registrations, and claims |
||||| `2026-07-12-partner-deal-intelligence-discern.json` | 23 | **DISCERN** — Partner Deal Intelligence, Scoring & Confidence-Enabled Routing Network. Multi-factor predictive deal scoring (7 dimensions: tier 25%, win rate 20%, expertise 15%, velocity 10%, competition 10%, engagement 10%, deal size 10%) with 3-way confidence routing (High ≥75 → auto-approve, Medium 50-74 → standard review with coaching, Low <50 → CM escalation with risk factors). Includes pipeline health check action for weighted pipeline analysis, coverage ratio, and confidence breakdown. Slack notifications + email at every confidence level with context-appropriate messaging. |
|||| `2026-07-13-partner-social-selling-bridge.json` | 23 | **BRIDGE** n8n companion — Partner social selling alerts and re-engagement workflow. Auto-detect inactive sharers (7+ days), send positive reinforcement for active sharing, weekly engagement leaderboard to Slack, and re-engagement email sequences. |
|||| `2026-07-14-partner-velocity-chronos.json` | 24 | **CHRONOS** — Channel Partner Time-to-Value & Onboarding Velocity Tracker. Records partner milestone achievements, calculates velocity scores against tier-specific benchmarks (Platinum/Gold/Authorized), routes by performance (ahead/on-track/at-risk/critical) with Slack alerts, email coaching notes, and channel director escalation for critical cases. Includes weekly summary aggregation with status distribution and top-performer/worst-performer identification. |
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