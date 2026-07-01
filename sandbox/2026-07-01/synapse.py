#!/usr/bin/env python3
"""
SYNAPSE — Partner Synergy & Ecosystem Intelligence Platform

Maps the partner ecosystem as an interconnected graph, identifies influencers,
bridges, clusters, and coverage gaps, and recommends strategic pairings for
co-sell, co-marketing, and referral optimization.

Usage:
    python3 synapse.py demo            # Load demo ecosystem data
    python3 synapse.py graph           # Show network graph (ASCII)
    python3 synapse.py metrics         # Network centrality & influence scores
    python3 synapse.py clusters        # Detect partner communities/clusters
    python3 synapse.py gaps            # Coverage gap analysis
    python3 synapse.py recommend       # Strategic pairing recommendations
    python3 synapse.py pair --p1 A --p2 B  # Synergy score between two partners
    python3 synapse.py partner NAME    # Drill into a specific partner
    python3 synapse.py dashboard       # Executive ecosystem summary
    python3 synapse.py serve           # Start as MCP server
"""

import json
import os
import sys
import math
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path.home() / ".synapse"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ECOSYSTEM_FILE = DATA_DIR / "ecosystem.json"

DEMO_PARTNERS = [
    {"id": "p1", "name": "TechSolvers Inc", "tier": "platinum", "region": "West",
     "verticals": ["healthcare", "fintech"],
     "capabilities": ["implementation", "support", "training", "integration"],
     "certifications": ["platinum_sales", "platinum_support", "security_specialist"],
     "annual_revenue": 850000, "deals_last_quarter": 18, "team_size": 45},
    {"id": "p2", "name": "EnterpriseOps Group", "tier": "platinum", "region": "Northeast",
     "verticals": ["enterprise", "manufacturing", "healthcare"],
     "capabilities": ["implementation", "support", "managed_services", "consulting"],
     "certifications": ["platinum_sales", "platinum_support", "cloud_architect"],
     "annual_revenue": 1200000, "deals_last_quarter": 24, "team_size": 68},
    {"id": "p3", "name": "DataBridge Partners", "tier": "gold", "region": "Midwest",
     "verticals": ["finance", "insurance"],
     "capabilities": ["implementation", "integration", "data_migration"],
     "certifications": ["gold_sales", "gold_support"],
     "annual_revenue": 420000, "deals_last_quarter": 9, "team_size": 22},
    {"id": "p4", "name": "CloudSync Networks", "tier": "gold", "region": "West",
     "verticals": ["saas", "tech", "healthcare"],
     "capabilities": ["cloud_migration", "implementation", "support"],
     "certifications": ["gold_sales", "gold_support", "cloud_practitioner"],
     "annual_revenue": 310000, "deals_last_quarter": 7, "team_size": 18},
    {"id": "p5", "name": "Summit Global", "tier": "gold", "region": "Southeast",
     "verticals": ["retail", "manufacturing", "logistics"],
     "capabilities": ["implementation", "support", "training"],
     "certifications": ["gold_sales"],
     "annual_revenue": 520000, "deals_last_quarter": 11, "team_size": 30},
    {"id": "p6", "name": "Peak Performance Group", "tier": "platinum", "region": "Southwest",
     "verticals": ["energy", "utilities"],
     "capabilities": ["implementation", "support", "managed_services", "integration"],
     "certifications": ["platinum_sales", "platinum_support", "security_specialist"],
     "annual_revenue": 620000, "deals_last_quarter": 14, "team_size": 35},
    {"id": "p7", "name": "Meridian Tech", "tier": "gold", "region": "Mid-Atlantic",
     "verticals": ["education", "government", "nonprofit"],
     "capabilities": ["implementation", "training", "support"],
     "certifications": ["gold_sales", "gold_support"],
     "annual_revenue": 195000, "deals_last_quarter": 5, "team_size": 12},
    {"id": "p8", "name": "NorthStar Solutions", "tier": "authorized", "region": "West",
     "verticals": ["small_business", "tech"],
     "capabilities": ["implementation"],
     "certifications": [],
     "annual_revenue": 95000, "deals_last_quarter": 2, "team_size": 5},
    {"id": "p9", "name": "Velocity Systems", "tier": "gold", "region": "Northeast",
     "verticals": ["fintech", "healthcare", "enterprise"],
     "capabilities": ["implementation", "integration", "consulting", "support"],
     "certifications": ["gold_sales", "gold_support", "security_specialist"],
     "annual_revenue": 480000, "deals_last_quarter": 13, "team_size": 28},
    {"id": "p10", "name": "Equinox Partners", "tier": "authorized", "region": "Southeast",
     "verticals": ["retail", "hospitality"],
     "capabilities": ["implementation", "training"],
     "certifications": [],
     "annual_revenue": 78000, "deals_last_quarter": 3, "team_size": 4},
    {"id": "p11", "name": "Titan Cloud Group", "tier": "platinum", "region": "Midwest",
     "verticals": ["manufacturing", "logistics", "energy"],
     "capabilities": ["cloud_migration", "managed_services", "implementation", "support", "consulting"],
     "certifications": ["platinum_sales", "platinum_support", "cloud_architect", "security_specialist"],
     "annual_revenue": 980000, "deals_last_quarter": 21, "team_size": 52},
    {"id": "p12", "name": "NexGen Solutions", "tier": "gold", "region": "Pacific Northwest",
     "verticals": ["tech", "saas", "gaming"],
     "capabilities": ["implementation", "integration", "data_migration"],
     "certifications": ["gold_sales", "gold_support", "cloud_practitioner"],
     "annual_revenue": 350000, "deals_last_quarter": 8, "team_size": 16},
]

DEMO_RELATIONSHIPS = [
    ("p1", "p4", 5), ("p1", "p2", 8), ("p2", "p9", 6), ("p2", "p3", 3),
    ("p3", "p6", 4), ("p4", "p8", 2), ("p4", "p12", 3), ("p5", "p10", 1),
    ("p5", "p2", 2), ("p6", "p11", 7), ("p7", "p2", 2), ("p7", "p9", 4),
    ("p9", "p11", 5), ("p10", "p5", 2), ("p11", "p1", 4), ("p11", "p6", 7),
    ("p12", "p1", 3), ("p12", "p4", 3), ("p3", "p9", 2), ("p8", "p1", 1),
]

DEMO_REFERRALS = [
    ("p4", "p1", 3), ("p8", "p4", 2), ("p10", "p5", 1), ("p3", "p2", 2),
    ("p7", "p9", 3), ("p12", "p1", 2), ("p5", "p2", 1), ("p9", "p11", 2),
    ("p4", "p12", 1),
]

class EcosystemGraph:
    def __init__(self, partners=None, cosell_edges=None, referral_edges=None):
        self.partners = {}
        self.cosell = defaultdict(dict)
        self.referrals = defaultdict(dict)
        self._partner_by_name = {}
        if partners:
            for p in partners:
                self.add_partner(p)
        if cosell_edges:
            for src, dst, weight in cosell_edges:
                self.add_cosell(src, dst, weight)
        if referral_edges:
            for src, dst, weight in referral_edges:
                self.add_referral(src, dst, weight)

    def add_partner(self, partner):
        pid = partner["id"]
        self.partners[pid] = partner
        self._partner_by_name[partner["name"].lower()] = pid

    def add_cosell(self, src, dst, weight=1):
        self.cosell[src][dst] = weight
        self.cosell[dst][src] = weight

    def add_referral(self, src, dst, weight=1):
        self.referrals[src][dst] = self.referrals[src].get(dst, 0) + weight

    def get_partner(self, identifier):
        if identifier in self.partners:
            return self.partners[identifier]
        key = identifier.lower()
        if key in self._partner_by_name:
            return self.partners[self._partner_by_name[key]]
        for name, pid in self._partner_by_name.items():
            if key in name or name in key:
                return self.partners[pid]
        return None

    @property
    def partner_count(self):
        return len(self.partners)

    def cosell_neighbors(self, pid):
        return list(self.cosell.get(pid, {}).items())

    def referral_incoming(self, pid):
        result = []
        for src, targets in self.referrals.items():
            if pid in targets:
                result.append((src, targets[pid]))
        return result

    def referral_outgoing(self, pid):
        return list(self.referrals.get(pid, {}).items())

    def total_connections(self, pid):
        cs = len(self.cosell.get(pid, {}))
        ri = len(self.referral_incoming(pid))
        ro = len(self.referral_outgoing(pid))
        return cs + ri + ro

    def synergy_score(self, pid_a, pid_b):
        pa = self.partners.get(pid_a)
        pb = self.partners.get(pid_b)
        if not pa or not pb:
            return 0, ["One or both partners not found"]

        score = 0.0
        reasons = []

        cosell_weight = self.cosell.get(pid_a, {}).get(pid_b, 0) + self.cosell.get(pid_b, {}).get(pid_a, 0)
        ref_ab = self.referrals.get(pid_a, {}).get(pid_b, 0)
        ref_ba = self.referrals.get(pid_b, {}).get(pid_a, 0)
        total_deals = cosell_weight + ref_ab + ref_ba
        deal_score = min(total_deals * 8, 40)
        if deal_score > 0:
            score += deal_score
            reasons.append(f"Direct relationship: {total_deals} joint/referred deals (+{deal_score:.0f})")

        verticals_a = set(pa.get("verticals", []))
        verticals_b = set(pb.get("verticals", []))
        overlap = verticals_a & verticals_b
        if overlap:
            v_score = min(len(overlap) * 5, 15)
            score += v_score
            reasons.append(f"Vertical overlap: {', '.join(sorted(overlap))} (+{v_score})")

        caps_a = set(pa.get("capabilities", []))
        caps_b = set(pb.get("capabilities", []))
        unique_a = caps_a - caps_b
        unique_b = caps_b - caps_a
        complementarity = len(unique_a) + len(unique_b)
        if complementarity > 0:
            c_score = min(complementarity * 3, 15)
            score += c_score
            reasons.append(f"Capability complementarity: {complementarity} unique capabilities (+{c_score})")

        if pa.get("region") == pb.get("region"):
            score += 10
            reasons.append(f"Same region: {pa['region']} (+10)")

        neighbors_a = set(self.cosell.get(pid_a, {}).keys())
        neighbors_b = set(self.cosell.get(pid_b, {}).keys())
        common = (neighbors_a & neighbors_b) - {pid_a, pid_b}
        if common:
            cn_score = min(len(common) * 3, 10)
            score += cn_score
            reasons.append(f"Common connections: {len(common)} mutual partners (+{cn_score})")

        tiers = {"platinum": 3, "gold": 2, "authorized": 1}
        ta = tiers.get(pa.get("tier", ""), 0)
        tb = tiers.get(pb.get("tier", ""), 0)
        tier_diff = abs(ta - tb)
        if tier_diff == 0:
            score += 10
            reasons.append("Same tier level (+10)")
        elif tier_diff == 1:
            score += 5
            reasons.append("Adjacent tier level (+5)")
        else:
            score += 2
            reasons.append("Tier gap exists (+2)")

        return min(score, 100), reasons

    def degree_centrality(self):
        n = self.partner_count
        if n <= 1:
            return {}
        result = {}
        for pid in self.partners:
            result[pid] = self.total_connections(pid) / (n - 1)
        return result

    def betweenness_centrality(self):
        nodes = list(self.partners.keys())
        n = len(nodes)
        betweenness = {pid: 0.0 for pid in nodes}
        if n <= 2:
            return betweenness

        adj = defaultdict(set)
        for src in self.cosell:
            for dst in self.cosell[src]:
                adj[src].add(dst)
                adj[dst].add(src)
        for src in self.referrals:
            for dst in self.referrals[src]:
                adj[src].add(dst)
                adj[dst].add(src)

        for s in nodes:
            stack = [s]
            prev = {s: []}
            dist = {s: 0}
            while stack:
                v = stack.pop(0)
                for w in adj.get(v, set()):
                    if w not in dist:
                        stack.append(w)
                        dist[w] = dist[v] + 1
                        prev[w] = [v]
                    elif dist[w] == dist[v] + 1:
                        prev[w].append(v)

            dependencies = {pid: 0.0 for pid in nodes}
            order = sorted(nodes, key=lambda x: dist.get(x, float('inf')), reverse=True)
            for w in order:
                if w == s:
                    continue
                for v in prev.get(w, []):
                    dependencies[v] += (1.0 + dependencies[w]) / len(prev[w])
            for v in nodes:
                if v != s:
                    betweenness[v] += dependencies[v]

        denom = (n - 1) * (n - 2) / 2
        if denom > 0:
            for pid in betweenness:
                betweenness[pid] /= denom
        return betweenness

    def detect_clusters(self):
        nodes = list(self.partners.keys())
        if not nodes:
            return []

        adj = defaultdict(set)
        for src in self.cosell:
            for dst in self.cosell[src]:
                adj[src].add(dst)
                adj[dst].add(src)
        for src in self.referrals:
            for dst in self.referrals[src]:
                adj[src].add(dst)
                adj[dst].add(src)

        labels = {pid: i for i, pid in enumerate(nodes)}
        changed = True
        for _ in range(50):
            if not changed:
                break
            changed = False
            for pid in nodes:
                neighbor_labels = defaultdict(float)
                for nb in adj.get(pid, set()):
                    weight = self.cosell.get(pid, {}).get(nb, 0) + \
                             self.referrals.get(pid, {}).get(nb, 0) + \
                             self.referrals.get(nb, {}).get(pid, 0)
                    weight = max(weight, 1)
                    neighbor_labels[labels[nb]] += weight
                if neighbor_labels:
                    max_count = max(neighbor_labels.values())
                    best_labels = [l for l, c in neighbor_labels.items() if c == max_count]
                    new_label = min(best_labels)
                    if new_label != labels[pid]:
                        labels[pid] = new_label
                        changed = True

        clusters = defaultdict(list)
        for pid, label in labels.items():
            clusters[label].append(pid)
        return list(clusters.values())

    def coverage_gaps(self):
        gaps = {}
        regions_covered = set(p.get("region", "") for p in self.partners.values())
        all_regions = ["Northeast", "Midwest", "South", "Southwest", "West",
                       "Pacific Northwest", "Southeast", "Mid-Atlantic"]
        missing = [r for r in all_regions if r not in regions_covered]
        if missing:
            gaps["uncovered_regions"] = missing

        low_coverage = {}
        for region in regions_covered:
            partners_in_region = [p for p in self.partners.values() if p.get("region") == region]
            tiers_in_region = [p.get("tier", "") for p in partners_in_region]
            if not any(t in ("platinum", "gold") for t in tiers_in_region):
                low_coverage[region] = len(partners_in_region)
        if low_coverage:
            gaps["low_coverage_regions"] = low_coverage

        vertical_coverage = defaultdict(list)
        for p in self.partners.values():
            for v in p.get("verticals", []):
                vertical_coverage[v].append(p["name"])
        weak_verticals = {v: plist for v, plist in vertical_coverage.items() if len(plist) < 2}
        if weak_verticals:
            gaps["weak_vertical_coverage"] = weak_verticals

        capability_coverage = Counter()
        for p in self.partners.values():
            for c in p.get("capabilities", []):
                capability_coverage[c] += 1
        rare = {c: count for c, count in capability_coverage.items() if count < 3}
        if rare:
            gaps["rare_capabilities"] = rare

        return gaps


def save_ecosystem(graph):
    data = {
        "partners": list(graph.partners.values()),
        "cosell_edges": [(s, d, w) for s, neighbors in graph.cosell.items()
                         for d, w in neighbors.items() if s < d],
        "referral_edges": [(s, d, w) for s, neighbors in graph.referrals.items()
                           for d, w in neighbors.items()],
        "generated": datetime.now().isoformat(),
    }
    ECOSYSTEM_FILE.write_text(json.dumps(data, indent=2))
    return ECOSYSTEM_FILE


def load_ecosystem():
    if not ECOSYSTEM_FILE.exists():
        return None
    data = json.loads(ECOSYSTEM_FILE.read_text())
    return EcosystemGraph(data.get("partners"), data.get("cosell_edges"), data.get("referral_edges"))


def _ansi(code, text):
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

BOLD = lambda t: _ansi("1", t)
DIM = lambda t: _ansi("2", t)
GREEN = lambda t: _ansi("32", t)
YELLOW = lambda t: _ansi("33", t)
RED = lambda t: _ansi("31", t)
CYAN = lambda t: _ansi("36", t)
MAGENTA = lambda t: _ansi("35", t)
BLUE = lambda t: _ansi("34", t)

TIER_COLORS = {
    "platinum": lambda t: _ansi("35;1", t),
    "gold": lambda t: _ansi("33;1", t),
    "authorized": lambda t: _ansi("37", t),
}

def _tier_color(tier, text):
    return TIER_COLORS.get(tier, lambda t: t)(text)


def _print_table(headers, rows, indent=0):
    if not rows:
        print("  (no data)")
        return
    col_widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) + 2 for i, h in enumerate(headers)]
    header = "".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(" " * indent + BOLD(header))
    print(" " * indent + "-" * sum(col_widths))
    for row in rows:
        line = "".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers)))
        print(" " * indent + line)


# ---- Commands ----

def cmd_demo():
    graph = EcosystemGraph(DEMO_PARTNERS, DEMO_RELATIONSHIPS, DEMO_REFERRALS)
    fpath = save_ecosystem(graph)
    print()
    print("  " + BOLD("SYNAPSE Demo Ecosystem Loaded"))
    print(f"     Saved to: {fpath}")
    print(f"     {BOLD(str(graph.partner_count))} partners")
    cosell_count = sum(1 for s in graph.cosell for d in graph.cosell[s] if s < d)
    print(f"     {BOLD(str(cosell_count))} co-sell relationships")
    ref_count = sum(len(v) for v in graph.referrals.values())
    print(f"     {BOLD(str(ref_count))} referral relationships")
    cmd_dashboard(graph)


def cmd_graph(graph):
    print()
    print("  " + BOLD("Partner Ecosystem Network Graph"))
    print()

    for pid, partner in graph.partners.items():
        name = partner["name"]
        tier = partner["tier"]
        label = _tier_color(tier, f"[{tier[0].upper()}]")
        print(f"  {label} {BOLD(name)} ({partner['region']})")

        cs = graph.cosell_neighbors(pid)
        if cs:
            for nb_id, w in sorted(cs, key=lambda x: -x[1]):
                nb = graph.partners.get(nb_id, {})
                nb_name = nb.get("name", nb_id)
                nb_tier = nb.get("tier", "")
                nb_label = _tier_color(nb_tier, f"[{nb_tier[0].upper()}]")
                deal_label = f"({w} joint deals)"
                print(f"       + {nb_label} {nb_name}  {DIM(deal_label)}")
        else:
            print(f"       + {DIM('(no co-sell relationships)')}")

        for dst_id, w in sorted(graph.referral_outgoing(pid), key=lambda x: -x[1]):
            dst = graph.partners.get(dst_id, {})
            print(f"          {DIM('-> ' + dst.get('name', '?') + f' ({w} referrals)')}")

        for src_id, w in sorted(graph.referral_incoming(pid), key=lambda x: -x[1]):
            src = graph.partners.get(src_id, {})
            print(f"          {DIM('<- ' + src.get('name', '?') + f' ({w} referrals)')}")

        print()


def cmd_metrics(graph):
    print()
    print("  " + BOLD("Partner Network Centrality & Influence"))
    print()

    degree = graph.degree_centrality()
    betweenness = graph.betweenness_centrality()

    partners_data = []
    for pid, partner in graph.partners.items():
        deg_score = degree.get(pid, 0)
        bet_score = betweenness.get(pid, 0)
        total_deals = partner.get("deals_last_quarter", 0)
        rev = partner.get("annual_revenue", 0)
        influence = (deg_score * 40) + (bet_score * 40) + (min(total_deals / 25, 1) * 10) + (min(rev / 1200000, 1) * 10)
        influence = round(min(influence * 10, 100), 1)
        partners_data.append({
            "name": partner["name"], "tier": partner["tier"],
            "degree": round(deg_score, 3), "betweenness": round(bet_score, 3),
            "connections": graph.total_connections(pid),
            "deals": total_deals, "revenue": rev, "influence": influence,
        })

    partners_data.sort(key=lambda x: -x["influence"])
    tier_abbrev = {"platinum": "P", "gold": "G", "authorized": "A"}

    rows = []
    for p in partners_data:
        ta = tier_abbrev.get(p["tier"], "?")
        inf_bar = chr(9608) * max(1, int(p["influence"] / 10))
        rows.append((
            _tier_color(p["tier"], ta),
            BOLD(p["name"]),
            f"{p['influence']:.0f}",
            str(p["connections"]),
            f"{p['degree']:.2f}",
            f"{p['betweenness']:.2f}",
            f"${p['revenue']:,}",
            inf_bar,
        ))
    _print_table(["T", "Partner", "Influence", "Conn", "Degree", "Between", "Revenue", "Bar"], rows)

    top3 = partners_data[:3]
    print()
    print("  " + BOLD("Top Influencers"))
    for i, p in enumerate(top3, 1):
        tc = _tier_color(p["tier"], p["tier"].upper())
        print(f"     {i}. {BOLD(p['name'])} ({tc}) - Influence: {p['influence']}/100, "
              f"{p['connections']} connections, {p['deals']} deals/quarter")

    bridges = [p for p in partners_data if p['betweenness'] > 0.05]
    if bridges:
        print()
        print("  " + BOLD("Network Bridges"))
        for p in sorted(bridges, key=lambda x: -x['betweenness'])[:3]:
            print(f"     {BOLD(p['name'])} - connects across clusters")


def cmd_clusters(graph):
    print()
    print("  " + BOLD("Partner Ecosystem Clusters"))
    print()

    clusters = graph.detect_clusters()
    for i, cluster in enumerate(clusters, 1):
        partners_in = [graph.partners[pid] for pid in cluster if pid in graph.partners]
        total_rev = sum(p.get("annual_revenue", 0) for p in partners_in)
        total_deals = sum(p.get("deals_last_quarter", 0) for p in partners_in)
        tiers = sorted(set(p.get("tier", "") for p in partners_in))
        print(f"  {BOLD(f'Cluster {i}')}  |  {len(partners_in)} partners  |  "
              f"${total_rev:,} annual revenue  |  {total_deals} deals/q  |  Tiers: {', '.join(tiers)}")

        internal_edges = []
        for pid_a in cluster:
            for pid_b in cluster:
                if pid_a < pid_b:
                    w = graph.cosell.get(pid_a, {}).get(pid_b, 0)
                    if w > 0:
                        internal_edges.append((pid_a, pid_b, w))

        for pid in cluster:
            p = graph.partners.get(pid, {})
            name = p.get("name", pid)
            tier = p.get("tier", "")
            region = p.get("region", "")
            verticals = ", ".join(p.get("verticals", []))
            label = _tier_color(tier, f"[{tier[0].upper()}]")
            print(f"     {label} {BOLD(name)}  {DIM('| ' + region + ' | ' + verticals)}")

            for (a, b, w) in internal_edges:
                if a == pid:
                    nb = graph.partners.get(b, {})
                    nb_name = nb.get("name", "?")
                    print(f"          {DIM('<=> ' + nb_name + f' ({w} deals)')}")
                elif b == pid:
                    nb = graph.partners.get(a, {})
                    nb_name = nb.get("name", "?")
                    print(f"          {DIM('<=> ' + nb_name + f' ({w} deals)')}")

        other_pids = set()
        for j, other in enumerate(clusters):
            if i - 1 != j:
                other_pids.update(other)
        cross_edges = []
        for pid in cluster:
            for other_pid in other_pids:
                w = graph.cosell.get(pid, {}).get(other_pid, 0)
                if w > 0:
                    cross_edges.append((pid, other_pid, w))
        if cross_edges:
            print(f"     {DIM('--- cross-cluster connections ---')}")
            for src, dst, w in cross_edges:
                src_p = graph.partners.get(src, {}).get("name", src)
                dst_p = graph.partners.get(dst, {}).get("name", dst)
                print(f"          {DIM('<=>' + src_p + ' <=> ' + dst_p + f' ({w} deals)')}")
        print()


def cmd_gaps(graph):
    print()
    print("  " + BOLD("Coverage Gap Analysis"))
    print()

    gaps = graph.coverage_gaps()
    if not gaps:
        print(GREEN("  No significant coverage gaps detected."))
        return

    if "uncovered_regions" in gaps:
        ur = gaps["uncovered_regions"]
        print(f"  {BOLD('Uncovered Regions')}  {RED(f'({len(ur)})')}")
        for r in ur:
            print(f"     x {r} - {DIM('no partners in this region')}")

    if "low_coverage_regions" in gaps:
        print()
        print("  " + BOLD("Under-Served Regions"))
        for r, count in gaps["low_coverage_regions"].items():
            print(f"     Warning {r} - only {count} authorized partner(s), no Gold/Platinum")
            print(f"        {DIM('-> Recruit or upgrade partner coverage in this region')}")

    if "weak_vertical_coverage" in gaps:
        print()
        print("  " + BOLD("Thin Vertical Coverage"))
        for v, partners in sorted(gaps["weak_vertical_coverage"].items()):
            print(f"     Warning {v} - only covered by: {', '.join(partners)}")
            print(f"        {DIM('-> Consider recruiting partners with this vertical focus')}")

    if "rare_capabilities" in gaps:
        print()
        print("  " + BOLD("Scarce Capabilities"))
        for c, count in sorted(gaps["rare_capabilities"].items(), key=lambda x: x[1]):
            if count < 2:
                print(f"     Red {c} - only {count} partner(s) have this capability {DIM('(critical gap)')}")
                print(f"        {DIM('-> Recruit or train partners in this capability')}")
            else:
                print(f"     Yellow {c} - only {count} partners have this capability")
                print(f"        {DIM('-> Consider developing this capability internally or recruiting')}")
    print()


def cmd_recommend(graph):
    print()
    print("  " + BOLD("Strategic Partner Pairing Recommendations"))
    print()

    pids = list(graph.partners.keys())
    pairs_scored = []
    for i in range(len(pids)):
        for j in range(i + 1, len(pids)):
            a, b = pids[i], pids[j]
            if graph.cosell.get(a, {}).get(b, 0) == 0:
                score, reasons = graph.synergy_score(a, b)
                pairs_scored.append((score, a, b, reasons))

    pairs_scored.sort(key=lambda x: -x[0])
    if not pairs_scored:
        print("  No recommendations available.")
        return

    print(f"  Top recommended pairings (no existing relationship):\n")
    for score, a, b, reasons in pairs_scored[:8]:
        pa = graph.partners[a]
        pb = graph.partners[b]
        ta = _tier_color(pa["tier"], f"[{pa['tier'][0].upper()}]")
        tb = _tier_color(pb["tier"], f"[{pb['tier'][0].upper()}]")
        bar_len = max(1, int(score / 10))
        bar = chr(9608) * bar_len + chr(9617) * (10 - bar_len)
        print(f"  {BOLD(pa['name'])} {ta}  x  {BOLD(pb['name'])} {tb}")
        print(f"     {BOLD(f'Synergy: {score:.0f}/100')}  {DIM(f'[{bar}]')}")
        for reason in reasons[:3]:
            print(f"       - {reason}")
        print()

    print(f"  {DIM('(showing top 8 of ' + str(len(pairs_scored)) + ' potential pairings)')}")


def cmd_pair(graph, p1_name, p2_name):
    pa = graph.get_partner(p1_name)
    pb = graph.get_partner(p2_name)
    if not pa or not pb:
        print(f"  {RED('X')} Partner not found")
        return
    if pa["id"] == pb["id"]:
        print("  Can't calculate synergy with yourself!")
        return

    ta = _tier_color(pa["tier"], f"[{pa['tier'][0].upper()}]")
    tb = _tier_color(pb["tier"], f"[{pb['tier'][0].upper()}]")
    print()
    print("  " + BOLD("Synergy Report"))
    print(f"  {BOLD(pa['name'])} {ta}  x  {BOLD(pb['name'])} {tb}\n")

    score, reasons = graph.synergy_score(pa["id"], pb["id"])
    bar_len = max(1, int(score / 10))
    bar = chr(9608) * bar_len + chr(9617) * (10 - bar_len)

    if score >= 60:
        color = GREEN
    elif score >= 30:
        color = YELLOW
    else:
        color = RED

    print(f"     {BOLD('Overall Synergy:')} {color(f'{score:.0f}/100')}  [{bar}]\n")
    print(f"     {BOLD('Score Breakdown:')}")
    for reason in reasons:
        print(f"       + {reason}")

    cosell_w = graph.cosell.get(pa["id"], {}).get(pb["id"], 0)
    if cosell_w > 0:
        print(f"\n     {DIM('Already co-selling:')} {BOLD(str(cosell_w))} joint deals")
    else:
        print(f"\n     {DIM('No existing co-sell relationship')}")

    ref_ab = graph.referrals.get(pa["id"], {}).get(pb["id"], 0)
    ref_ba = graph.referrals.get(pb["id"], {}).get(pa["id"], 0)
    if ref_ab > 0 or ref_ba > 0:
        print(f"     {DIM('Referral activity:')} {pa['name']}->{pb['name']}: {ref_ab}, "
              f"{pb['name']}->{pa['name']}: {ref_ba}")

    print(f"\n     {BOLD('Recommendation:')}")
    if score >= 60:
        print(f"       {GREEN('Strong synergy - introduce these partners for co-sell/co-marketing')}")
    elif score >= 30:
        print(f"       {YELLOW('Moderate synergy - consider joint webinar or pilot co-sell program')}")
    else:
        print(f"       {RED('Low synergy - not a priority for strategic pairing')}")
    print()


def cmd_partner(graph, identifier):
    partner = graph.get_partner(identifier)
    if not partner:
        print(f"  {RED('X')} Partner not found: {identifier}")
        available = ", ".join(sorted(p["name"] for p in graph.partners.values()))
        print(f"     Available: {available}")
        return

    pid = partner["id"]
    tier_label = _tier_color(partner["tier"], partner["tier"].upper())

    print()
    print("  " + BOLD("Partner Intelligence Report"))
    print(f"  {BOLD(partner['name'])}  {tier_label}  |  {partner['region']}\n")

    print("  " + BOLD("Profile"))
    print(f"     Revenue:   ${partner['annual_revenue']:,}/yr")
    print(f"     Team:      {partner['team_size']} people")
    print(f"     Deals:     {partner['deals_last_quarter']} last quarter")
    print(f"     Verticals: {', '.join(partner.get('verticals', []))}")
    print(f"     Certs:     {', '.join(partner.get('certifications', [])) or 'none'}")
    print(f"     Capabilities: {', '.join(partner.get('capabilities', []))}")

    degree = graph.degree_centrality().get(pid, 0)
    betweenness = graph.betweenness_centrality().get(pid, 0)
    connections = graph.total_connections(pid)

    print()
    print("  " + BOLD("Network Position"))
    print(f"     Connections: {connections}")
    print(f"     Degree Centrality: {degree:.3f}")
    print(f"     Betweenness: {betweenness:.3f}")

    cs = graph.cosell_neighbors(pid)
    if cs:
        print()
        print("  " + BOLD("Co-Sell Partners"))
        for nb_id, w in sorted(cs, key=lambda x: -x[1]):
            nb = graph.partners.get(nb_id, {})
            print(f"     <=> {nb.get('name', '?')} ({w} joint deals)")

    ref_out = graph.referral_outgoing(pid)
    if ref_out:
        print()
        print("  " + BOLD("Referrals Given (Outgoing)"))
        for dst_id, w in sorted(ref_out, key=lambda x: -x[1]):
            dst = graph.partners.get(dst_id, {})
            print(f"     -> {dst.get('name', '?')} ({w} deals referred)")

    ref_in = graph.referral_incoming(pid)
    if ref_in:
        print()
        print("  " + BOLD("Referrals Received (Incoming)"))
        for src_id, w in sorted(ref_in, key=lambda x: -x[1]):
            src = graph.partners.get(src_id, {})
            print(f"     <- {src.get('name', '?')} ({w} deals referred)")

    suggested = []
    for other_pid in graph.partners:
        if other_pid == pid or graph.cosell.get(pid, {}).get(other_pid, 0) > 0:
            continue
        score, _ = graph.synergy_score(pid, other_pid)
        if score >= 40:
            suggested.append((score, other_pid))

    if suggested:
        suggested.sort(key=lambda x: -x[0])
        print()
        print("  " + BOLD("Suggested New Connections"))
        for score, sid in suggested[:4]:
            sp = graph.partners.get(sid, {})
            print(f"     + {sp.get('name', '?')} (synergy: {score:.0f}/100)")
    print()


def cmd_dashboard(graph=None):
    if graph is None:
        graph = load_ecosystem()
        if not graph:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
            return

    print()
    print("  " + BOLD("SYNAPSE Ecosystem Dashboard"))
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    total_rev = sum(p.get("annual_revenue", 0) for p in graph.partners.values())
    total_deals = sum(p.get("deals_last_quarter", 0) for p in graph.partners.values())
    cosell_count = sum(1 for s in graph.cosell for d in graph.cosell[s] if s < d)
    ref_count = sum(len(v) for v in graph.referrals.values())

    print("  " + BOLD("Ecosystem at a Glance"))
    print(f"     Total Partners:   {BOLD(str(graph.partner_count))}")
    print(f"     Annual Revenue:   {BOLD(f'${total_rev:,}')}")
    print(f"     Quarterly Deals:  {BOLD(str(total_deals))}")
    print(f"     Co-Sell Edges:    {BOLD(str(cosell_count))}")
    print(f"     Referral Edges:   {BOLD(str(ref_count))}")

    tier_counts = Counter(p.get("tier", "") for p in graph.partners.values())
    print()
    print("  " + BOLD("Tier Distribution"))
    for tier in ["platinum", "gold", "authorized"]:
        count = tier_counts.get(tier, 0)
        tc = _tier_color(tier, tier.upper())
        print(f"     {tc}: {count}")

    region_counts = Counter(p.get("region", "") for p in graph.partners.values())
    print()
    print("  " + BOLD("Regional Coverage"))
    for region in sorted(region_counts.keys(), key=lambda r: -region_counts[r]):
        count = region_counts[region]
        tiers_in = [p.get("tier", "") for p in graph.partners.values()
                     if p.get("region") == region]
        best = max(set(tiers_in), key=tiers_in.count) if tiers_in else ""
        print(f"     {region}: {count} partners  {DIM(f'(best: {best})')}")

    degree = graph.degree_centrality()
    betweenness = graph.betweenness_centrality()
    influencers = []
    for pid, partner in graph.partners.items():
        inf = (degree.get(pid, 0) * 40 + betweenness.get(pid, 0) * 40 +
               min(partner.get("deals_last_quarter", 0) / 25, 1) * 10 +
               min(partner.get("annual_revenue", 0) / 1200000, 1) * 10)
        influencers.append((inf * 10, pid))
    influencers.sort(key=lambda x: -x[0])

    print()
    print("  " + BOLD("Key Ecosystem Players"))
    for i, (score, pid) in enumerate(influencers[:3], 1):
        p = graph.partners.get(pid, {})
        tc = _tier_color(p.get("tier", ""), p.get("tier", "").upper())
        print(f"     {i}. {BOLD(p.get('name', ''))} ({tc}) - influence: {min(score, 100):.0f}/100")

    clusters = graph.detect_clusters()
    print()
    print("  " + BOLD("Community Clusters"))
    for i, cluster in enumerate(clusters, 1):
        names = [graph.partners[pid]["name"] for pid in cluster if pid in graph.partners]
        print(f"     Cluster {i}: {', '.join(names)}")

    gaps = graph.coverage_gaps()
    if gaps:
        gap_count = sum(len(v) if isinstance(v, list) else len(v) for v in gaps.values())
        print()
        print("  " + BOLD("Coverage Gaps Detected"))
        print(f"     {gap_count} gap(s) found. Run {CYAN('synapse.py gaps')} for details.")
    print()


# ---- MCP Server Mode ----

def cmd_serve():
    try:
        from mcp.server import Server, NotificationOptions
        from mcp.server.models import InitializationOptions
        import mcp.server.stdio
        import mcp.types as types
    except ImportError:
        print("  MCP mode requires the 'mcp' package. Install with:")
        print("    pip install mcp")
        sys.exit(1)

    server = Server("synapse")

    @server.list_tools()
    async def list_tools() -> list:
        return [
            types.Tool(
                name="load_demo_ecosystem",
                description="Load demo ecosystem data with 12 partners, 20 co-sell relationships, and referral edges.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="get_ecosystem_summary",
                description="Get an executive summary of the partner ecosystem.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="get_partner_intel",
                description="Get detailed network intelligence for a specific partner.",
                inputSchema={
                    "type": "object",
                    "properties": {"partner_name": {"type": "string", "description": "Partner name"}},
                    "required": ["partner_name"],
                },
            ),
            types.Tool(
                name="calculate_synergy",
                description="Calculate synergy score between two partners.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "partner_a": {"type": "string", "description": "First partner name"},
                        "partner_b": {"type": "string", "description": "Second partner name"},
                    },
                    "required": ["partner_a", "partner_b"],
                },
            ),
            types.Tool(
                name="get_top_influencers",
                description="Get top ecosystem influencers by network centrality.",
                inputSchema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "description": "Number to return", "default": 5}},
                    "required": [],
                },
            ),
            types.Tool(
                name="detect_clusters",
                description="Detect partner communities/clusters in the ecosystem.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="get_coverage_gaps",
                description="Identify coverage gaps by region, vertical, and capability.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="get_pairing_recommendations",
                description="Get strategic pairing recommendations for unconnected partners.",
                inputSchema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "description": "Number", "default": 8}},
                    "required": [],
                },
            ),
            types.Tool(
                name="get_network_metrics",
                description="Get network centrality metrics for all partners.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        graph = load_ecosystem()
        if not graph and name != "load_demo_ecosystem":
            return [types.TextContent(type="text", text="No ecosystem data loaded. Call load_demo_ecosystem first.")]

        if name == "load_demo_ecosystem":
            g = EcosystemGraph(DEMO_PARTNERS, DEMO_RELATIONSHIPS, DEMO_REFERRALS)
            save_ecosystem(g)
            return [types.TextContent(type="text", text=f"Loaded demo ecosystem with {g.partner_count} partners.")]

        elif name == "get_ecosystem_summary":
            tr = sum(p.get("annual_revenue", 0) for p in graph.partners.values())
            td = sum(p.get("deals_last_quarter", 0) for p in graph.partners.values())
            tc = dict(Counter(p.get("tier", "") for p in graph.partners.values()))
            cls = graph.detect_clusters()
            out = json.dumps({
                "partner_count": graph.partner_count,
                "total_annual_revenue": tr, "quarterly_deals": td,
                "tier_distribution": tc, "cluster_count": len(cls),
                "cosell_edges": sum(1 for s in graph.cosell for d in graph.cosell[s] if s < d),
            }, indent=2)
            return [types.TextContent(type="text", text=out)]

        elif name == "get_partner_intel":
            partner = graph.get_partner(arguments["partner_name"])
            if not partner:
                return [types.TextContent(type="text", text=f"Partner not found")]
            pid = partner["id"]
            cs = [{"partner": graph.partners.get(nid, {}).get("name"), "joint_deals": w}
                  for nid, w in graph.cosell_neighbors(pid)]
            rout = [{"to": graph.partners.get(did, {}).get("name"), "count": w}
                    for did, w in graph.referral_outgoing(pid)]
            rin = [{"from": graph.partners.get(sid, {}).get("name"), "count": w}
                   for sid, w in graph.referral_incoming(pid)]
            dg = graph.degree_centrality().get(pid, 0)
            bt = graph.betweenness_centrality().get(pid, 0)
            out = json.dumps({
                "partner": partner, "connections": graph.total_connections(pid),
                "degree_centrality": round(dg, 3), "betweenness_centrality": round(bt, 3),
                "co_sell_partners": cs, "referrals_given": rout, "referrals_received": rin,
            }, indent=2)
            return [types.TextContent(type="text", text=out)]

        elif name == "calculate_synergy":
            pa = graph.get_partner(arguments["partner_a"])
            pb = graph.get_partner(arguments["partner_b"])
            if not pa or not pb:
                return [types.TextContent(type="text", text="One or both partners not found.")]
            score, reasons = graph.synergy_score(pa["id"], pb["id"])
            out = json.dumps({
                "partner_a": pa["name"], "partner_b": pb["name"],
                "synergy_score": round(score, 1), "breakdown": reasons,
            }, indent=2)
            return [types.TextContent(type="text", text=out)]

        elif name == "get_top_influencers":
            limit = arguments.get("limit", 5)
            dg = graph.degree_centrality()
            bt = graph.betweenness_centrality()
            infs = []
            for pid, partner in graph.partners.items():
                sc = (dg.get(pid, 0) * 40 + bt.get(pid, 0) * 40 +
                      min(partner.get("deals_last_quarter", 0) / 25, 1) * 10 +
                      min(partner.get("annual_revenue", 0) / 1200000, 1) * 10)
                infs.append({
                    "name": partner["name"], "tier": partner["tier"],
                    "influence_score": round(min(sc * 10, 100), 1),
                    "connections": graph.total_connections(pid),
                    "degree_centrality": round(dg.get(pid, 0), 3),
                    "betweenness": round(bt.get(pid, 0), 3),
                })
            infs.sort(key=lambda x: -x["influence_score"])
            return [types.TextContent(type="text", text=json.dumps(infs[:limit], indent=2))]

        elif name == "detect_clusters":
            cls = graph.detect_clusters()
            result = []
            for i, cluster in enumerate(cls, 1):
                pi = [graph.partners[pid] for pid in cluster if pid in graph.partners]
                tr = sum(p.get("annual_revenue", 0) for p in pi)
                result.append({
                    "cluster_id": i, "partner_count": len(cluster),
                    "partners": [p["name"] for p in pi], "total_revenue": tr,
                })
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_coverage_gaps":
            return [types.TextContent(type="text", text=json.dumps(graph.coverage_gaps(), indent=2))]

        elif name == "get_pairing_recommendations":
            limit = arguments.get("limit", 8)
            pids = list(graph.partners.keys())
            pairs = []
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    a, b = pids[i], pids[j]
                    if graph.cosell.get(a, {}).get(b, 0) == 0:
                        score, reasons = graph.synergy_score(a, b)
                        pairs.append({
                            "partner_a": graph.partners[a]["name"],
                            "partner_b": graph.partners[b]["name"],
                            "synergy_score": round(score, 1),
                            "top_reasons": reasons[:3],
                        })
            pairs.sort(key=lambda x: -x["synergy_score"])
            return [types.TextContent(type="text", text=json.dumps(pairs[:limit], indent=2))]

        elif name == "get_network_metrics":
            dg = graph.degree_centrality()
            bt = graph.betweenness_centrality()
            metrics = [{
                "name": p["name"], "tier": p["tier"],
                "connections": graph.total_connections(pid),
                "degree_centrality": round(dg.get(pid, 0), 3),
                "betweenness_centrality": round(bt.get(pid, 0), 3),
            } for pid, p in graph.partners.items()]
            return [types.TextContent(type="text", text=json.dumps(metrics, indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    async def run():
        async with mcp.server.stdio.stdio_server() as (rs, ws):
            await server.run(rs, ws, InitializationOptions(
                server_name="synapse", server_version="0.1.0",
            ))

    import asyncio
    asyncio.run(run())


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "demo":
        cmd_demo()
    elif cmd == "graph":
        g = load_ecosystem()
        if g:
            cmd_graph(g)
        else:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
    elif cmd == "metrics":
        g = load_ecosystem()
        if g:
            cmd_metrics(g)
        else:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
    elif cmd == "clusters":
        g = load_ecosystem()
        if g:
            cmd_clusters(g)
        else:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
    elif cmd == "gaps":
        g = load_ecosystem()
        if g:
            cmd_gaps(g)
        else:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
    elif cmd == "recommend":
        g = load_ecosystem()
        if g:
            cmd_recommend(g)
        else:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
    elif cmd == "pair":
        if len(args) < 3:
            print("  Usage: synapse.py pair --p1 <name> --p2 <name>")
            return
        p1 = p2 = None
        for i in range(1, len(args), 2):
            if args[i] in ("--p1", "-1") and i + 1 < len(args):
                p1 = args[i + 1]
            elif args[i] in ("--p2", "-2") and i + 1 < len(args):
                p2 = args[i + 1]
        if not p1 or not p2:
            print("  Usage: synapse.py pair --p1 <name> --p2 <name>")
            return
        g = load_ecosystem()
        if g:
            cmd_pair(g, p1, p2)
        else:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
    elif cmd == "partner":
        if len(args) < 2:
            print("  Usage: synapse.py partner <name>")
            return
        g = load_ecosystem()
        if g:
            cmd_partner(g, args[1])
        else:
            print("  No ecosystem data. Run 'synapse.py demo' first.")
    elif cmd == "dashboard":
        cmd_dashboard()
    elif cmd == "serve":
        cmd_serve()
    else:
        print(f"  Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()