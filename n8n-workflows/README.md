# ⚡ n8n Workflows — Channel Management Automation

> Importable JSON workflow files ready to drop into your n8n instance at `navitools.net`.

Workflows here automate partner program operations that are better done as **event-driven multi-step processes** than MCP tool calls — human approval chains, Slack notifications, CRM sync, email sequences, etc.

## How to Use

1. Open your n8n instance at https://n8n.navitools.net
2. Workflows → Import from File → Select the `.json` file
3. Update credential IDs and webhook URLs to match your setup
4. Activate

## Workflow Catalog

| Workflow | Nodes | What It Does |
|----------|-------|-------------|
| *(populated by nightly cron)* | | |

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