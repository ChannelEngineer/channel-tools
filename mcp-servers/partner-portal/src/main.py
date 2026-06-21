"""
Partner Portal MCP Server
Grounded in the Chanimal Channel Kit — partner self-service, locator, MDF, NFR quiz, and portal management.
"""
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import json, random
from datetime import datetime, timedelta
from typing import Any

server = Server("partner-portal")

# ── Knowledge Base ──────────────────────────────────────────────────────────

NFR_QUESTIONS = [
    {
        "id": 1,
        "question": "How long does a registered deal stay valid?",
        "answer": "90 days",
        "hint": "See Deal Reg Policy",
    },
    {
        "id": 2,
        "question": "What are the three classifications for leads?",
        "answer": "A, B, and C",
        "hint": "See Lead policy",
        "accept_any": ["a b c", "a, b, c", "a b and c", "a, b and c"],
    },
    {
        "id": 3,
        "question": "How do you request Market Development Funds (MDF)?",
        "answer": "Use the online form or contact the Channel Manager",
        "hint": "Look under Marketing Tools",
    },
    {
        "id": 4,
        "question": "All leads must be claimed within how many working days?",
        "answer": "2 working days",
        "hint": "See Lead policy",
    },
    {
        "id": 5,
        "question": "How much does the company charge for training?",
        "answer": "Nothing — training is FREE",
        "hint": "See training under Support",
    },
    {
        "id": 6,
        "question": "What is the amount of the extra Jump Start margin?",
        "answer": "10%",
        "hint": "See special promotions",
    },
    {
        "id": 7,
        "question": "How much extra margin do you receive if you register a deal?",
        "answer": "10%",
        "hint": "See Deal Reg Policy",
    },
    {
        "id": 8,
        "question": "What must you do FIRST to get listed in the reseller locator?",
        "answer": "List the company's products on your website",
        "hint": "Partners must display the product on their site before being listed",
    },
    {
        "id": 9,
        "question": "What is Deal Registration?",
        "answer": "A policy of registering a deal to obtain exclusive margin, support, and reduced channel conflict",
        "hint": "See Deal Registration policy",
    },
    {
        "id": 10,
        "question": "What are the three partner program tiers?",
        "answer": "Authorized, Gold, and Platinum",
        "hint": "See Program Level Grid",
        "accept_any": ["authorized gold platinum", "authorized, gold, platinum"],
    },
]

MDF_CATEGORIES = [
    "Joint email campaign",
    "Regional event / tradeshow",
    "Webinar / online event",
    "Direct mail campaign",
    "Digital advertising",
    "Customer event / user group",
    "PR / press release",
    "Case study / testimonial development",
    "Demo center setup",
    "Other (specify)",
]

LOCATOR_REGIONS = [
    "Northeast", "Midwest", "South", "Southwest", "West",
    "Pacific Northwest", "Southeast", "Mid-Atlantic",
]

TIER_PRIORITY = {"platinum": 3, "gold": 2, "authorized": 1}

DEAL_REG_DEFAULTS = {
    "validity_days": 90,
    "mdf_reimbursement_pct": 50,
    "mdf_claim_window_days": 90,
    "response_window_hours": 48,
}


# ── MCP Tools ────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="find_partners",
            description="Search the partner locator by zip code, region, tier, or product expertise. Prioritized by certification level (Platinum listed first).",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Geographic region or zip code to search",
                    },
                    "tier_filter": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["authorized", "gold", "platinum"]},
                        "description": "Filter by partner tier(s)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 20)",
                    },
                    "product_expertise": {
                        "type": "string",
                        "description": "Filter by product expertise area",
                    },
                },
                "required": ["region"],
            },
        ),
        types.Tool(
            name="request_mdf",
            description="Submit a Market Development Funds (MDF) request. Generates the request form and provides policy guidance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "partner_company": {
                        "type": "string",
                        "description": "Partner company name",
                    },
                    "contact_name": {
                        "type": "string",
                        "description": "Requestor name",
                    },
                    "contact_email": {
                        "type": "string",
                        "description": "Requestor email",
                    },
                    "activity_type": {
                        "type": "string",
                        "description": "Type of marketing activity (e.g., 'Joint email campaign', 'Regional event')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the proposed activity, opportunity, and expected results",
                    },
                    "total_cost": {
                        "type": "number",
                        "description": "Total estimated cost of the activity",
                    },
                    "requested_amount": {
                        "type": "number",
                        "description": "Amount of MDF reimbursement requested",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Proposed start date (ISO format)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Proposed end date (ISO format)",
                    },
                },
                "required": ["partner_company", "contact_name", "contact_email", "activity_type", "total_cost"],
            },
        ),
        types.Tool(
            name="nfr_quiz",
            description="Generate and grade the NFR (Not For Resale) quiz. Partners pass to earn free software access. Can generate a new quiz or grade submitted answers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["generate", "grade"],
                        "description": "'generate' to create a new quiz, 'grade' to check submitted answers",
                    },
                    "partner_name": {
                        "type": "string",
                        "description": "Partner name (required for generate)",
                    },
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_id": {"type": "integer"},
                                "answer": {"type": "string"},
                            },
                        },
                        "description": "Array of {question_id, answer} objects (required for grade)",
                    },
                },
                "required": ["action"],
            },
        ),
        types.Tool(
            name="portal_orientation",
            description="Generate a partner orientation checklist and getting-started guide for the partner portal. Covers setup, training, locator listing, and first deal.",
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
                    "company_name": {
                        "type": "string",
                        "description": "Your company name (the vendor)",
                    },
                    "portal_url": {
                        "type": "string",
                        "description": "Partner portal URL",
                    },
                },
                "required": ["partner_name", "partner_tier", "company_name"],
            },
        ),
        types.Tool(
            name="manage_deals",
            description="List, renew, or close partner deal registrations. Track deal pipeline by partner, tier, or status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "renew", "close", "summary"],
                        "description": "Action to perform on deal registrations",
                    },
                    "partner_name": {
                        "type": "string",
                        "description": "Filter by partner (optional)",
                    },
                    "status_filter": {
                        "type": "string",
                        "enum": ["active", "expiring_soon", "expired", "closed_won", "closed_lost"],
                        "description": "Filter by deal status",
                    },
                    "deal_id": {
                        "type": "string",
                        "description": "Deal ID for renew/close actions",
                    },
                },
                "required": ["action"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "find_partners":
        return _handle_find_partners(arguments)
    elif name == "request_mdf":
        return _handle_request_mdf(arguments)
    elif name == "nfr_quiz":
        return _handle_nfr_quiz(arguments)
    elif name == "portal_orientation":
        return _handle_portal_orientation(arguments)
    elif name == "manage_deals":
        return _handle_manage_deals(arguments)
    raise ValueError(f"Unknown tool: {name}")


# ── Tool Implementations ─────────────────────────────────────────────────────

def _handle_find_partners(args: dict) -> list[types.TextContent]:
    region = args["region"]
    tier_filter = args.get("tier_filter", ["authorized", "gold", "platinum"])
    max_results = args.get("max_results", 20)
    expertise = args.get("product_expertise", "")

    # Sort tiers by priority
    sorted_tiers = sorted(tier_filter, key=lambda t: TIER_PRIORITY.get(t, 0), reverse=True)

    output = f"""# Partner Locator Results
*Search: {region}* | Max results: {max_results}

## Results by Tier Priority

"""

    for tier in sorted_tiers:
        tname = tier.capitalize()
        output += f"""### {tname} Partners
*Priority: {TIER_PRIORITY.get(tier, 0)}/3 — listed first in results*

| Partner | Region | Expertise | Certified | Since |
|---|---|---|---|---|
| [Results would display here from your partner database] | | | | |

"""

    output += f"""## How the Locator Works

- Partners are **prioritized by tier level**: Platinum → Gold → Authorized
- Within the same tier, higher certification levels rank first
- Results are sorted by zip code proximity or map-based
- Only partners who have listed products on their website are included

## Requirements to Be Listed

1. List {args.get('company_name', 'the vendor')}'s products on your website
2. Contact the Channel Manager to validate the listing
3. Channel Manager adds your contact info to the public locator

---
*Search generated: {datetime.now().isoformat()}*
"""
    return [types.TextContent(type="text", text=output)]


def _handle_request_mdf(args: dict) -> list[types.TextContent]:
    company = args["partner_company"]
    contact = args["contact_name"]
    email = args["contact_email"]
    activity = args["activity_type"]
    desc = args.get("description", "Not provided")
    total_cost = args["total_cost"]
    requested = args.get("requested_amount", total_cost * 0.5)
    start = args.get("start_date", "TBD")
    end = args.get("end_date", "TBD")

    recommended = total_cost * (DEAL_REG_DEFAULTS["mdf_reimbursement_pct"] / 100)
    max_reimbursable = min(requested, recommended)
    claim_by = (datetime.now() + timedelta(days=DEAL_REG_DEFAULTS["mdf_claim_window_days"])).strftime("%Y-%m-%d")

    output = f"""# MDF Request — Submission Summary

**Status:** PENDING REVIEW

## Request Details

| Field | Value |
|---|---|
| Partner | {company} |
| Contact | {contact} |
| Email | {email} |
| Activity Type | {activity} |
| Total Cost | ${total_cost:,.2f} |
| Requested Amount | ${requested:,.2f} |
| Proposed Dates | {start} → {end} |

## Description
{desc}

## MDF Policy

| Policy | Detail |
|---|---|
| Max Reimbursement | {DEAL_REG_DEFAULTS['mdf_reimbursement_pct']}% of total cost (up to **${recommended:,.2f}**) |
| Recommended Award | **${max_reimbursable:,.2f}** |
| Claim Deadline | Within {DEAL_REG_DEFAULTS['mdf_claim_window_days']} days of activity end ({claim_by}) |
| Alternative | Vendor may contribute materials/manpower instead of cash |

## Next Steps

1. Channel Manager reviews request (typical response: 24-48 hours)
2. If approved: receive MDF agreement with terms
3. Execute activity within proposed dates
4. Submit claim with receipts within {DEAL_REG_DEFAULTS['mdf_claim_window_days']} days of completion
5. Reimbursement processed via accounting

---
*Submitted: {datetime.now().isoformat()}*
"""
    return [types.TextContent(type="text", text=output)]


def _handle_nfr_quiz(args: dict) -> list[types.TextContent]:
    action = args["action"]
    partner = args.get("partner_name", "Partner")

    if action == "generate":
        # Select a subset of questions (8 of 10 as sample)
        selected = random.sample(NFR_QUESTIONS, min(8, len(NFR_QUESTIONS)))
        selected.sort(key=lambda q: q["id"])

        output = f"""# NFR Quiz — {partner}

*Pass the quiz and earn FREE software/access!*

## Instructions

Answer the following questions correctly to gain access to the software.
Most answers are covered within the partner portal. The Channel Manager
will receive your responses and should email you NFR access within 24 hours.

---
"""
        for q in selected:
            output += f"""### Question {q['id']}: {q['question']}
*Hint: {q['hint']}*

Your answer:
_________________________

"""
        output += f"""
---
*Quiz generated: {datetime.now().isoformat()}* — 8 of {len(NFR_QUESTIONS)} questions
*To grade: submit answers via nfr_quiz with action=grade*
"""
        return [types.TextContent(type="text", text=output)]

    elif action == "grade":
        answers = args.get("answers", [])
        if not answers:
            return [types.TextContent(type="text", text="No answers provided. Submit as: [{'question_id': 1, 'answer': '90 days'}, ...]")]

        correct = 0
        total = len(answers)
        results = []

        q_lookup = {q["id"]: q for q in NFR_QUESTIONS}

        for a in answers:
            qid = a.get("question_id")
            ans = a.get("answer", "").strip().lower()
            q = q_lookup.get(qid)
            if not q:
                results.append(f"  Q{qid}: Unknown question ID")
                continue

            expected = q["answer"].lower()
            accept_any = [s.lower() for s in q.get("accept_any", [])]

            # Check against expected answer or accepted alternatives
            is_correct = (
                ans == expected
                or any(ans == alt for alt in accept_any)
                or (len(ans) > 5 and ans in expected)
                or (len(expected) > 5 and expected in ans)
            )
            if is_correct:
                correct += 1
                results.append(f"  ✓ Q{qid}: {q['question'][:60]}... — CORRECT")
            else:
                results.append(f"  ✗ Q{qid}: {q['question'][:60]}... — INCORRECT (expected: {q['answer']})")

        passed = correct >= 7  # 7/8 or 8/10 to pass
        output = f"""# NFR Quiz Results — {partner}

**Score: {correct}/{total}** {'✅ PASSED' if passed else '❌ FAILED'}

{'Congratulations! Your answers will be sent to the Channel Manager. You should receive NFR access within 24 hours.' if passed else f'You need at least 7/10 correct to pass. Review the partner portal and try again.'}

## Detailed Results

{chr(10).join(results)}

"""
        return [types.TextContent(type="text", text=output)]

    return [types.TextContent(type="text", text="Specify action='generate' or action='grade'")]


def _handle_portal_orientation(args: dict) -> list[types.TextContent]:
    partner = args["partner_name"]
    tier = args["partner_tier"]
    company = args["company_name"]
    portal_url = args.get("portal_url", "[portal URL]")

    output = f"""# Partner Portal Orientation — {partner}

**Welcome to the {company} Partner Program!**

## Getting Started Checklist

### Step 1: Portal Access
- [ ] Log in at {portal_url}
- [ ] Review your Personal Data page
- [ ] Verify contact information is current
- [ ] Change your password
- [ ] Review partner program benefits grid (see your {tier.capitalize()} level benefits)

### Step 2: Setup Your Presence
- [ ] Download the {company} PowerPoint presentation
- [ ] Download the Competitive Matrix PDF
- [ ] Download and personalize the Promotional Templates
- [ ] **CRITICAL:** Set up a page on your website that talks about {company}
- [ ] Notify the Channel Manager that your site is ready — they'll add you to the **Reseller Locator**
- [ ] Verify your entry appears correctly in the locator

### Step 3: Training & Product Access
- [ ] Complete the online product training (self-paced, FREE)
- [ ] Watch the demo videos
- [ ] Watch the training videos
- [ ] Take the NFR Quiz for FREE software access
- [ ] Download demo scripts ("Show this, Say this")
- [ ] Review the FAQ (including how to place an order)

### Step 4: First Marketing Activities
- [ ] Send the Product Introduction Email to your existing customers
- [ ] Review MDF options for joint promotions
- [ ] Check current promotions (Jump Start margin, NFR specials)
- [ ] Review the Marketing Plan of Action template (required for Gold/Platinum)

### Step 5: Start Selling
- [ ] Review Deal Registration process
- [ ] Register your first deal for exclusive margin
- [ ] Attend group webinars: bring prospects — we demo, you close
- [ ] Review co-op/MDF tickler system
- [ ] Set up recurring touch points with Channel Manager

## Partner Portal Sections

| Section | What's There |
|---|---|
| Personal Data | Contact info, password, orientation checklist |
| Leads | View and claim assigned leads |
| Deal Registration | Register new deals, view active registrations |
| Marketing Tools | Product descriptions, price list, competitive matrix, white papers, case studies, promotional templates |
| Sales Tools | PowerPoints, demo scripts, videos, market info |
| Support | Training, NFR quiz, FAQ, tech support |
| Partner Locator | Verify your listing, check search results |
| MDF | Request funds, view accrued Co-op |
| Promotions | Current specials, Jump Start, NFR deals |

**Channel Manager contact:** See portal support page for direct contact info.

---
*Orientation generated: {datetime.now().isoformat()}*
"""
    return [types.TextContent(type="text", text=output)]


def _handle_manage_deals(args: dict) -> list[types.TextContent]:
    action = args["action"]
    partner = args.get("partner_name", "")
    status_filter = args.get("status_filter", "")
    deal_id = args.get("deal_id", "")

    now = datetime.now()

    if action == "list":
        output = f"""# Deal Registration Pipeline
{'Filter: Partner = ' + partner if partner else ''}
{'Filter: Status = ' + status_filter if status_filter else ''}

## Active Deals

| Deal ID | Partner | Account | Value | Probability | Close Date | Tier | Days Left |
|---|---|---|---|---|---|---|---|
| [Sample data — integrate with your deal registration database] | | | | | | | |

## Deal Registration Rules

- **Validity:** {DEAL_REG_DEFAULTS['validity_days']} days from registration
- **Renewal:** May be renewed if the deal is still active
- **Approval:** 24-48 hour response from Channel Manager
- **Max deals per partner:** Varies by tier (Gold: 5/quarter, Platinum: 15/quarter)
- **Margin bump:** +10% on registered deals

"""
    elif action == "renew":
        if not deal_id:
            return [types.TextContent(type="text", text="deal_id required for renew action")]
        new_expiry = (now + timedelta(days=DEAL_REG_DEFAULTS["validity_days"])).strftime("%Y-%m-%d")
        output = f"""# Deal Renewal — {deal_id}

**Status:** Renewal Submitted for Approval

- Previous expiry: [TBD]
- **New expiry: {new_expiry}** (extended {DEAL_REG_DEFAULTS['validity_days']} days)
- Must include updated status, close date, and opportunity size

"""
    elif action == "close":
        if not deal_id:
            return [types.TextContent(type="text", text="deal_id required for close action")]
        output = f"""# Deal Close — {deal_id}

**Status:** Pending final reporting

- Mark deal as Won or Lost
- Record final deal size and margin
- If Won: process partner margin payment
- If Lost: capture reason for loss analysis

"""
    elif action == "summary":
        output = f"""# Deal Registration Summary

## Pipeline Overview
| Metric | Value |
|---|---|
| Active Deals | [Count] |
| Total Pipeline Value | [$] |
| Avg Deal Size | [$] |
| Avg Probability | [%] |
| Expiring in 30 Days | [Count] |
| Closed Won (This Quarter) | [Count/Value] |
| Close Rate | [%] |

## By Partner Tier
| Tier | Deals | Pipeline | Avg Size |
|---|---|---|---|
| Platinum | | | |
| Gold | | | |
| Authorized | | | |

"""
    else:
        output = f"Unknown action: {action}"

    output += f"\n*Generated: {now.isoformat()}*"
    return [types.TextContent(type="text", text=output)]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="partner-portal",
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