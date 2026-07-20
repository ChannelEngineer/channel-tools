"""
Channel Management MCP Server
Grounded in production-proven channel program mechanics — tier structures, deal registration,
lead management, MDF policies, and onboarding from hundreds of channel program launches.

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
# Encoded from production channel program mechanics

DISTRIBUTION_MODELS = {
    "referral_affiliate": {
        "name": "Referral / Affiliate",
        "margin_pct": 10,
        "form_referral_margin_pct": 15,
        "description": "Sends links or completes a referral form. No training, no support, no closing. Lightest touch.",
        "closing": False,
        "training": False,
        "support": "None",
        "best_for": "Partners who want a simple commission without any engagement beyond sending referrals.",
    },
    "authorized_var": {
        "name": "Authorized VAR",
        "margin_pct": 20,
        "description": "Closes deals, basic training, no formal quota or certification. Vendor sends leads.",
        "closing": True,
        "training": "Basic",
        "support": "1st line",
        "certification_required": False,
        "best_for": "Entry-level resellers who want to start selling with minimal commitment.",
    },
    "gold_var": {
        "name": "Gold VAR",
        "margin_pct": 30,
        "description": "Closes deals, 1st-level support, certification required, quota required (~$50k). Plan of action required.",
        "closing": True,
        "training": "1st level + certification",
        "support": "1st line + vendor assistance",
        "certification_required": True,
        "quota_required": True,
        "min_quota": 50000,
        "best_for": "Established resellers with proven sales capability.",
    },
    "platinum_var": {
        "name": "Platinum VAR",
        "margin_pct": 40,
        "description": "Closes deals, 1st & 2nd level support/integration, dual certification, higher quota (~$200k).",
        "closing": True,
        "training": "2nd level + dual certification",
        "support": "1st & 2nd line, integration",
        "certification_required": True,
        "quota_required": True,
        "min_quota": 200000,
        "best_for": "Top-tier partners providing full-service solutions including implementation.",
    },
    "white_label": {
        "name": "White Label / OEM",
        "margin_pct": 50,
        "description": "ALL support, ALL training, everything. Heavy quota with performance clause (~$500k). Partner rebrands the product as their own.",
        "closing": True,
        "training": "Full",
        "support": "Full (all levels)",
        "certification_required": True,
        "quota_required": True,
        "min_quota": 500000,
        "best_for": "Large partners who want to fully own the customer relationship and brand the product.",
    },
    "distributor_wholesale": {
        "name": "Distributor (Wholesale)",
        "margin_pct": 5,
        "range": "3-7%",
        "description": "Fulfillment, financing, logistics, returns. Can help recruit (typically charges for campaigns). Limited value for SaaS — no physical inventory.",
        "services": "Fulfillment, financing, logistics, returns, assisted recruitment",
        "best_for": "Hardware vendors needing logistics. Not ideal for SaaS.",
    },
    "vad_country_manager": {
        "name": "VAD — Value Added Distributor",
        "margin_pct": 50,
        "description": "Signs up, trains, and manages everything — including re-doing collateral in another language. Pays their partners normal margins, keeps the difference. Big quotas with performance clauses.",
        "services": "Full: recruitment, training, localization, management",
        "best_for": "Entering international markets where you need a local operator who owns the full channel.",
    },
    "saas_distributor": {
        "name": "SaaS Distributor (SaaSMAX)",
        "margin_pct": 10,
        "description": "Discount consulting, help with partner database, recruiting assistance, marketplace access (customers & resellers).",
        "services": "Consulting, database, recruiting, marketplace",
        "best_for": "SaaS companies needing a partner marketplace and recruiting assistance without building from scratch.",
    },
    "consultant": {
        "name": "Consultant / Bounty",
        "margin_pct": 5,
        "range": "5-10%",
        "description": "Only refers channel partners, not end customers. Bounty (one-time) or percentage (1st year, ongoing, or first-year only). Common: 10% first year, 5% lifetime.",
        "services": "Referral only",
        "best_for": "Industry consultants who can recommend your product or introduce you to resellers.",
    },
    "rep_firm": {
        "name": "Rep Firm / Manufacturers Rep",
        "margin_pct": 5,
        "description": "Sell-in representation. 5% sell-in commission plus approved expenses. Rep firms represent multiple vendors and sell to the channel.",
        "services": "Sell-in representation, relationship management",
        "best_for": "Expanding geographic reach through established rep networks.",
    },
}

SALES_FORECAST_DEFAULTS = {
    "avg_deal_size_annual": 1800,
    "avg_deals_per_reseller_first_year": 6,
    "sales_cycle_months": 1,
    "ramp_up_months": 1,
    "expected_first_sale_month": 2,
    "pct_resellers_active": 0.7,
    "avg_reseller_tenure_years": 5,
}

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
            description="Design a 3-tier partner program (Authorized → Gold → Platinum) with benefits grid, requirements, and margin structure.",
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
            description="Register a partner deal opportunity. Handles the full deal registration lifecycle including margin rules, exclusivity periods, and conflict checks.",
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
            description="Classify a lead as A, B, or C. A = immediate, B = near-term, C = nurture. Includes SLA rules, follow-up windows, and auto-reassignment logic.",
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
            description="Generate a channel policy document. Choose from: lead policy, deal registration, MDF, NFR, partner program overview, or partner onboarding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_type": {
                        "type": "string",
                        "enum": [
                            "program_overview", "lead_policy", "deal_registration",
                            "mdf_policy", "nfr_policy", "onboarding_checklist",
                            "referral_program",
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
            description="Generate a partner onboarding plan. Covers orientation, training, setup, and go-live checklist.",
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
        types.Tool(
            name="design_distribution_model",
            description="Design a distribution channel model from 10 types (Referral, Authorized VAR, Gold VAR, Platinum VAR, White Label, Distributor, VAD, SaaS Distributor, Consultant, Rep Firm). Includes margin ranges, services, and strategic recommendations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Your company name",
                    },
                    "product_type": {
                        "type": "string",
                        "enum": ["saas", "hardware", "services", "software"],
                        "description": "Type of product being sold through the channel",
                    },
                    "include_models": {
                        "type": "array",
                        "items": {"type": "string", "enum": [
                            "referral_affiliate", "authorized_var", "gold_var", "platinum_var",
                            "white_label", "distributor_wholesale", "vad_country_manager",
                            "saas_distributor", "consultant", "rep_firm"
                        ]},
                        "description": "Which distribution models to include (default: referral + authorized + gold + platinum)",
                    },
                    "international": {
                        "type": "boolean",
                        "description": "Is this for an international market? (impacts VAD and distributor recommendations)",
                    },
                    "maturity": {
                        "type": "string",
                        "enum": ["startup", "growing", "established"],
                        "description": "Company maturity — impacts program design recommendations",
                    },
                },
                "required": ["company_name", "product_type"],
            },
        ),
        types.Tool(
            name="calculate_channel_roi",
            description="Calculate channel ROI. Shows reseller lifetime value, recruitment ROI, and promotional budget returns. Uses real spreadsheet logic from channel ROI analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "avg_deal_size_annual": {
                        "type": "number",
                        "description": "Average annual deal size per customer (e.g., $1,200)",
                    },
                    "avg_customer_tenure_years": {
                        "type": "number",
                        "description": "Average years a customer remains (SaaS: ~3 years)",
                    },
                    "avg_deals_per_reseller_per_year": {
                        "type": "number",
                        "description": "Average number of deals per reseller per year",
                    },
                    "avg_reseller_tenure_years": {
                        "type": "number",
                        "description": "Average years a reseller remains active",
                    },
                    "recruitment_budget": {
                        "type": "number",
                        "description": "Total budget for recruitment activities ($)",
                    },
                    "expected_resellers_recruited": {
                        "type": "integer",
                        "description": "How many resellers you expect to recruit with this budget",
                    },
                },
                "required": ["avg_deal_size_annual", "avg_customer_tenure_years", "avg_deals_per_reseller_per_year"],
            },
        ),
        types.Tool(
            name="forecast_channel_sales",
            description="Generate a 12-month channel sales forecast. Includes monthly revenue projections, ramp-up timelines, and cash flow expectations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "monthly_recruiting_target": {
                        "type": "integer",
                        "description": "Number of resellers to recruit per month (default: 10)",
                    },
                    "avg_deal_size": {
                        "type": "number",
                        "description": "Average annual deal size (default: $1,800)",
                    },
                    "avg_deals_per_reseller_first_year": {
                        "type": "integer",
                        "description": "Avg deals per reseller in first year (default: 6)",
                    },
                    "sales_cycle_months": {
                        "type": "integer",
                        "description": "Sales cycle length in months (default: 1)",
                    },
                    "ramp_up_months": {
                        "type": "integer",
                        "description": "Months to ramp up a new reseller (default: 1)",
                    },
                    "pct_active": {
                        "type": "number",
                        "description": "Percentage of recruited resellers who become active (default: 0.7)",
                    },
                    "months_to_project": {
                        "type": "integer",
                        "description": "Number of months to forecast (default: 12)",
                    },
                },
                "required": [],
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
    elif name == "design_distribution_model":
        return _handle_distribution_model(arguments)
    elif name == "calculate_channel_roi":
        return _handle_channel_roi(arguments)
    elif name == "forecast_channel_sales":
        return _handle_sales_forecast(arguments)
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
*Generated from production channel program framework*

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
        "referral_program": f"""# {company} Referral / Affiliate Program

## Overview
A low-touch referral program for partners who want to earn commissions by referring
business without the commitment of a full reseller relationship.

## Margins

| Referral Type | Commission |
|---|---|
| Affiliate Link | 10% of subscription payments |
| Form-Based Referral | 15% of first-year subscription |

## 90-Day Jump Start Promotion
New affiliates receive an additional 10% margin on all referrals within the first
90 days — up to 20% total commission.

## How It Works
1. Each affiliate receives a unique affiliate ID/link
2. Share the link or submit referrals via the partner portal
3. Commission is tracked via the affiliate link or referral form
4. Payouts are processed monthly on collected revenue

## Affiliate Approval Email Template

Subject: {company} Affiliate Approval — please respond ASAP

Thank you for joining the {company} Partner Program as an affiliate!

Your affiliate ID is: https://partners.{company.lower().replace(' ','')}.com/ref=[ID]

When you have a referral, submit it via the portal referral form.
Make sure to keep your affiliate ID so we can properly credit you.

## Getting Started
1. Create a free trial account to get familiar with the product
2. Access marketing materials, product descriptions, and demo scripts in the portal
3. Schedule a 30-minute orientation with the Channel Manager
4. Start sharing your affiliate link

**Contact:**
{cm_name}, Channel Manager
{cm_email}
{phone}
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
|- Max open leads: {DEAL_REG_DEFAULTS['max_open_leads']}
"""
    return [types.TextContent(type="text", text=output)]


def _handle_distribution_model(args: dict) -> list[types.TextContent]:
    company = args["company_name"]
    product_type = args["product_type"]
    include = args.get("include_models", ["referral_affiliate", "authorized_var", "gold_var", "platinum_var"])
    international = args.get("international", False)
    maturity = args.get("maturity", "growing")

    output = f"""# Distribution Channel Model — {company}

*Product type: {product_type.upper()}* | *Maturity: {maturity}*
{'*International: Yes*' if international else ''}
*Generated from distribution models (2026)*

## Selected Models

"""

    for key in include:
        m = DISTRIBUTION_MODELS.get(key)
        if not m:
            continue
        margin = m.get("range", f"{m['margin_pct']}%")
        output += f"""### {m['name']}
**Margin:** {margin} | **Closes deals:** {'Yes' if m.get('closing') else 'No'}
**Training:** {m.get('training', 'None')} | **Support:** {m.get('support', 'None')}

{m['description']}

**Best for:** {m['best_for']}

"""

    output += """## Strategic Recommendations

"""
    if product_type == "saas":
        output += """- **SaaS margin structure:** Typical margins range 10% (referral) to 50% (white label). Industry leaders pay 20-40% for resellers, 30% for affiliates.
- **Distributors add limited value** for SaaS (no physical inventory). Consider SaaSMAX-style at 10%.
- **Recurring revenue model:** Pay margins on subscription payments (recurring). Best practice: monthly on collected revenue.

"""
    elif product_type == "hardware":
        output += """- **Distributors add value** for hardware (fulfillment, logistics, returns). Expect 3-7%.
- **VADs recommended** for international — handle localization, training, on-ground management.
- **Volume-based tiering**: higher margins for higher volumes.

"""
    if maturity == "startup":
        output += """- **Startup:** Start direct + referral/affiliate. Keep entry simple — no certification fees.
- Don't create barriers to join. "If a NEW program, can't do what branded products get away with."
- Recruit 10-20 partners to stress-test your program before scaling.

"""
    elif maturity == "growing":
        output += """- **Growing:** Add Authorized VAR tier with basic training. Expand to Gold + certification.
- 90-day Jump Start (+10%) to incentivize early engagement.
- Introduce Deal Registration once you have 20+ active partners.

"""
    elif maturity == "established":
        output += """- **Established:** Full tier structure including Platinum and White Label/OEM.
- Consider VAD for international expansion.
- Rep firms for geographic coverage gaps.
- Performance clauses and quarterly Plan of Action for top tiers.

"""
    if international:
        output += """- **International:** VAD at ~50% margin handles localization, training, partner management.
- SaaS Distributor for marketplace reach. Consultant/bounty for targeted entry.

"""
    output += f"\n*Generated: {datetime.now().isoformat()}*\n"
    return [types.TextContent(type="text", text=output)]


def _handle_channel_roi(args: dict) -> list[types.TextContent]:
    deal_size = args["avg_deal_size_annual"]
    tenure = args["avg_customer_tenure_years"]
    deals_per_year = args["avg_deals_per_reseller_per_year"]
    reseller_tenure = args.get("avg_reseller_tenure_years", SALES_FORECAST_DEFAULTS["avg_reseller_tenure_years"])
    budget = args.get("recruitment_budget", 0)
    recruited = args.get("expected_resellers_recruited", 0)

    revenue_per_customer = deal_size * tenure
    revenue_per_reseller_year = deal_size * deals_per_year
    ltv_per_reseller = revenue_per_reseller_year * reseller_tenure

    roi_multiple = 0
    if budget > 0 and recruited > 0:
        total_return = recruited * ltv_per_reseller
        roi_multiple = round(total_return / budget, 1)

    output = f"""# Channel ROI Calculator

*Based on channel ROI analysis*

## Reseller Value

| Metric | Value |
|---|---|
| Avg Annual Deal Size | ${deal_size:,.2f} |
| Avg Customer Tenure | {tenure} years |
| Revenue Per Customer | ${revenue_per_customer:,.2f} |
| Deals / Reseller / Year | {deals_per_year} |
| Revenue / Reseller / Year | ${revenue_per_reseller_year:,.2f} |
| Avg Reseller Tenure | {reseller_tenure} years |
| **Lifetime Value / Reseller** | **${ltv_per_reseller:,.2f}** |
"""

    if budget > 0 and recruited > 0:
        total = recruited * ltv_per_reseller
        output += f"""
## Recruitment ROI

| Metric | Value |
|---|---|
| Budget | ${budget:,.2f} |
| Resellers Recruited | {recruited} |
| Lifetime Revenue | ${total:,.2f} |
| **ROI Multiple** | **{roi_multiple}x** |

> "The absolute HIGHEST ROI of anything a company can do with their promotional budget."

### Promotional Scenarios:
| Campaign | Budget | Resellers | Revenue | ROI |
|---|---|---|---|---|
| Direct Mail (2,000 pcs) | $8,000 | 20 | $6M | 750x |
| Roadshow (10 cities) | $25,000 | 125 | $37.5M | 1,500x |
| Mag Ads (4) | $24,000 | 10 | $3M | 125x |
| Card Decks (4) | $10,000 | 4 | $1.2M | 120x |
| **Combined** | **$67,000** | **159** | **$47.7M** | **712x** |
"""
    output += f"\n*Generated: {datetime.now().isoformat()}*\n"
    return [types.TextContent(type="text", text=output)]


def _handle_sales_forecast(args: dict) -> list[types.TextContent]:
    monthly_recruits = args.get("monthly_recruiting_target", 10)
    deal_size = args.get("avg_deal_size", SALES_FORECAST_DEFAULTS["avg_deal_size_annual"])
    deals_first = args.get("avg_deals_per_reseller_first_year", SALES_FORECAST_DEFAULTS["avg_deals_per_reseller_first_year"])
    sales_cycle = args.get("sales_cycle_months", SALES_FORECAST_DEFAULTS["sales_cycle_months"])
    ramp_up = args.get("ramp_up_months", SALES_FORECAST_DEFAULTS["ramp_up_months"])
    pct_active = args.get("pct_active", SALES_FORECAST_DEFAULTS["pct_resellers_active"])
    months = args.get("months_to_project", 12)

    first_sale_month = ramp_up + sales_cycle + 1
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    revenue_per_sale = deal_size / deals_first

    rows = []
    cumulative_active = 0

    for m in range(1, months + 1):
        active_this_month = int(monthly_recruits * pct_active)
        cumulative_active += active_this_month

        if m <= first_sale_month:
            monthly_revenue = 0
        else:
            selling = sum(int(monthly_recruits * pct_active) for _ in range(m - first_sale_month))
            monthly_revenue = selling * revenue_per_sale

        label = month_names[(m - 1) % 12]
        if m > 12:
            label += f" Yr{((m-1)//12)+1}"
        rows.append((label, monthly_recruits, cumulative_active, round(monthly_revenue, 2)))

    total_rev = sum(r[3] for r in rows)

    output = f"""# Channel Sales Forecast

*Based on reseller recruiting model*

## Assumptions

| Parameter | Value |
|---|---|
| Monthly Target | {monthly_recruits} |
| Avg Deal Size | ${deal_size:,.0f} |
| Deals/Reseller/Year | {deals_first} |
| Sales Cycle | {sales_cycle} mo |
| Ramp-Up | {ramp_up} mo |
| Active % | {pct_active*100:.0f}% |

## Monthly Projection

| Month | Recruited | Active Cumul. | Revenue |
|---|---|---|---|
"""
    for label, rec, act, rev in rows:
        rev_str = f"${rev:,.2f}" if rev > 0 else "$0"
        output += f"| {label} | {rec} | {act} | {rev_str} |\n"

    output += f"""
## Summary
**Total recruited:** {monthly_recruits * months} | **Avg active:** {cumulative_active // max(months, 1)}
**Total Revenue:** ${total_rev:,.2f}

> "Complete the variables and it forecasts the revenue. Account for ramp-up, sales cycle, and when partners come on board."
"""
    output += f"\n*Generated: {datetime.now().isoformat()}*\n"
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