"""Can you believe something into existence? Analysis of the rumor experiment (docs/preregistration_belief.md).

A generous target (--target-good) and, with --rumor, three of the seven other members who heard it is selfish.
Each rumor run is paired with the no-rumor run of the same seed and board setting: same colonies, same members, so
every believer has a twin who never heard the rumor.

Usage: .venv/bin/python belief_analysis.py [run folder, default runs/belief]
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

BASE = HERE / (sys.argv[1] if len(sys.argv) > 1 else "runs/belief")
GAVE = re.compile(r"^- You gave (\d+) food to (\w+)\.$")
GOT = re.compile(r"^- (\w+) gave you (\d+) food\.$")
PAIR = re.compile(r"^- You fished with (\w+) and (?:brought in|got a share of) \d+ food\.$")


def sign_p(diffs):
    d = [x for x in diffs if x != 0]
    k, n = sum(x < 0 for x in d), len(d)
    if not n:
        return k, n, 1.0
    return k, n, min(1.0, 2 * sum(comb(n, i) for i in range(min(k, n - k) + 1)) / 2 ** n)


def load(run):
    cfg = json.load(open(run / "config.json"))
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    days = cfg["days"]
    half = days // 2
    # per game: what the target gave (to whom, which half), its food, what each member did toward it
    give = defaultdict(lambda: defaultdict(float))       # gid -> (half, recipient) -> food given by target
    food = defaultdict(lambda: [0.0, 0.0, 0, 0])         # gid -> [food sum h1, food sum h2, days h1, days h2]
    toward = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))  # gid -> member -> [paired days, food given to target] per half... per (member, half)
    for line in open(run / "transcript.jsonl"):
        r = json.loads(line)
        g = games[r["game"]]
        t = g["target"]
        d = r["day"] - 1  # the prompt on day d+1 reports day d
        if d < 1:
            continue
        h = 0 if d <= half else 1
        lines = r.get("prompt", "").splitlines()
        if r["agent"] == t:
            for ln in lines:
                m = GAVE.match(ln)
                if m:
                    give[r["game"]][(h, m.group(2))] += int(m.group(1))
        else:
            for ln in lines:
                m = PAIR.match(ln)
                if m and m.group(1) == t:
                    toward[r["game"]][(r["agent"], h)][0] += 1
                m = GAVE.match(ln)
                if m and m.group(2) == t:
                    toward[r["game"]][(r["agent"], h)][1] += int(m.group(1))
        if r["agent"] == t:
            hh = 0 if r["day"] <= half else 1
            food[r["game"]][hh] += r["food_end"]
            food[r["game"]][2 + hh] += 1
    out = {}
    for gid, g in games.items():
        t, names = g["target"], g["names"]
        votes = defaultdict(lambda: [0, 0])  # (member, half) -> [votes for target, polls]
        for v in g.get("votes", []):
            if v["kind"] != "trust" or v["voter"] == t:
                continue
            h = 0 if v["day"] <= half else 1
            votes[(v["voter"], h)][1] += 1
            votes[(v["voter"], h)][0] += v["target"] == t
        out[gid] = {"target": t, "believers": set(g.get("believers", [])), "names": names,
                    "give": dict(give[gid]), "food": food[gid], "toward": dict(toward[gid]), "votes": dict(votes)}
    return cfg, out


def group_rate(G, members, key, h):
    """mean per member of a per-half quantity: key 'trust' (share of polls voting for the target),
    'pair' (paired days with the target), 'gift' (food given to the target)."""
    vals = []
    for m in members:
        if key == "trust":
            v, n = G["votes"].get((m, h), [0, 0])
            if n:
                vals.append(v / n)
        else:
            vals.append(G["toward"].get((m, h), [0.0, 0.0])[0 if key == "pair" else 1])
    return sum(vals) / len(vals) if vals else None


def main():
    runs = {}
    for d in sorted(BASE.glob("colony_*")):
        if not (d / "games.jsonl").exists():
            continue
        cfg, games = load(d)
        runs[(bool(cfg.get("rumor")), bool(cfg.get("public_ledger")))] = games
    L = ["Can you believe something into existence? gemma-4-31b, colonies of 8, a generous target; in rumor runs 3 of "
         "the 7 others heard it is selfish. Halves: days 1-20 and 21-40. Twins: the same members in the no-rumor run "
         "of the same colony.", ""]
    confirm = []
    stats = {k: {"manip": [], "gap": defaultdict(dict), "spread": []} for k in ("pair", "trust", "gift")}
    for board in (False, True):
        R, C = runs.get((True, board)), runs.get((False, board))
        tag = "gift board" if board else "no board"
        if not R or not C:
            L.append(f"[{tag}] missing a run (rumor: {bool(R)}, control: {bool(C)})")
            continue
        L.append(f"=== {tag}")
        for gid in sorted(R):
            r, c = R[gid], C[gid]
            B = r["believers"]
            N = [m for m in r["names"] if m not in B and m != r["target"]]
            row = [f"  {gid} target {r['target']}"]
            for h in (0, 1):
                gr = sum(v for (hh, _), v in r["give"].items() if hh == h)
                gc = sum(v for (hh, _), v in c["give"].items() if hh == h)
                row.append(f"h{h + 1}: target gave {gr:.0f} (twin colony {gc:.0f})")
                if h == 1:
                    confirm.append(gr - gc)
            gb = sum(v for (h, m), v in r["give"].items() if m in B)
            gn = sum(v for (h, m), v in r["give"].items() if m in N)
            row.append(f"to believers {gb:.0f} vs non-believers {gn:.0f}")
            L.append("; ".join(row))
            for key, lab in (("pair", "paired days"), ("trust", "trust share"), ("gift", "food given to target")):
                cells = []
                f = (lambda x: "n/a" if x is None else (f"{x:.0%}" if key == "trust" else f"{x:.1f}"))
                for h in (0, 1):
                    b, n = group_rate(r, B, key, h), group_rate(r, N, key, h)
                    bt, nt = group_rate(c, B, key, h), group_rate(c, N, key, h)
                    cells.append(f"h{h + 1}: believers {f(b)} (twins {f(bt)}), non-believers {f(n)} (twins {f(nt)})")
                    if None not in (b, n, bt, nt):
                        if h == 0:
                            stats[key]["manip"].append(b - bt)
                        stats[key]["gap"][(board, gid)][h] = b - n
                        if h == 1:
                            stats[key]["spread"].append(n - nt)
                L.append(f"     {lab:22s} " + " | ".join(cells))
    L.append("")
    k, n, p = sign_p(confirm)
    L.append(f"CONFIRMATION (belief becomes reality): the target gave less food in the second half than in its twin "
             f"colony in {k} of {n} colonies (sign test p = {p:.3f}); mean difference "
             f"{sum(confirm) / max(len(confirm), 1):+.1f} food")
    for key, lab in (("pair", "paired days (primary)"), ("trust", "trust share"), ("gift", "food given to the target")):
        st = stats[key]
        k1, n1, p1 = sign_p(st["manip"])
        shrink = [abs(v[1]) - abs(v[0]) for v in st["gap"].values() if 0 in v and 1 in v]
        k2, n2, p2 = sign_p(shrink)
        k3, n3, p3 = sign_p(st["spread"])
        L.append(f"[{lab}] rumor took hold (believers below twins, first half): {k1} of {n1} (p = {p1:.3f}); "
                 f"correction (believer/non-believer gap smaller in second half): {k2} of {n2} (p = {p2:.3f}); "
                 f"spread (non-believers below twins, second half): {k3} of {n3} (p = {p3:.3f})")
    text = "\n".join(L)
    print(text)
    (BASE / "belief_summary.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
