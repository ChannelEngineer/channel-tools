"""Team module — CAM performance consistency diagnostics.

Implements the VP-of-channel diagnostic playbook:
1. Cadence variance    — days between partner touches per CAM vs team median
2. QBR prep quality    — rubric-based scoring of review decks (manual or AI-assisted)
3. Follow-through      — action items closed before the next review
4. Baseline comparison — each rep's numbers alongside the team, specifics not vibes

Data model additions: cams, touchpoints, qbr_reviews, action_items.
"""
import json
import os
import statistics
import uuid
from datetime import datetime
from .. import db

TEAM_SCHEMA = """
CREATE TABLE IF NOT EXISTS cams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT,
    hired_at TEXT
);
CREATE TABLE IF NOT EXISTS touchpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cam_id TEXT REFERENCES cams(id),
    partner_id TEXT REFERENCES partners(id),
    kind TEXT DEFAULT 'call',            -- call|email|meeting|qbr
    occurred_at TEXT NOT NULL,
    notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS qbr_reviews (
    id TEXT PRIMARY KEY,
    cam_id TEXT REFERENCES cams(id),
    partner_id TEXT REFERENCES partners(id),
    quarter TEXT,
    -- rubric: 0-5 each
    structure INTEGER, data_backed INTEGER, clear_asks INTEGER,
    prior_commitments INTEGER, followup_items INTEGER,
    total REAL,
    scored_by TEXT DEFAULT 'manual',      -- manual|ai
    reviewed_at TEXT,
    detail TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS action_items (
    id TEXT PRIMARY KEY,
    cam_id TEXT REFERENCES cams(id),
    partner_id TEXT REFERENCES partners(id),
    description TEXT,
    created_at TEXT,
    due_at TEXT,
    closed_at TEXT
);
"""

RUBRIC = ["structure", "data_backed", "clear_asks", "prior_commitments", "followup_items"]


def _ensure_schema():
    with db.connect() as c:
        c.executescript(TEAM_SCHEMA)


def _now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def add_cam(cam_id: str, name: str, region: str = None):
    _ensure_schema()
    db.insert("cams", {"id": cam_id, "name": name, "region": region, "hired_at": _now()})
    return {"added": cam_id}


def log_touchpoint(cam_id: str, partner_id: str, kind: str = "call",
                   occurred_at: str = None, notes: str = ""):
    _ensure_schema()
    with db.connect() as c:
        c.execute("INSERT INTO touchpoints (cam_id, partner_id, kind, occurred_at, notes) VALUES (?,?,?,?,?)",
                  (cam_id, partner_id, kind, occurred_at or _now(), notes))
    return {"logged": True}


def score_qbr(cam_id: str, partner_id: str, quarter: str, scores: dict,
              scored_by: str = "manual", detail: dict = None) -> dict:
    """Record rubric scores (0-5 each) for a QBR deck/review."""
    _ensure_schema()
    missing = [k for k in RUBRIC if k not in scores]
    if missing:
        raise ValueError(f"Missing rubric dimensions: {missing}")
    total = round(sum(scores[k] for k in RUBRIC) / (5 * len(RUBRIC)) * 100, 1)
    row = {"id": f"QBR-{uuid.uuid4().hex[:8].upper()}", "cam_id": cam_id,
           "partner_id": partner_id, "quarter": quarter,
           **{k: scores[k] for k in RUBRIC}, "total": total,
           "scored_by": scored_by, "reviewed_at": _now(),
           "detail": json.dumps(detail or {})}
    db.insert("qbr_reviews", row)
    return row


def ai_score_qbr(cam_id: str, partner_id: str, quarter: str, deck_text: str) -> dict:
    """AI rubric-scoring of QBR content via the Anthropic API.

    Requires ANTHROPIC_API_KEY. Returns the same record shape as score_qbr,
    with scored_by='ai' and rationale in detail.
    """
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Set ANTHROPIC_API_KEY to use AI scoring, or use score_qbr manually.")
    prompt = (
        "Score this QBR deck content on 5 dimensions, 0-5 integers each: "
        "structure (logical flow, agenda, sections), data_backed (metrics and evidence, not anecdotes), "
        "clear_asks (explicit requests/next steps for the partner), "
        "prior_commitments (references and closes out last quarter's action items), "
        "followup_items (concrete owned action items with owners/dates). "
        "Respond ONLY with JSON: {\"structure\":n,\"data_backed\":n,\"clear_asks\":n,"
        "\"prior_commitments\":n,\"followup_items\":n,\"rationale\":\"one sentence per dimension\"}\n\n"
        f"QBR CONTENT:\n{deck_text[:12000]}"
    )
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": "claude-sonnet-4-6", "max_tokens": 500,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Content-Type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    parsed = json.loads(text.replace("```json", "").replace("```", "").strip())
    scores = {k: int(parsed[k]) for k in RUBRIC}
    return score_qbr(cam_id, partner_id, quarter, scores, scored_by="ai",
                     detail={"rationale": parsed.get("rationale", "")})


def add_action_item(cam_id: str, partner_id: str, description: str, due_at: str = None) -> dict:
    _ensure_schema()
    row = {"id": f"AI-{uuid.uuid4().hex[:8].upper()}", "cam_id": cam_id,
           "partner_id": partner_id, "description": description,
           "created_at": _now(), "due_at": due_at, "closed_at": None}
    db.insert("action_items", row)
    return row


def close_action_item(item_id: str) -> dict:
    _ensure_schema()
    with db.connect() as c:
        c.execute("UPDATE action_items SET closed_at=? WHERE id=?", (_now(), item_id))
    return {"closed": item_id}


def _cadence_stats(cam_id: str) -> dict:
    """Average days between touches per partner, then averaged across a CAM's book."""
    rows = db.query("SELECT partner_id, occurred_at FROM touchpoints WHERE cam_id=? ORDER BY partner_id, occurred_at", (cam_id,))
    by_partner = {}
    for r in rows:
        by_partner.setdefault(r["partner_id"], []).append(r["occurred_at"])
    gaps = []
    for dates in by_partner.values():
        ds = sorted(datetime.fromisoformat(d.rstrip("Z")) for d in dates)
        gaps += [(b - a).days for a, b in zip(ds, ds[1:])]
    return {
        "touch_count": len(rows),
        "partners_touched": len(by_partner),
        "avg_days_between_touches": round(statistics.mean(gaps), 1) if gaps else None,
        "max_gap_days": max(gaps) if gaps else None,
    }


def team_report() -> dict:
    """The baseline comparison: every CAM's cadence, QBR quality, and follow-through vs team median."""
    _ensure_schema()
    cams = db.query("SELECT * FROM cams ORDER BY name")
    reps = []
    for cam in cams:
        cadence = _cadence_stats(cam["id"])
        qbrs = db.query("SELECT total FROM qbr_reviews WHERE cam_id=?", (cam["id"],))
        items = db.query("SELECT closed_at, due_at FROM action_items WHERE cam_id=?", (cam["id"],))
        closed = sum(1 for i in items if i["closed_at"])
        reps.append({
            "cam_id": cam["id"], "name": cam["name"],
            **cadence,
            "qbr_count": len(qbrs),
            "avg_qbr_score": round(statistics.mean(q["total"] for q in qbrs), 1) if qbrs else None,
            "action_items": len(items),
            "followthrough_pct": round(closed / len(items) * 100, 1) if items else None,
        })
    def med(key):
        vals = [r[key] for r in reps if r[key] is not None]
        return round(statistics.median(vals), 1) if vals else None
    baseline = {k: med(k) for k in ["avg_days_between_touches", "avg_qbr_score", "followthrough_pct"]}
    # Flag reps vs baseline — specifics, not vibes
    for r in reps:
        flags = []
        b = baseline
        if r["avg_days_between_touches"] and b["avg_days_between_touches"] and \
           r["avg_days_between_touches"] > b["avg_days_between_touches"] * 1.5:
            flags.append(f"touch cadence {r['avg_days_between_touches']}d vs team median {b['avg_days_between_touches']}d")
        if r["avg_qbr_score"] is not None and b["avg_qbr_score"] and r["avg_qbr_score"] < b["avg_qbr_score"] - 15:
            flags.append(f"QBR quality {r['avg_qbr_score']} vs median {b['avg_qbr_score']}")
        if r["followthrough_pct"] is not None and b["followthrough_pct"] and \
           r["followthrough_pct"] < b["followthrough_pct"] - 20:
            flags.append(f"follow-through {r['followthrough_pct']}% vs median {b['followthrough_pct']}%")
        r["coaching_flags"] = flags
        r["pattern"] = "disciplined" if not flags else "reactive" if len(flags) >= 2 else "mixed"
    return {"team_baseline": baseline, "reps": reps}


def rep_coaching_view(cam_id: str) -> dict:
    """One rep's data alongside the team baseline — the coaching conversation artifact."""
    report = team_report()
    rep = next((r for r in report["reps"] if r["cam_id"] == cam_id), None)
    if not rep:
        raise ValueError(f"Unknown CAM: {cam_id}")
    return {"rep": rep, "team_baseline": report["team_baseline"],
            "open_action_items": db.query(
                "SELECT id, partner_id, description, due_at FROM action_items "
                "WHERE cam_id=? AND closed_at IS NULL", (cam_id,))}
