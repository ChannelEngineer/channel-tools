"""Channel Platform web dashboard.

Single-file FastAPI app: JSON API over the consolidated modules plus a
server-delivered single-page console. No build step; runs anywhere Python runs.

    uvicorn channel_platform.web:app --host 0.0.0.0 --port 8090
"""
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import db
from .modules import health, incentives, growth, velocity, team

app = FastAPI(title="Channel Platform")


# ── API ──────────────────────────────────────────────────────────────────────

@app.get("/api/overview")
def api_overview():
    portfolio = health.portfolio_report()
    scores = health.run_all()
    claims = db.query("SELECT * FROM incentive_claims ORDER BY submitted_at DESC LIMIT 25")
    return {"portfolio": portfolio, "scores": scores, "recent_claims": claims}


@app.get("/api/partners")
def api_partners():
    out = []
    for p in db.list_partners():
        h = health.health_score(p)
        c = health.churn_risk(p)
        adv = velocity.tier_advancement(p["id"])
        out.append({**p, "health": h["score"], "health_level": h["level"],
                    "churn": c["score"], "churn_level": c["level"],
                    "next_tier": adv.get("next_tier"), "tier_eligible": adv.get("eligible")})
    return out


@app.get("/api/partners/{pid}")
def api_partner(pid: str):
    p = db.get_partner(pid)
    if not p:
        raise HTTPException(404, "Unknown partner")
    return {"partner": p, "health": health.health_score(p), "churn": health.churn_risk(p),
            "velocity": velocity.partner_velocity(pid), "advancement": velocity.tier_advancement(pid)}


@app.get("/api/team")
def api_team():
    return team.team_report()


@app.get("/api/team/{cam_id}")
def api_coach(cam_id: str):
    try:
        return team.rep_coaching_view(cam_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/referrals")
def api_referrals():
    return db.query("SELECT * FROM referrals ORDER BY submitted_at DESC LIMIT 50")


@app.get("/api/claims")
def api_claims():
    return db.query("SELECT * FROM incentive_claims ORDER BY submitted_at DESC LIMIT 100")


class ClaimIn(BaseModel):
    partner_id: str
    kind: str
    amount: float
    program: str = ""


@app.post("/api/claims")
def api_submit_claim(c: ClaimIn):
    try:
        return incentives.submit_claim(c.partner_id, c.kind, c.amount, c.program)
    except ValueError as e:
        raise HTTPException(400, str(e))


class ReferralIn(BaseModel):
    sender_id: str
    customer: str
    deal_value: float
    expertise: list[str] = []
    region: str | None = None


@app.post("/api/referrals")
def api_submit_referral(r: ReferralIn):
    return growth.submit_referral(r.sender_id, r.customer, r.deal_value, r.expertise, r.region)


@app.post("/api/claims/{claim_id}/{decision}")
def api_decide_claim(claim_id: str, decision: str):
    if decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be approved|rejected")
    rows = db.query("SELECT * FROM incentive_claims WHERE id=?", (claim_id,))
    if not rows:
        raise HTTPException(404, "Unknown claim")
    with db.connect() as c:
        c.execute("UPDATE incentive_claims SET status=?, resolved_at=datetime('now') WHERE id=?",
                  (decision, claim_id))
    return {"id": claim_id, "status": decision}


@app.get("/api/leaderboard")
def api_leaderboard():
    return incentives.leaderboard()


# ── UI ───────────────────────────────────────────────────────────────────────

PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Channel Console</title>
<style>
:root{
  --ink:#0d1017; --panel:#151a23; --panel2:#1b2230; --line:#242d3d;
  --text:#dde5ee; --dim:#7d8a9c;
  --steel:#5b9bd5;           /* actions */
  --platinum:#c9d3de; --gold:#d4a843; --authorized:#8a97a8;  /* tier metals */
  --green:#57b98a; --yellow:#d9b64a; --red:#d96757;
  font-size:15px;
}
*{box-sizing:border-box;margin:0}
body{background:var(--ink);color:var(--text);
  font:400 1rem/1.5 "Segoe UI",system-ui,sans-serif;min-height:100vh}
.mono{font-family:ui-monospace,"Cascadia Code",Consolas,monospace}
header{display:flex;align-items:baseline;gap:1.2rem;padding:1.1rem 1.6rem;border-bottom:1px solid var(--line)}
header h1{font-size:1.05rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase}
header h1 span{color:var(--steel)}
nav{display:flex;gap:.25rem;margin-left:auto;flex-wrap:wrap}
nav button{background:none;border:1px solid transparent;color:var(--dim);padding:.35rem .8rem;
  cursor:pointer;font:inherit;font-size:.85rem;letter-spacing:.05em;text-transform:uppercase;border-radius:4px}
nav button:hover{color:var(--text)}
nav button.on{color:var(--text);border-color:var(--line);background:var(--panel)}
nav button:focus-visible{outline:2px solid var(--steel);outline-offset:2px}
main{padding:1.4rem 1.6rem;max-width:1200px;margin:0 auto}
.grid{display:grid;gap:1rem}
@media(min-width:820px){.grid.cols3{grid-template-columns:repeat(3,1fr)}.grid.cols2{grid-template-columns:1fr 1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:1rem 1.1rem}
.card h2{font-size:.72rem;font-weight:600;color:var(--dim);letter-spacing:.14em;text-transform:uppercase;margin-bottom:.7rem}
.big{font-size:1.9rem;font-weight:300}
.big small{font-size:.8rem;color:var(--dim);margin-left:.4rem}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th{color:var(--dim);font-weight:500;text-align:left;padding:.35rem .6rem .45rem .6rem;
  font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;border-bottom:1px solid var(--line)}
td{padding:.5rem .6rem;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
tr.click{cursor:pointer}tr.click:hover td{background:var(--panel2)}
.tier{display:inline-block;padding:.1rem .5rem;border-radius:3px;font-size:.7rem;
  letter-spacing:.08em;text-transform:uppercase;border:1px solid}
.tier.platinum{color:var(--platinum);border-color:var(--platinum)}
.tier.gold{color:var(--gold);border-color:var(--gold)}
.tier.authorized{color:var(--authorized);border-color:var(--authorized)}
.ribbon{height:6px;border-radius:3px;background:var(--line);overflow:hidden;min-width:90px}
.ribbon i{display:block;height:100%}
.lv-green{background:var(--green)}.lv-yellow{background:var(--yellow)}.lv-red{background:var(--red)}
.lv-minimal,.lv-low{background:var(--green)}.lv-moderate{background:var(--yellow)}
.lv-high,.lv-critical{background:var(--red)}
.pill{display:inline-block;padding:.08rem .5rem;border-radius:10px;font-size:.72rem}
.pill.green{background:rgba(87,185,138,.15);color:var(--green)}
.pill.yellow{background:rgba(217,182,74,.15);color:var(--yellow)}
.pill.red{background:rgba(217,103,87,.15);color:var(--red)}
.pill.dim{background:var(--panel2);color:var(--dim)}
.flag{color:var(--red);font-size:.8rem;display:block}
button.act{background:var(--panel2);border:1px solid var(--line);color:var(--steel);
  padding:.25rem .7rem;border-radius:4px;cursor:pointer;font:inherit;font-size:.78rem}
button.act:hover{border-color:var(--steel)}
form.row{display:flex;gap:.6rem;flex-wrap:wrap;align-items:end;margin-bottom:1rem}
form.row label{display:flex;flex-direction:column;gap:.2rem;font-size:.72rem;color:var(--dim);
  letter-spacing:.08em;text-transform:uppercase}
input,select{background:var(--ink);border:1px solid var(--line);color:var(--text);
  padding:.4rem .6rem;border-radius:4px;font:inherit;font-size:.85rem}
input:focus,select:focus{outline:2px solid var(--steel);outline-offset:1px}
.empty{color:var(--dim);padding:1.2rem 0;text-align:center;font-size:.86rem}
#detail{position:fixed;inset:0;background:rgba(9,12,18,.75);display:none;align-items:start;
  justify-content:center;padding:4rem 1rem;overflow:auto}
#detail.open{display:flex}
#detail .card{max-width:640px;width:100%}
@media(prefers-reduced-motion:no-preference){.card{animation:up .18s ease-out}@keyframes up{from{opacity:0;transform:translateY(4px)}to{opacity:1}}}
</style></head><body>
<header>
  <h1>Channel <span>Console</span></h1>
  <nav id="nav"></nav>
</header>
<main id="main"><div class="empty">Loading…</div></main>
<div id="detail" onclick="if(event.target.id==='detail')this.classList.remove('open')"></div>
<script>
const TABS=["Overview","Partners","Team","Referrals","Claims"];
let tab="Overview";
const $=s=>document.querySelector(s);
const fmt$=n=>n==null?"—":"$"+Number(n).toLocaleString();
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const api=(p,opt)=>fetch("/api/"+p,opt).then(r=>{if(!r.ok)throw r;return r.json()});
const ribbon=(v,lv)=>`<div class="ribbon" title="${v}"><i class="lv-${lv}" style="width:${Math.min(v,100)}%"></i></div>`;
const tierB=t=>`<span class="tier ${t}">${t}</span>`;

function renderNav(){
  $("#nav").innerHTML=TABS.map(t=>`<button class="${t===tab?'on':''}" onclick="go('${t}')">${t}</button>`).join("");
}
function go(t){tab=t;renderNav();VIEWS[t]()}

const VIEWS={
async Overview(){
  const d=await api("overview");
  const p=d.portfolio;
  const worst=[...d.scores].sort((a,b)=>b.churn_risk.score-a.churn_risk.score).slice(0,5);
  $("#main").innerHTML=`
  <div class="grid cols3">
    <div class="card"><h2>Partners</h2><div class="big">${p.partner_count}</div></div>
    <div class="card"><h2>Portfolio revenue</h2><div class="big mono">${fmt$(p.total_revenue)}</div></div>
    <div class="card"><h2>Top-3 concentration</h2><div class="big">${p.top3_concentration_pct}%<small class="pill ${p.concentration_risk==='high'?'red':p.concentration_risk==='moderate'?'yellow':'green'}">${p.concentration_risk}</small></div></div>
  </div>
  <div class="grid cols2" style="margin-top:1rem">
    <div class="card"><h2>Highest churn risk</h2><table><tr><th>Partner</th><th>Risk</th><th>Action</th></tr>
    ${worst.map(s=>`<tr><td>${esc(s.churn_risk.partner_id)}</td>
      <td>${ribbon(s.churn_risk.score,s.churn_risk.level)}</td>
      <td style="color:var(--dim);font-size:.8rem">${esc(s.churn_risk.action)}</td></tr>`).join("")}</table></div>
    <div class="card"><h2>Recent claims</h2>${d.recent_claims.length?`<table><tr><th>ID</th><th>Kind</th><th>Amount</th><th>Status</th></tr>
    ${d.recent_claims.slice(0,6).map(c=>`<tr><td class="mono">${esc(c.id)}</td><td>${esc(c.kind)}</td>
      <td class="mono">${fmt$(c.amount)}</td><td><span class="pill ${c.status==='approved'?'green':c.status==='rejected'?'red':'yellow'}">${esc(c.status)}</span></td></tr>`).join("")}</table>`:`<div class="empty">No claims yet</div>`}</div>
  </div>`;
},
async Partners(){
  const rows=await api("partners");
  $("#main").innerHTML=`<div class="card"><h2>Partner book — health &amp; churn</h2>
  <table><tr><th>Partner</th><th>Tier</th><th>Revenue</th><th>Health</th><th>Churn risk</th><th>Advance</th></tr>
  ${rows.map(p=>`<tr class="click" onclick="partnerDetail('${esc(p.id)}')">
    <td>${esc(p.name)}<div style="color:var(--dim);font-size:.75rem" class="mono">${esc(p.id)} · ${esc(p.region||"")}</div></td>
    <td>${tierB(p.tier)}</td><td class="mono">${fmt$(p.annual_revenue)}</td>
    <td>${ribbon(p.health,p.health_level)}</td><td>${ribbon(p.churn,p.churn_level)}</td>
    <td>${p.next_tier?(p.tier_eligible?`<span class="pill green">→ ${p.next_tier}</span>`:`<span class="pill dim">gaps</span>`):`<span class="pill dim">top tier</span>`}</td>
  </tr>`).join("")}</table></div>`;
},
async Team(){
  const d=await api("team");
  const b=d.team_baseline;
  $("#main").innerHTML=`
  <div class="grid cols3">
    <div class="card"><h2>Median touch cadence</h2><div class="big">${b.avg_days_between_touches??"—"}<small>days</small></div></div>
    <div class="card"><h2>Median QBR score</h2><div class="big">${b.avg_qbr_score??"—"}<small>/100</small></div></div>
    <div class="card"><h2>Median follow-through</h2><div class="big">${b.followthrough_pct??"—"}<small>%</small></div></div>
  </div>
  <div class="card" style="margin-top:1rem"><h2>Reps vs baseline</h2>
  ${d.reps.length?`<table><tr><th>Rep</th><th>Pattern</th><th>Cadence</th><th>QBR</th><th>Follow-through</th><th>Coaching flags</th></tr>
  ${d.reps.map(r=>`<tr><td>${esc(r.name)}</td>
    <td><span class="pill ${r.pattern==='disciplined'?'green':r.pattern==='reactive'?'red':'yellow'}">${r.pattern}</span></td>
    <td class="mono">${r.avg_days_between_touches??"—"}d</td>
    <td class="mono">${r.avg_qbr_score??"—"}</td>
    <td class="mono">${r.followthrough_pct??"—"}%</td>
    <td>${r.coaching_flags.length?r.coaching_flags.map(f=>`<span class="flag">${esc(f)}</span>`).join(""):'<span class="pill green">clear</span>'}</td>
  </tr>`).join("")}</table>`:`<div class="empty">No CAMs yet — add with: channelctl team add-cam</div>`}</div>`;
},
async Referrals(){
  const rows=await api("referrals");
  const partners=await api("partners");
  $("#main").innerHTML=`<div class="card"><h2>Submit referral</h2>
  <form class="row" onsubmit="return submitRef(event)">
    <label>Sender<select id="rf-sender">${partners.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("")}</select></label>
    <label>Customer<input id="rf-cust" required></label>
    <label>Deal value<input id="rf-val" type="number" min="0" required></label>
    <label>Expertise (csv)<input id="rf-exp" placeholder="cloud,security"></label>
    <label>Region<input id="rf-reg"></label>
    <button class="act" type="submit">Submit referral</button>
  </form></div>
  <div class="card" style="margin-top:1rem"><h2>Referral pipeline</h2>
  ${rows.length?`<table><tr><th>ID</th><th>Sender → Receiver</th><th>Customer</th><th>Value</th><th>Status</th><th>Net fee</th></tr>
  ${rows.map(r=>`<tr><td class="mono">${esc(r.id)}</td>
    <td class="mono">${esc(r.sender_partner_id)} → ${esc(r.receiver_partner_id||"unmatched")}</td>
    <td>${esc(r.customer)}</td><td class="mono">${fmt$(r.deal_value)}</td>
    <td><span class="pill ${r.status==='won'?'green':r.status==='lost'?'red':'yellow'}">${esc(r.status)}</span></td>
    <td class="mono">${fmt$(r.fee_net)}</td></tr>`).join("")}</table>`:`<div class="empty">No referrals yet</div>`}</div>`;
},
async Claims(){
  const rows=await api("claims");
  const partners=await api("partners");
  $("#main").innerHTML=`<div class="card"><h2>Submit claim</h2>
  <form class="row" onsubmit="return submitClaim(event)">
    <label>Partner<select id="cl-p">${partners.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("")}</select></label>
    <label>Kind<select id="cl-k"><option>mdf</option><option>spif</option><option>rebate</option></select></label>
    <label>Amount<input id="cl-a" type="number" min="0" required></label>
    <button class="act" type="submit">Submit claim</button>
  </form></div>
  <div class="card" style="margin-top:1rem"><h2>Claims queue</h2>
  ${rows.length?`<table><tr><th>ID</th><th>Partner</th><th>Kind</th><th>Amount</th><th>Status</th><th></th></tr>
  ${rows.map(c=>`<tr><td class="mono">${esc(c.id)}</td><td class="mono">${esc(c.partner_id)}</td><td>${esc(c.kind)}</td>
    <td class="mono">${fmt$(c.amount)}</td>
    <td><span class="pill ${c.status==='approved'?'green':c.status==='rejected'?'red':'yellow'}">${esc(c.status)}</span></td>
    <td>${c.status==='pending'?`<button class="act" onclick="decide('${esc(c.id)}','approved')">Approve</button>
      <button class="act" style="color:var(--red)" onclick="decide('${esc(c.id)}','rejected')">Reject</button>`:""}</td>
  </tr>`).join("")}</table>`:`<div class="empty">No claims yet</div>`}</div>`;
}
};

async function partnerDetail(id){
  const d=await api("partners/"+id);
  const p=d.partner, adv=d.advancement;
  $("#detail").innerHTML=`<div class="card">
    <h2>${esc(p.name)} ${tierB(p.tier)}</h2>
    <table><tr><th>Health</th><th>Churn</th><th>Velocity</th></tr>
    <tr><td>${ribbon(d.health.score,d.health.level)} <span class="mono">${d.health.score}</span></td>
    <td>${ribbon(d.churn.score,d.churn.level)} <span class="mono">${d.churn.score}</span></td>
    <td class="mono">${d.velocity.avg_velocity??"no data"} <span class="pill dim">${esc(d.velocity.overall_status)}</span></td></tr></table>
    <h2 style="margin-top:1rem">Advance to ${esc(adv.next_tier||"—")}</h2>
    ${adv.next_tier?`<table><tr><th>Requirement</th><th>Actual</th><th>Required</th><th></th></tr>
    ${Object.entries(adv.checks).map(([k,v])=>`<tr><td>${esc(k)}</td><td class="mono">${v.actual}</td>
      <td class="mono">${v.required}</td><td>${v.met?'<span class="pill green">met</span>':'<span class="pill red">gap</span>'}</td></tr>`).join("")}</table>`
    :`<div class="empty">Already at top tier</div>`}
    <div style="margin-top:1rem;text-align:right"><button class="act" onclick="$('#detail').classList.remove('open')">Close</button></div>
  </div>`;
  $("#detail").classList.add("open");
}
async function submitRef(e){e.preventDefault();
  await api("referrals",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    sender_id:$("#rf-sender").value,customer:$("#rf-cust").value,deal_value:+$("#rf-val").value,
    expertise:$("#rf-exp").value?$("#rf-exp").value.split(","):[],region:$("#rf-reg").value||null})});
  VIEWS.Referrals();return false}
async function submitClaim(e){e.preventDefault();
  await api("claims",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    partner_id:$("#cl-p").value,kind:$("#cl-k").value,amount:+$("#cl-a").value})});
  VIEWS.Claims();return false}
async function decide(id,decision){await api(`claims/${id}/${decision}`,{method:"POST"});VIEWS.Claims()}

renderNav();VIEWS.Overview();
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
