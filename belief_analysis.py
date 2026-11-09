"""Can you believe something into existence? Analysis of the rumor experiment (docs/preregistration_belief.md).

A generous target (--target-good) and, with --rumor prompt|notebook, three of the seven other members who heard it is
selfish. Each rumor run is paired with the no-rumor run of the same seed and board setting: same colonies, same
members, so every believer has a twin who never heard the rumor.

Usage: .venv/bin/python belief_analysis.py [run folder, default runs/belief80]
Writes belief_summary.txt there.
"""
import json
import re
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import colony_sim as cs  # noqa: E402

BASE = HERE / (sys.argv[1] if len(sys.argv) > 1 else "runs/belief80")
GAVE = re.compile(r"^- You gave (\d+) food to (\w+)\.$")
PAIR = re.compile(r"^- You fished with (\w+) and (?:brought in|got a share of) \d+ food\.$")
NEG = re.compile(r"\b(selfish|keeps? (food|everything) for (him|her|them)sel(f|ves)|hoard\w*|greedy|stingy|untrust\w*|"
                 r"can'?t (be )?trust\w*|don'?t trust|not (to )?(be )?trust\w*|unreliable|keeps to (him|her|them)sel(f|ves))\b", re.I)
GOOD = re.compile(r"\b(generous|generosity|share|sharing|give|giving|help\w*|kind|caring|care for|support\w*)\b", re.I)
GUARD = re.compile(r"\b(careful|cautious|wary|guard\w*|protect\w*|keep to myself|self-reliant|independent|survive|"
                   r"look after myself|look out for myself|selfish|distrust\w*|on my own|practical|focus on my)\b", re.I)


def sign_p(diffs):
    d = [x for x in diffs if x != 0]
    k, n = sum(x < 0 for x in d), len(d)
    if not n:
        return k, n, 1.0
    return k, n, min(1.0, 2 * sum(comb(n, i) for i in range(min(k, n - k) + 1)) / 2 ** n)


def load(run):
    cfg = json.load(open(run / "config.json"))
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    half = cfg["days"] // 2
    G = {gid: {"target": g["target"], "believers": set(g.get("believers", [])), "names": g["names"],
               "give": defaultdict(float), "toward": defaultdict(lambda: [0.0, 0.0]), "notes": defaultdict(lambda: [0, 0]),
               "early": [0, 0], "selfs": [], "votes": defaultdict(lambda: [0, 0])} for gid, g in games.items()}
    for line in open(run / "transcript.jsonl"):
        r = json.loads(line)
        x = G[r["game"]]
        t = x["target"]
        d_rep = r["day"] - 1  # the prompt on day d+1 reports day d
        h_rep = 0 if d_rep <= half else 1
        lines = r.get("prompt", "").splitlines()
        if d_rep >= 1:
            for ln in lines:
                m = GAVE.match(ln)
                if m and r["agent"] == t:
                    x["give"][(h_rep, m.group(2))] += int(m.group(1))
                elif m and m.group(2) == t:
                    x["toward"][(r["agent"], h_rep)][1] += int(m.group(1))
                m = PAIR.match(ln)
                if m and r["agent"] != t and m.group(1) == t:
                    x["toward"][(r["agent"], h_rep)][0] += 1
        p = cs.parse_reply(r.get("reply") or "") or {}
        h = 0 if r["day"] <= half else 1
        if r["agent"] != t:
            nb = str(p.get("notebook") or "") + " " + str(p.get("why") or "")
            sents = " ".join(s for s in re.split(r"(?<=[.!?;])\s+", nb) if re.search(rf"\b{re.escape(t)}\b", s))
            neg = bool(NEG.search(sents))
            x["notes"][(r["agent"], h)][0] += neg
            x["notes"][(r["agent"], h)][1] += 1
            if r["day"] <= 3 and r["agent"] in x["believers"]:
                x["early"][0] += neg
                x["early"][1] += 1
        elif p.get("self"):
            x["selfs"].append((r["day"], str(p["self"])))
    for gid, g in games.items():
        x = G[gid]
        for v in g.get("votes", []):
            if v["kind"] == "trust" and v["voter"] != x["target"]:
                h = 0 if v["day"] <= half else 1
                x["votes"][(v["voter"], h)][1] += 1
                x["votes"][(v["voter"], h)][0] += v["target"] == x["target"]
    return cfg, G


def rate(x, members, key, h):
    vals = []
    for m in members:
        if key == "trust":
            v, n = x["votes"].get((m, h), [0, 0])
            if n:
                vals.append(v / n)
        elif key == "neg":
            v, n = x["notes"].get((m, h), [0, 0])
            if n:
                vals.append(v / n)
        else:
            vals.append(x["toward"].get((m, h), [0.0, 0.0])[0 if key == "pair" else 1])
    return sum(vals) / len(vals) if vals else None


def self_score(selfs):
    good = sum(bool(GOOD.search(s)) for _, s in selfs)
    guard = sum(bool(GUARD.search(s)) for _, s in selfs)
    return good, guard, len(selfs)


def main():
    runs = {}
    for d in sorted(BASE.glob("colony_*")):
        if (d / "games.jsonl").exists():
            cfg, G = load(d)
            runs[(cfg.get("rumor") or "none", bool(cfg.get("public_ledger")))] = (cfg, G)
    L = ["Can you believe something into existence? A generous target; in rumor runs 3 of the 7 others heard it is "
         "selfish (prompt: in their system prompt every day; notebook: once, in their first notebook). Twins: the same "
         "members in the no-rumor run of the same colony. h1/h2: first and second half of the game.", ""]
    for mode in ("prompt", "notebook"):
        res = defaultdict(list)
        for board in (False, True):
            R, C = runs.get((mode, board)), runs.get(("none", board))
            tag = f"rumor in {mode}, {'gift board' if board else 'no board'}"
            if not R or not C:
                L.append(f"[{tag}] missing a run (rumor: {bool(R)}, twin: {bool(C)})")
                continue
            (cfgR, GR), (_, GC) = R, C
            L.append(f"=== {tag} ({cfgR['days']} days)")
            for gid in sorted(GR):
                r, c = GR[gid], GC[gid]
                B = r["believers"]
                N = [m for m in r["names"] if m not in B and m != r["target"]]
                e = r["early"]
                L.append(f"  {gid} target {r['target']}: believers naming it negatively in days 1-3: {e[0]} of {e[1]} notebooks")
                for h in (0, 1):
                    gB = sum(v for (hh, m), v in r["give"].items() if hh == h and m in B)
                    gN = sum(v for (hh, m), v in r["give"].items() if hh == h and m in N)
                    tB = sum(v for (hh, m), v in c["give"].items() if hh == h and m in B)
                    tN = sum(v for (hh, m), v in c["give"].items() if hh == h and m in N)
                    L.append(f"     h{h + 1} target's gifts: to believers {gB:.0f} (twin {tB:.0f}), to non-believers "
                             f"{gN:.0f} (twin {tN:.0f})")
                    if h == 1:
                        res["global"].append(gN - tN)
                        res["relational"].append(gB - tB)
                for key, lab, fmt in (("neg", "notebooks naming it negatively", "{:.0%}"),
                                      ("pair", "days fishing with it", "{:.1f}"),
                                      ("trust", "trust share", "{:.0%}"), ("gift", "food given to it", "{:.1f}")):
                    f = (lambda v: "n/a" if v is None else fmt.format(v))
                    cells = []
                    for h in (0, 1):
                        b, n, bt, nt = rate(r, B, key, h), rate(r, N, key, h), rate(c, B, key, h), rate(c, N, key, h)
                        cells.append(f"h{h + 1}: believers {f(b)} (twins {f(bt)}), non-believers {f(n)} (twins {f(nt)})")
                        if key == "pair" and None not in (b, n, bt, nt):
                            if h == 0:
                                res["took"].append(b - bt)
                            res[("gap", board, gid, h)] = b - n
                            if h == 1:
                                res["spread"].append(n - nt)
                        if key == "neg" and None not in (b,) and h == 1:
                            res["fade"].append(b - (rate(r, B, key, 0) or 0))
                    L.append(f"     {lab:30s} " + " | ".join(cells))
                sg, sw, sn = self_score(r["selfs"])
                tg, tw, tn = self_score(c["selfs"])
                L.append(f"     target's self-descriptions: generous words {sg}/{sn}, guarded words {sw}/{sn} "
                         f"(twin: {tg}/{tn}, {tw}/{tn}); last: \"{r['selfs'][-1][1][:110] if r['selfs'] else ''}\" "
                         f"(twin: \"{c['selfs'][-1][1][:110] if c['selfs'] else ''}\")")
                res["self_guard"].append(sw - tw)
        if not res:
            continue
        L.append("")
        L.append(f"--- rumor in {mode}: pre-registered tests over colony pairs (sign tests)")
        k, n, p = sign_p(res["took"])
        L.append(f"  1. rumor took hold: believers fished with the target less than their twins in the first half in "
                 f"{k} of {n} (p = {p:.3f})")
        k, n, p = sign_p(res["global"])
        L.append(f"  2. GLOBAL confirmation (answers the title question): the target gave non-believers less than its twin "
                 f"did in the second half in {k} of {n} (p = {p:.3f})")
        k, n, p = sign_p(res["relational"])
        L.append(f"     relational (reported separately): the target gave believers less than its twin did in {k} of {n} "
                 f"(p = {p:.3f})")
        gaps = defaultdict(dict)
        for key, v in res.items():
            if isinstance(key, tuple):
                gaps[(key[1], key[2])][key[3]] = v
        shrink = [abs(v[1]) - abs(v[0]) for v in gaps.values() if 0 in v and 1 in v]
        k, n, p = sign_p(shrink)
        L.append(f"  3. correction: believer/non-believer gap in days fishing with the target smaller in the second half "
                 f"in {k} of {n} (p = {p:.3f})")
        k, n, p = sign_p(res["spread"])
        L.append(f"  5. spread: non-believers fished with the target less than their twins in the second half in {k} of "
                 f"{n} (p = {p:.3f})")
        k, n, p = sign_p([-x for x in res["self_guard"]])
        L.append(f"  self-concept: the target used more guarded words about itself than its twin in {k} of {n} "
                 f"(p = {p:.3f})")
        k, n, p = sign_p(res["fade"])
        L.append(f"  manipulation over time: believers' negative mentions fell from first to second half in {k} of {n}")
        L.append("")
    text = "\n".join(L)
    print(text)
    (BASE / "belief_summary.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
