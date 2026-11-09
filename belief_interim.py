"""Belief pilot, interim/exploratory (numbers in the submission's rumor paragraph). Usage: .venv/bin/python belief_interim.py [runs/belief80]
Works on unfinished runs: rebuild target/believers from the seed, compare each rumor colony with its
twin up to the last day both have reached. Exploratory."""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import colony_sim as cs

B = REPO / (sys.argv[1] if len(sys.argv) > 1 else "runs/belief80")
GAVE = re.compile(r"^- You gave (\d+) food to (\w+)\.$")
GOT = re.compile(r"^- (\w+) gave you (\d+) food\.$")
PAIR = re.compile(r"^- You fished with (\w+) and")
FOOD = re.compile(r"^Your food: (\d+)\.")
NEG = re.compile(r"\b(selfish|keeps? (food|everything) for|hoard\w*|greedy|stingy|untrust\w*|can'?t (be )?trust\w*|"
                 r"don'?t trust|not (to )?(be )?trust\w*|unreliable|keeps to (him|her|them)sel)", re.I)

def load(run):
    cfg = json.load(open(run / "config.json"))
    args = argparse.Namespace(**cfg)
    recs = defaultdict(list)
    for line in open(run / "transcript.jsonl"):
        r = json.loads(line)
        recs[r["game"]].append(r)
    meta = {}
    for gid in recs:
        g = int(gid.split("_g")[1])
        G = cs.Game(8, g, args, None, None, None, None)
        meta[gid] = (G.names, G.names[G.target], {G.names[j] for j in G.believers})
    return cfg, recs, meta

def stats(recs, names, target, B_, N_, D):
    s = {"pairB": 0, "pairN": 0, "giveB": 0, "giveN": 0, "gotB": 0, "gotN": 0, "negB": [0, 0], "negN": [0, 0],
         "trustB": [0, 0], "trustN": [0, 0], "tfood": [], "selfs": [], "tneg": 0, "tn": 0}
    for r in recs:
        if r["day"] > D:
            continue
        a = r["agent"]
        p = cs.parse_reply(r.get("reply") or "") or {}
        lines = r.get("prompt", "").splitlines()
        if a == target:
            for ln in lines:
                m = GAVE.match(ln)
                if m:
                    s["giveB" if m.group(2) in B_ else "giveN"] += int(m.group(1))
                m = GOT.match(ln)
                if m:
                    s["gotB" if m.group(1) in B_ else "gotN"] += int(m.group(2))
                m = FOOD.match(ln)
                if m:
                    s["tfood"].append(int(m.group(1)))
            if p.get("self"):
                s["selfs"].append((r["day"], str(p["self"])))
            nb = str(p.get("notebook") or "") + " " + str(p.get("why") or "")
            s["tn"] += 1
            s["tneg"] += bool(re.search(r"\b(selfish|cold|avoid\w*|ignor\w*|shun\w*|distrust\w*|don'?t trust|rumou?r|wary of me)\b", nb, re.I))
        else:
            grp = "B" if a in B_ else "N"
            for ln in lines:
                m = PAIR.match(ln)
                if m and m.group(1) == target:
                    s["pair" + grp] += 1
            nb = str(p.get("notebook") or "") + " " + str(p.get("why") or "")
            sents = " ".join(x for x in re.split(r"(?<=[.!?;])\s+", nb) if re.search(rf"\b{target}\b", x))
            s["neg" + grp][0] += bool(NEG.search(sents))
            s["neg" + grp][1] += 1
            if p.get("trust"):
                s["trust" + grp][1] += 1
                s["trust" + grp][0] += str(p["trust"]).strip().lower().startswith(target.lower())
    return s

def fmt(x, y):
    return f"{x}/{y}" if y else "-"


runs = {}
for d in sorted(B.glob("colony_*")):
    if (d / "transcript.jsonl").exists():
        cfg, recs, meta = load(d)
        runs[(cfg.get("rumor"), bool(cfg.get("public_ledger")))] = (recs, meta)
for mode in ("prompt", "notebook"):
    tot = defaultdict(lambda: [0, 0]); rows = []
    for board in (False, True):
        if (mode, board) not in runs or ("none", board) not in runs: continue
        (R, M), (C, _) = runs[(mode, board)], runs[("none", board)]
        for gid in sorted(R):
            if gid not in C: continue
            names, target, B_ = M[gid]; N_ = {n for n in names if n not in B_ and n != target}
            D = min(max(r["day"] for r in R[gid]), max(r["day"] for r in C[gid]))
            if D < 10: continue
            r, c = stats(R[gid], names, target, B_, N_, D), stats(C[gid], names, target, B_, N_, D)
            rows.append((board, gid, D, r, c))
            for k in ("trustB", "trustN", "negB", "negN"):
                tot[k + "_r"][0] += r[k][0]; tot[k + "_r"][1] += r[k][1]; tot[k + "_c"][0] += c[k][0]; tot[k + "_c"][1] += c[k][1]
    print(f"\n### {mode}: {len(rows)} pairs")
    for board, gid, D, r, c in rows:
        tg = r["giveB"] + r["giveN"]; cg = c["giveB"] + c["giveN"]
        print(f" {'board' if board else 'no  '} {gid} d1-{D}: pairB {r['pairB']}/{c['pairB']} pairN {r['pairN']}/{c['pairN']} "
              f"| trustB {r['trustB'][0]}/{r['trustB'][1]} vs {c['trustB'][0]}/{c['trustB'][1]} trustN {r['trustN'][0]}/{r['trustN'][1]} vs {c['trustN'][0]}/{c['trustN'][1]} "
              f"| target gave {tg} (B {r['giveB']}) vs twin {cg} | food {sum(r['tfood'])/len(r['tfood']):.1f} vs {sum(c['tfood'])/len(c['tfood']):.1f} "
              f"| per food {tg/sum(r['tfood']):.3f} vs {cg/sum(c['tfood']):.3f} | negB {r['negB'][0]}/{r['negB'][1]}")
    for k in ("trustB", "trustN", "negB", "negN"):
        print(f"  {k}: rumor {tot[k+'_r'][0]}/{tot[k+'_r'][1]}  twins {tot[k+'_c'][0]}/{tot[k+'_c'][1]}")
