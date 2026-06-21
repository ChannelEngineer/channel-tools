"""
Channel Management MCP Server
Grounded in the Chanimal Channel Kit — a production-proven channel program framework
built from 200+ channel program launches.

Tools: design_partner_program, register_deal, manage_leads, generate_policy, onboard_partner
"""
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import json
from datetime import datetime, timedelta
from typing import Any

server = Server("channel-mgmt")

# ── Knowledge Base ──────────────────────────────────────────────────────────
# Encoded from the Chanimal Channel Kit docs

PARTNER_TIERS = {
    "authorized": {
        "name": "Authorized",
        "index": 0,
        "leads_ratio": "Limited (1:1 ratio or lower)",
        "deal_registration": False,
        "volume_discount": False,
        "partner_locator": "Low priority",
        "nfr_access": True,
        "joint_promotions": "Limited",
        "certification": False,
        "pre_release_access": False,
        "priority_support": False,
        "plan_of_action_required": False,
        "quarterly_targets": False,
        "credit_application": True,
        "deals_per_quarter": None,
        "revenue_share_pct": 15,
        "deal_reg_margin_bump": 0,
    },
    "gold": {
        "name": "Gold",
        "index": 1,
        "leads_ratio": "Medium (2:1 ratio)",
        "deal_registration": True,
        "volume_discount": True,
        "partner_locator": "Medium priority",
        "nfr_access": True,
        "joint_promotions": True,
        "certification": "Medium requirement",
        "pre_release_access": True,
        "priority_support": True,
        "plan_of_action_required": True,
        "quarterly_targets": True,
        "credit_application": True,
        "deals_per_quarter": 5,
        "revenue_share_pct": 25,
        "deal_reg_margin_bump": 10,
    },
    "platinum": {
        "name": "Platinum",
        "index": 2,
        "leads_ratio": "High (3:1 ratio)",
        "deal_registration": True,
        "volume_discount": True,
        "partner_locator": "High priority",
        "nfr_access": True,
        "joint_promotions": True,
        "certification": "High requirement",
        "pre_release_access": True,
        "priority_support": True,
        "plan_of_action_required": True,
        "quarterly_targets": True,
        "credit_application": True,
        "deals_per_quarter": 15,
        "revenue_share_pct": 35,
        "deal_reg_margin_bump": 10,
    }
}

LEAD_CLASSIFICATIONS = {
    "a": {
        "name": "A Lead",
        "description": "Immediate contact requested — decision coming soon",
        "response_window_hours": 48,  # 2 working days
        "follow_up_days": 2,
    },
    "b": {
        "name": "B Lead",
        "description": "Specified decision timeline, not immediate",
        "response_window_hours": 48,  # claim within 2 days
        "follow_up_days": 5,
    },
    "c": {
        "name": "C Lead / Contact",
        "description": "Not yet qualified — nurture until re-qualified",
        "response_window_hours": None,
        "follow_up_days": None,
        "action": "Send marketing materials (direct mail, brochures, updates). Re-qualify when they respond.",
    }
}

DEAL_REG_DEFAULTS = {
    "validity_days": 90,
    "max_open_leads": 10,
    "approval_window_hours": 48,
    "jump_start_days": 90,
    "jump_start_margin_bump_pct": 10,
    "mdf_reimbursement_pct": 50,
    "mdf_claim_window_days": 90,
}

# ── Helper: Build tier grid ──────────────────────────────────────────────────

def _build_tier_grid(company_name: str, tiers: list[str] | None = None) -> dict:
    selected = tiers or ["authorized", "gold", "platinum"]
    grid = {}
    for key in selected:
        tier = PARTNER_TIERS.get(key)
        if not tier:
            continue
        grid[key] = dict(tier)
        grid[key].pop("deals_per_quarter", None)
        grid[key].pop("revenue_share_pct", None)
        grid[key].pop("deal_reg_margin_bump", None)
    return {
        "company": company_name,
        "generated": datetime.now().isoformat(),
        "tiers": grid,
    }

# ── MCP Tools ────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="design_partner_program",
            description="Design a 3-tier partner program (Authorized → Gold → Platinum) using the Chanimal framework. Generates benefits grid, requirements, and margin structure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Your company name",
                    },
                    "include_tiers": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["authorized", "gold", "platinum"]},
                        "description": "Which tiers to include (default: all three)",
                    },
                    "custom_margins": {
                        "type": "object",
                        "description": "Override default revenue share percentages per tier",
                        "additionalProperties": {"type": "number"},
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any specific adjustments or notes about the program",
                    },
                },
                "required": ["company_name"],
            },
        ),
        types.Tool(
            name="register_deal",
            description="Register a partner deal opportunity. Handles the full deal registration lifecycle including margin rules, exclusivity periods, and conflict checks per Chanimal best practices.",
            inputSchema={
                "type": "object",
                "properties": {
                    "partner_company": {
                        "type": "string",
                        "description": "Partner company registering the deal",
                    },
                    "partner_tier": {
                        "type": "string",
                        "enum": ["authorized", "gold", "platinum"],
                        "description": "Partner's program tier (Authorized considered on one-off basis)",
                    },
                    "opportunity_company": {
                        "type": "string",
                        "description": "Name of the target account/company",
                    },
                    "opportunity_size": {
                        "type": "number",
                        "description": "Estimated deal value in dollars",
                    },
                    "probability_pct": {
                        "type": "integer",
                        "description": "Probability as percentage (10, 25, 50, 75, or 100)",
                    },
                    "stage": {
                        "type": "string",
                        "enum": [
                            "just_found_out", "not_contacted_yet", "talked_with_contact",
                            "gave_demo", "submitted_bid", "final_negotiations"
                        ],
                        "description": "Current stage of the deal",
                    },
                    "days_working": {
                        "type": "integer",
                        "description": "Number of days the partner has been working this deal",
                    },
                    "anticipated_close_date": {
                        "type": "string",
                        "description": "Expected close date (ISO format e.g. 2026-08-15)",
                    },
                    "products": {
                        "type": "string",
                        "description": "Products being bid",
                    },
                    "is_jump_start": {
                        "type": "boolean",
                        "description": "Is this within the partner's first 90 days? (earns extra Jump Start margin)",
                    },
                },
                "required": ["partner_company", "partner_tier", "opportunity_company", "opportunity_size"],
            },
        ),
        types.Tool(
            name="classify_lead",
            description="Classify a lead as A, B, or C per Chanimal lead management framework. A = immediate, B = near-term, C = nurture. Includes SLA rules, follow-up windows, and auto-reassignment logic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "classification": {
                        "type": "string",
                        "enum": ["a", "b", "c"],
                        "description": "Lead classification: A (immediate contact), B (near-term decision), C (not yet qualified)",
                    },
                    "company": {
                        "type": "string",
                        "description": "Lead company name",
                    },
                    "contact_name": {
                        "type": "string",
                        "description": "Primary contact name",
                    },
                    "region": {
                        "type": "string",
                        "description": "Geographic region for partner assignment",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional context about the lead",
                    },
                },
                "required": ["classification", "company"],
            },
        ),
        types.Tool(
            name="generate_policy",
            description="Generate a channel policy document from Chanimal templates. Choose from: lead policy, deal registration, MDF, NFR, partner program overview, or partner onboarding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_type": {
                        "type": "string",
                        "enum": [
                            "program_overview", "lead_policy", "deal_registration",
                            "mdf_policy", "nfr_policy", "onboarding_checklist",
                        ],
                        "description": "Type of policy document to generate",
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Your company name for personalization",
                    },
                    "channel_manager_name": {
                        "type": "string",
                        "description": "Channel manager contact name",
                    },
                    "channel_manager_email": {
                        "type": "string",
                        "description": "Partner program email address",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Channel manager phone number",
                    },
                },
                "required": ["policy_type", "company_name"],
            },
        ),
        types.Tool(
            name="onboard_partner",
            description="Generate a partner onboarding plan based on the Chanimal framework. Covers orientation, training, setup, and go-live checklist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "partner_name": {
                        "type": "string",
                        "description": "Partner company name",
                    },
                    "partner_tier": {
                        "type": "string",
                        "enum": ["authorized", "gold", "platinum"],
                        "description": "Partner's assigned tier",
                    },
                    "channel_manager": {
                        "type": "string",
                        "description": "Assigned channel manager name",
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Your company name (the vendor)",
                    },
                },
                "required": ["partner_name", "partner_tier", "company_name"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "design_partner_program":
        return _handle_design_program(arguments)
    elif name == "register_deal":
        return _handle_register_deal(arguments)
    elif name == "classify_lead":
        return _handle_classify_lead(arguments)
    elif name == "generate_policy":
        return _handle_generate_policy(arguments)
    elif name == "onboard_partner":
        return _handle_onboard_partner(arguments)
    raise ValueError(f"Unknown tool: {name}")

# ── Tool Implementations ─────────────────────────────────────────────────────

def _handle_design_program(args: dict) -> list[types.TextContent]:
    company = args["company_name"]
    tiers = args.get("include_tiers", ["authorized", "gold", "platinum"])
    custom_margins = args.get("custom_margins", {})
    notes = args.get("notes", "")

    grid = _build_tier_grid(company, tiers)

    # Apply custom margins
    for tier_key, margin in custom_margins.items():
        if tier_key in grid["tiers"]:
            grid["tiers"][tier_key]["revenue_share_pct"] = margin

    # Generate the benefits grid document
    output = f"""# {company} Partner Program
*Generated from the Chanimal Channel Kit framework*

## Program Overview
A 3-tier partner program designed to reward partner commitment and performance.
Partners start at the tier they qualify for and can advance based on certification,
sales volume, and plan of action execution.

## Partner Levels

"""

    for key, tier in grid["tiers"].items():
        output += f"""### {tier['name']} Level

**Requirements:**
- Register as a VAR on the partner portal
- Complete partner application
- Qualify as a partner (face-to-face selling, 1st-line post-sale support, outbound sales)
{f'- Submit quarterly Business Plan of Action' if tier['plan_of_action_required'] else '- No plan of action required'}
{f'- Quarterly sales targets required' if tier['quarterly_targets'] else '- No quarterly targets'}

**Benefits:**
| Feature | |
|---|---|
| Lead Access | {tier['leads_ratio']} |
| Deal Registration | {'✓ Available (10% extra margin)' if tier['deal_registration'] else '✗ Not available'} |
| Volume Discount | {'✓ Back-end rebates' if tier['volume_discount'] else '✗ Not available'} |
| Partner Locator | {tier['partner_locator']} |
| NFR Access | {'✓' if tier['nfr_access'] else '✗'} |
| Joint Promotions | {tier['joint_promotions']} |
| Pre-Release Access | {'✓' if tier['pre_release_access'] else '✗'} |
| Priority Tech Support | {'✓' if tier['priority_support'] else 'Standard'} |
| Certification | {tier['certification']} |
| Revenue Share | {tier.get('revenue_share_pct', 'N/A')}% standard margin |
| Deal Reg Margin Bump | +{tier.get('deal_reg_margin_bump', 0)}% on registered deals |

"""

    output += f"\n*Generated: {grid['generated']}*\n"
    if notes:
        output += f"\n**Notes:** {notes}\n"

    return [types.TextContent(type="text", text=output)]


def _handle_register_deal(args: dict) -> list[types.TextContent]:
    partner = args["partner_company"]
    tier = args["partner_tier"]
    opp = args["opportunity_company"]
    size = args["opportunity_size"]
    prob = args.get("probability_pct", 50)
    stage = args.get("stage", "just_found_out")
    days_working = args.get("days_working", 0)
    close_date = args.get("anticipated_close_date", "TBD")
    products = args.get("products", "Not specified")
    is_jump_start = args.get("is_jump_start", False)

    tier_info = PARTNER_TIERS.get(tier, PARTNER_TIERS["authorized"])

    # Validation
    issues = []
    if tier == "authorized":
        issues.append("⚠️ Authorized partners are considered on a one-off basis — approval not guaranteed.")
    if prob not in [10, 25, 50, 75, 100]:
        issues.append("⚠️ Probability must be one of: 10%, 25%, 50%, 75%, or 100%")

    margin_bump = tier_info["deal_reg_margin_bump"]
    total_margin = tier_info.get("revenue_share_pct", 20) + margin_bump
    if is_jump_start:
        total_margin += DEAL_REG_DEFAULTS["jump_start_margin_bump_pct"]

    valid_until = (datetime.now() + timedelta(days=DEAL_REG_DEFAULTS["validity_days"])).strftime("%Y-%m-%d")

    stage_labels = {
        "just_found_out": "Just Found Out",
        "not_contacted_yet": "Have Not Made Contact Yet",
        "talked_with_contact": "Have Talked with Primary Contact",
        "gave_demo": "Gave Product Demo",
        "submitted_bid": "Submitted Bid",
        "final_negotiations": "Final Negotiations",
    }

    output = f"""# Deal Registration — Registration Summary

**Status:** {'CONDITIONAL' if issues else 'ACCEPTED'} — Pending review by Channel Manager

## Deal Details
| Field | Value |
|---|---|
| Partner | {partner} |
| Tier | {tier_info['name']} |
| Target Account | {opp} |
| Est. Deal Size | ${size:,} |
| Probability | {prob}% |
| Stage | {stage_labels.get(stage, stage)} |
| Days Working | {days_working} |
| Products | {products} |
| Expected Close | {close_date} |
| Jump Start | {'✓ Yes (+10% extra margin)' if is_jump_start else 'No'} |

## Margin Structure
| Component | Rate |
|---|---|
| Standard Tier Margin | {tier_info.get('revenue_share_pct', 'N/A')}% |
| Deal Registration Bump | +{margin_bump}% |
{f'| Jump Start Bump | +{DEAL_REG_DEFAULTS["jump_start_margin_bump_pct"]}% |' if is_jump_start else ''}
| **Effective Margin** | **{total_margin}%** |

## Rules of Engagement
- **Validity:** This registration expires on {valid_until} (90 days)
- **Renewal:** May be renewed if the deal is still active
- **Exclusivity:** {company_name} agrees not to compete on this account
- **Loyalty:** Both parties agree to win or lose the deal together
- **Conflict:** No competitive products may be introduced by the partner
- **Pricing:** All pricing to end customer handled by the partner

"""
    if issues:
        output += "\n## Issues\n" + "\n".join(f"- {i}" for i in issues)

    output += f"\n*Generated: {datetime.now().isoformat()}*\n"
    return [types.TextContent(type="text", text=output)]


def _handle_classify_lead(args: dict) -> list[types.TextContent]:
    classification = args["classification"]
    company = args["company"]
    contact = args.get("contact_name", "Not specified")
    region = args.get("region", "Unspecified")
    notes = args.get("notes", "")

    cls = LEAD_CLASSIFICATIONS[classification]

    output = f"""# Lead Classification — {cls['name']}

| Field | Value |
|---|---|
| Company | {company} |
| Contact | {contact} |
| Region | {region} |
| Classification | {cls['name']} |
| Description | {cls['description']} |

## SLA Requirements
"""
    if cls["response_window_hours"]:
        claimed_by = (datetime.now() + timedelta(hours=cls["response_window_hours"])).strftime("%Y-%m-%d %H:%M")
        follow_up_by = (datetime.now() + timedelta(days=cls["follow_up_days"])).strftime("%Y-%m-%d")
        # Simplified datetime since we already have it above
        output += f"""- **Claim by:** Within {cls['response_window_hours']} working hours (by approx. {claimed_by})
- **Contact by:** Within {cls['follow_up_days']} working days
- **Max open leads:** {DEAL_REG_DEFAULTS['max_open_leads']} at any time
- **Auto-reassign:** If not claimed or followed up within SLA, lead is auto-reassigned to another partner

## Partner Assignment
"""
    else:
        output += f"""- **Action:** {cls['action']}
- **Status:** Nurture until re-qualified as A or B

"""
    if notes:
        output += f"\n**Notes:** {notes}\n"

    return [types.TextContent(type="text", text=output)]


def _handle_generate_policy(args: dict) -> list[types.TextContent]:
    ptype = args["policy_type"]
    company = args["company_name"]
    cm_name = args.get("channel_manager_name", "[Channel Manager Name]")
    cm_email = args.get("channel_manager_email", "partners@company.com")
    phone = args.get("phone", "(xxx)xxx-xxxx")

    templates = {
        "program_overview": f"""# {company} Partner Program — Overview

Thank you for your interest in becoming a member of the {company} Partner Program.

**Benefits:**
- Highly competitive margins with unique recurring revenue model and quick payout
- Pre-qualified sales leads (not just names) from events, SEO, and more
- Inclusion in the reseller locator map — so buyers can find you
- FREE NFR Access — take the quiz and it's yours
- Deal Registration — Quick, easy approval, exclusive support, +10% extra margin
- Jump Start Margin — Extra margin for every registered deal in the first 90 days
- Start at Gold level for good margins immediately
- FREE product and market training — no cost or barriers to entry
- MDF — Pre-allocated budget with easy-to-apply form
- Partner Conference — Invitation to the annual event
- Online Webinars to help you sell
- Sales tools — competitive matrix, PowerPoints, market info, and more
- Special spiffs, promotions, and recognition

This is an ACTIVE partner program. You're sure to love it!

**Contact:**
{cm_name}, Channel Manager
{cm_email}
{phone}
""",

        "lead_policy": f"""# {company} Lead Policy

## Lead Classification
All leads are classified as A, B, or C.

**A Leads** — Decision coming soon, immediate contact requested.
- Must be contacted within 2 working days
- Claim within 48 hours

**B Leads** — Specified decision time, not immediate.
- Must be contacted within 5 working days
- Claim within 48 hours

**C Leads / Contacts** — Not yet qualified.
- Sent marketing materials until they re-engage
- Re-qualified as A or B when they respond

## Lead Follow-Up Requirements
- All leads must be claimed within 2 working days
- Maximum of {DEAL_REG_DEFAULTS['max_open_leads']} open leads at any time
- Leads not claimed or followed up within SLA are auto-reassigned
- Chronic SLA violations may result in lead system disablement

## Lead Dissemination
Leads are prioritized by partner region, program level, and certification level.
Higher-tier, certified partners receive priority lead access.
""",

        "deal_registration": f"""# {company} Deal Registration Policy

## Benefits
- Exclusive margin advantage over non-registered competitors
- +10% extra margin on registered deals
- Assistance from {company} sales to help close the deal
- Early pre-sales and engineering support
- Increased chance to win the sale

## Eligibility
- Gold and Platinum Partners (Authorized considered on a one-off basis)
- Must be registered in the online partner portal with current information

## How It Works
1. Register an account opportunity (company name, deal size, expected close date)
2. Submit for approval — response within 24-48 hours
3. If approved: exclusive pricing discount, sales support, engineering assistance
4. If rejected: reason noted, partner works the deal normally

## Rules of Engagement
- First-come, first-serve basis
- One registration per opportunity
- Valid for 90 days (renewable)
- Deal Loyalty: we win or lose together
- Partner agrees not to introduce competitive products into registered deals
- {company} internal sales will not compete on pricing for registered deals
""",

        "mdf_policy": f"""# {company} Market Development Funds (MDF) Policy

## Allocation
MDF funds are allocated on a discretionary basis to pre-approved marketing activities.
Proposed activities should tie into the partner's marketing plans to generate revenue.

## Reimbursement
- {company} may reimburse up to {DEAL_REG_DEFAULTS['mdf_reimbursement_pct']}% of total cost
- Or elect to contribute materials and manpower
- Claims must be submitted within {DEAL_REG_DEFAULTS['mdf_claim_window_days']} days of activity end date

## How to Request
Complete the MDF request form with:
- Company and contact information
- Description of the opportunity and proposed activity
- Expected contribution amount
- Timeline

**Contact:**
{cm_name}, Channel Manager
{cm_email}
{phone}
""",

        "nfr_policy": f"""# {company} Not For Resale (NFR) Program

## Overview
NFR copies/access are available at a significant discount to Partners and their employees,
allowing you to benefit from {company} products at work and home.

## Pricing
- Standard cost: $10-$25 per NFR copy (see current promotions for specials)
- Maximums vary by organization size

## NFR Quiz
Pass the 10-question quiz and get a FREE NFR copy/access!
The quiz covers material from the partner portal (lead policy, deal registration,
MDF process, locator requirements, etc.). Contact the Channel Manager for access.

**Contact:**
{cm_name}, Channel Manager
{cm_email}
{phone}
""",

        "onboarding_checklist": f"""# {company} Partner Onboarding Checklist

## Phase 1: Application & Approval
- [ ] Complete partner application form
- [ ] Submit credit application (if direct purchase relationship)
- [ ] Verify distributor account (for indirect purchasing)
- [ ] Application reviewed and approved by Channel Manager

## Phase 2: Portal Setup
- [ ] Receive portal login credentials
- [ ] Complete orientation webinar or review orientation materials
- [ ] Set up personalized portal with company information
- [ ] Review partner program grid and understand tier benefits

## Phase 3: Training & Certification
- [ ] Complete product training (self-paced, FREE)
- [ ] Watch demo videos
- [ ] Take NFR Quiz for FREE software access
- [ ] Download and review competitive matrix
- [ ] Review demo scripts

## Phase 4: Go-to-Market
- [ ] List {company} products on your website
- [ ] Notify Channel Manager to verify website listing
- [ ] Get added to the public Reseller Locator
- [ ] Download and personalize promotional templates
- [ ] Send product introduction email to existing customers
- [ ] Download sales presentations

## Phase 5: Active Selling
- [ ] Attend group webinars (bring prospects, we demo, you close)
- [ ] Register your first deal for exclusive margin
- [ ] Submit quarterly Plan of Action (Gold/Platinum)
- [ ] Review MDF budget and plan joint promotions
- [ ] Explore co-op funds and tickler system

**Channel Manager:** {cm_name}
**Contact:** {cm_email} | {phone}
""",
    }

    content = templates.get(ptype, f"Policy type '{ptype}' not found.")
    return [types.TextContent(type="text", text=content)]


def _handle_onboard_partner(args: dict) -> list[types.TextContent]:
    partner = args["partner_name"]
    tier = args["partner_tier"]
    cm = args.get("channel_manager", "Channel Manager")
    company = args["company_name"]

    tier_info = PARTNER_TIERS.get(tier, PARTNER_TIERS["authorized"])
    tier_name = tier_info["name"]

    output = f"""# Partner Onboarding Plan — {partner}

**Tier:** {tier_name}
**Channel Manager:** {cm}
**Vendor:** {company}
**Generated:** {datetime.now().isoformat()}

## Week 1: Welcome & Setup
- Send welcome email with program overview and benefits grid
- Schedule orientation call/webinar
- Provide portal login credentials
- Walk through Reseller Application process
- Complete and sign Reseller Agreement
- Set up distributor relationship (if applicable)

## Week 2: Training & Enablement
- Assign product training (self-paced, FREE)
- Schedule first product demo (tag-team: we demo, you close)
- Share competitive matrix and market backgrounder
- Provide demo scripts and sales presentations
- Review NFR quiz process for free software access
- Set up NFR access for hands-on product experience

## Week 3: Go-to-Market Prep
{f'- Develop quarterly Business Plan of Action (required for {tier_name})' if tier_info['plan_of_action_required'] else '- Optional: develop Business Plan of Action'}
- Help partner list {company} products on their website
- Verify website listing → add to Reseller Locator
- Share promotional templates and product introduction emails
- Review Deal Registration process and benefits
- Explain MDF request process
- Discuss Jump Start margin program (first 90 days)

## Week 4: Active & Selling
- First pipeline review meeting
- Review co-op/MDF opportunities
- Connect with assigned sales engineer
- Enroll in certification program
- Register first deal opportunity
- Schedule regular touch points (weekly webinars, monthly reviews)

## 90-Day Check-In
- Review Jump Start margin utilization
- Pipeline health assessment
- Plan of Action results review
- Identify advancement opportunities for next tier
- Gather feedback on portal, tools, and support

## Notes
- Partners start at {tier_name} with immediate benefits
- Deal Registration available{' (gold/platinum only)' if not tier_info['deal_registration'] else ''}
- MDF available for joint promotional activities
- Partner locator priority: {tier_info['partner_locator']}
- Max open leads: {DEAL_REG_DEFAULTS['max_open_leads']}
"""
    return [types.TextContent(type="text", text=output)]


company_name = "ChannelEngineer"  # default for deal reg

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="channel-mgmt",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())