"""channelctl — unified CLI for the channel platform.

Usage:
  channelctl partner add --id P001 --name "Acme" --tier gold [--region West] [--revenue 120000] ...
  channelctl partner list [--tier gold]
  channelctl health score [--partner P001]        # health + churn risk
  channelctl health portfolio                     # concentration/dependency report
  channelctl incentives rebate --file txns.json
  channelctl incentives claim --partner P001 --kind mdf --amount 4000
  channelctl incentives leaderboard
  channelctl growth refer --sender P001 --customer "BigCo" --value 80000 [--expertise cloud,security] [--region West]
  channelctl growth convert --id REF-... --won
  channelctl growth fee --value 100000 --tier platinum [--type enterprise] [--fast-pay]
  channelctl velocity milestone --partner P001 --name first_deal_won --days 52
  channelctl velocity report --partner P001
  channelctl velocity advance --partner P001      # tier advancement check
  channelctl demo                                 # seed sample data
"""
import argparse
import json
import sys

from . import db
from .modules import health, incentives, growth, velocity, team


def _print(obj):
    print(json.dumps(obj, indent=2, default=str))


def main(argv=None):
    p = argparse.ArgumentParser(prog="channelctl", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    # partner
    sp = sub.add_parser("partner").add_subparsers(dest="sub", required=True)
    a = sp.add_parser("add")
    for f in ["id", "name"]:
        a.add_argument(f"--{f}", required=True)
    a.add_argument("--tier", default="authorized", choices=["authorized", "gold", "platinum"])
    for f, t in [("region", str), ("email", str), ("expertise", str), ("revenue", float),
                 ("deals", int), ("won", int), ("certs", int), ("training", float),
                 ("mdf-allocated", float), ("mdf-used", float), ("logins", int), ("last-deal-days", int)]:
        a.add_argument(f"--{f}", type=t, default=None)
    ls = sp.add_parser("list")
    ls.add_argument("--tier", default=None)

    # health
    hp = sub.add_parser("health").add_subparsers(dest="sub", required=True)
    hs = hp.add_parser("score")
    hs.add_argument("--partner", default=None)
    hp.add_parser("portfolio")

    # incentives
    ip = sub.add_parser("incentives").add_subparsers(dest="sub", required=True)
    ir = ip.add_parser("rebate")
    ir.add_argument("--file", required=True)
    ic = ip.add_parser("claim")
    ic.add_argument("--partner", required=True)
    ic.add_argument("--kind", required=True, choices=["mdf", "spif", "rebate"])
    ic.add_argument("--amount", type=float, required=True)
    ic.add_argument("--program", default="")
    ip.add_parser("leaderboard")

    # growth
    gp = sub.add_parser("growth").add_subparsers(dest="sub", required=True)
    gr = gp.add_parser("refer")
    gr.add_argument("--sender", required=True)
    gr.add_argument("--customer", required=True)
    gr.add_argument("--value", type=float, required=True)
    gr.add_argument("--expertise", default="")
    gr.add_argument("--region", default=None)
    gc = gp.add_parser("convert")
    gc.add_argument("--id", required=True)
    gc.add_argument("--won", action="store_true")
    gf = gp.add_parser("fee")
    gf.add_argument("--value", type=float, required=True)
    gf.add_argument("--tier", required=True)
    gf.add_argument("--type", default="standard")
    gf.add_argument("--fast-pay", action="store_true")
    gp.add_parser("engagement")

    # velocity
    vp = sub.add_parser("velocity").add_subparsers(dest="sub", required=True)
    vm = vp.add_parser("milestone")
    vm.add_argument("--partner", required=True)
    vm.add_argument("--name", required=True)
    vm.add_argument("--days", type=int, required=True)
    vr = vp.add_parser("report")
    vr.add_argument("--partner", required=True)
    va = vp.add_parser("advance")
    va.add_argument("--partner", required=True)


    # team
    tp = sub.add_parser("team").add_subparsers(dest="sub", required=True)
    ta = tp.add_parser("add-cam")
    ta.add_argument("--id", required=True); ta.add_argument("--name", required=True); ta.add_argument("--region", default=None)
    tt = tp.add_parser("touch")
    tt.add_argument("--cam", required=True); tt.add_argument("--partner", required=True)
    tt.add_argument("--kind", default="call"); tt.add_argument("--date", default=None); tt.add_argument("--notes", default="")
    tq = tp.add_parser("score-qbr")
    tq.add_argument("--cam", required=True); tq.add_argument("--partner", required=True); tq.add_argument("--quarter", required=True)
    for dim in team.RUBRIC:
        tq.add_argument(f"--{dim.replace('_','-')}", type=int, required=False)
    tq.add_argument("--deck-file", default=None, help="Path to QBR text; if given, scores via Anthropic API")
    ti = tp.add_parser("action-item")
    ti.add_argument("--cam", required=True); ti.add_argument("--partner", required=True)
    ti.add_argument("--desc", required=True); ti.add_argument("--due", default=None)
    tc = tp.add_parser("close-item"); tc.add_argument("--id", required=True)
    tp.add_parser("report")
    tv = tp.add_parser("coach"); tv.add_argument("--cam", required=True)

    sub.add_parser("demo")

    args = p.parse_args(argv)

    if args.cmd == "partner" and args.sub == "add":
        db.upsert_partner({
            "id": args.id, "name": args.name, "tier": args.tier, "region": args.region,
            "email": args.email,
            "expertise": args.expertise.split(",") if args.expertise else [],
            "annual_revenue": args.revenue or 0, "deals_registered": args.deals or 0,
            "deals_won": args.won or 0, "certifications": args.certs or 0,
            "training_hours": args.training or 0,
            "mdf_allocated": getattr(args, "mdf_allocated") or 0,
            "mdf_used": getattr(args, "mdf_used") or 0,
            "portal_logins_30d": args.logins or 0,
            "days_since_last_deal": getattr(args, "last_deal_days") or 0,
        })
        _print({"added": args.id})
    elif args.cmd == "partner" and args.sub == "list":
        _print(db.list_partners(args.tier))
    elif args.cmd == "health" and args.sub == "score":
        if args.partner:
            partner = db.get_partner(args.partner)
            if not partner:
                sys.exit(f"Unknown partner: {args.partner}")
            _print({"health": health.health_score(partner), "churn_risk": health.churn_risk(partner)})
        else:
            _print(health.run_all())
    elif args.cmd == "health" and args.sub == "portfolio":
        _print(health.portfolio_report())
    elif args.cmd == "incentives" and args.sub == "rebate":
        with open(args.file) as f:
            txns = json.load(f)
        _print(incentives.calculate_rebate(txns))
    elif args.cmd == "incentives" and args.sub == "claim":
        _print(incentives.submit_claim(args.partner, args.kind, args.amount, args.program))
    elif args.cmd == "incentives" and args.sub == "leaderboard":
        _print(incentives.leaderboard())
    elif args.cmd == "growth" and args.sub == "refer":
        _print(growth.submit_referral(args.sender, args.customer, args.value,
                                      args.expertise.split(",") if args.expertise else [], args.region))
    elif args.cmd == "growth" and args.sub == "convert":
        _print(growth.convert_referral(args.id, args.won))
    elif args.cmd == "growth" and args.sub == "fee":
        _print(growth.calculate_fee(args.value, args.tier, args.type, args.fast_pay))
    elif args.cmd == "growth" and args.sub == "engagement":
        _print(growth.engagement_report())
    elif args.cmd == "velocity" and args.sub == "milestone":
        _print(velocity.record_milestone(args.partner, args.name, args.days))
    elif args.cmd == "velocity" and args.sub == "report":
        _print(velocity.partner_velocity(args.partner))
    elif args.cmd == "velocity" and args.sub == "advance":
        _print(velocity.tier_advancement(args.partner))
    elif args.cmd == "team" and args.sub == "add-cam":
        _print(team.add_cam(args.id, args.name, args.region))
    elif args.cmd == "team" and args.sub == "touch":
        _print(team.log_touchpoint(args.cam, args.partner, args.kind, args.date, args.notes))
    elif args.cmd == "team" and args.sub == "score-qbr":
        if args.deck_file:
            with open(args.deck_file) as f:
                _print(team.ai_score_qbr(args.cam, args.partner, args.quarter, f.read()))
        else:
            scores = {d: getattr(args, d) for d in team.RUBRIC}
            if any(v is None for v in scores.values()):
                sys.exit("Provide all rubric flags (--structure ... --followup-items) or --deck-file for AI scoring.")
            _print(team.score_qbr(args.cam, args.partner, args.quarter, scores))
    elif args.cmd == "team" and args.sub == "action-item":
        _print(team.add_action_item(args.cam, args.partner, args.desc, args.due))
    elif args.cmd == "team" and args.sub == "close-item":
        _print(team.close_action_item(args.id))
    elif args.cmd == "team" and args.sub == "report":
        _print(team.team_report())
    elif args.cmd == "team" and args.sub == "coach":
        _print(team.rep_coaching_view(args.cam))
    elif args.cmd == "demo":
        _seed_demo()
        _print({"seeded": True, "partners": [p["id"] for p in db.list_partners()]})


def _seed_demo():
    samples = [
        {"id": "P001", "name": "CloudBridge Solutions", "tier": "platinum", "region": "Northeast",
         "expertise": ["cloud", "security", "data"], "annual_revenue": 480000, "deals_registered": 22,
         "deals_won": 14, "certifications": 3, "training_hours": 28, "mdf_allocated": 20000,
         "mdf_used": 12000, "portal_logins_30d": 18, "days_since_last_deal": 12},
        {"id": "P002", "name": "Summit Integrators", "tier": "gold", "region": "West",
         "expertise": ["networking", "cloud"], "annual_revenue": 95000, "deals_registered": 7,
         "deals_won": 4, "certifications": 1, "training_hours": 12, "mdf_allocated": 8000,
         "mdf_used": 2000, "portal_logins_30d": 6, "days_since_last_deal": 45},
        {"id": "P003", "name": "Gem State Tech", "tier": "authorized", "region": "West",
         "expertise": ["security"], "annual_revenue": 18000, "deals_registered": 1,
         "deals_won": 0, "certifications": 0, "training_hours": 3, "mdf_allocated": 0,
         "mdf_used": 0, "portal_logins_30d": 1, "days_since_last_deal": 160},
    ]
    for s in samples:
        db.upsert_partner(s)


if __name__ == "__main__":
    main()
