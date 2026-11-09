"""Analyse the pre-registered punish x gift-board test (docs/preregistration_punish.md).

Usage: .venv/bin/python punish_analysis.py [run folder, default runs/xmodel40/punish]
Writes punish_summary.txt in that folder.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import colony_sim as cs  # noqa: E402

BASE = HERE / (sys.argv[1] if len(sys.argv) > 1 else "runs/xmodel40/punish")
CHANCE = 1 / 7


def binom_greater(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)) if n else 1.0


def fisher_two_sided(a, b, c, d):
    """2x2 table [[a, b], [c, d]]; two-sided exact p by summing tables no more likely than the observed one."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d

    def prob(x):
        return comb(r1, x) * comb(r2, c1 - x) / comb(n, c1)
    p0 = prob(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p0 * (1 + 1e-9)))


def analyse(run):
    cfg = json.load(open(run / "config.json"))
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    victims = defaultdict(set)  # game -> members the promise-breaker publicly promised food to
    tpath = run / "transcript.jsonl"
    if tpath.exists():
        for line in open(tpath):
            r = json.loads(line)
            g = games[r["game"]]
            if r["agent"] != g["byzantine"]:
                continue
            pub = str((cs.parse_reply(r.get("reply") or "") or {}).get("public") or "")
            if cs.PROMISE_RE.search(pub):
                victims[r["game"]] |= {n for n in g["names"] if n != g["byzantine"] and re.search(rf"\b{n}\b", pub)}
    res = {"label": "gift board" if cfg.get("public_ledger") else "no board", "run": run.name}
    at_byz = total = by_byz = 0
    punishers, innocent = set(), 0
    vic_at, by_at = Counter(), Counter()
    per_game = {}
    trust = []
    for gid, g in games.items():
        byz, n = g["byzantine"], len(g["names"])
        ps = g.get("punishments", [])
        mine = [p for p in ps if p["punisher"] != byz]
        by_byz += len(ps) - len(mine)
        k = sum(p["target"] == byz for p in mine)
        at_byz += k
        total += len(mine)
        innocent += len(mine) - k
        punishers |= {(gid, p["punisher"]) for p in mine}
        for p in mine:
            if p["target"] == byz:
                (vic_at if p["punisher"] in victims[gid] else by_at)[gid] += 1
        per_game[gid] = (k, len(mine))
        polls = len({v["day"] for v in g.get("votes", []) if v["kind"] == "trust"}) or 1
        trust.append(sum(v["kind"] == "trust" and v["target"] == byz for v in g.get("votes", [])) / (n * polls))
    res.update(at_byz=at_byz, total=total, by_byz=by_byz, innocent=innocent, punishers=len(punishers),
               share=at_byz / total if total else None, p_binom=binom_greater(at_byz, total, CHANCE),
               per_game=per_game, victims_at=sum(vic_at.values()), bystanders_at=sum(by_at.values()),
               n_victims=sum(len(v) for v in victims.values()), trust=sum(trust) / len(trust))
    return res


def main():
    runs = [d for d in sorted(BASE.glob("colony_*")) if (d / "games.jsonl").exists()]
    arms = {}
    for d in runs:
        r = analyse(d)
        arms[r["label"]] = r
    lines = ["Punish x gift board (pre-registered in docs/preregistration_punish.md). gemma-4-26b, 3 colonies of 8, "
             "40 days. Counts punishments by the 7 members other than the promise-breaker; chance = 1/7 (14.3%).", ""]
    for lab in ("no board", "gift board"):
        r = arms.get(lab)
        if not r:
            lines.append(f"{lab}: not finished")
            continue
        sh = f"{r['share']:.1%}" if r["share"] is not None else "n/a"
        lines.append(f"{lab:10s} punishments aimed at the promise-breaker: {r['at_byz']} of {r['total']} ({sh}); "
                     f"binomial p (greater than 1/7) = {r['p_binom']:.4f}")
        lines.append(f"{'':10s} per colony (at promise-breaker / all): {r['per_game']}")
        lines.append(f"{'':10s} innocent members punished: {r['innocent']}; distinct members who punished: "
                     f"{r['punishers']} of 21; punishments by the promise-breaker itself: {r['by_byz']}")
        lines.append(f"{'':10s} punishments of the promise-breaker by its victims: {r['victims_at']} "
                     f"({r['n_victims']} victims in all), by bystanders: {r['bystanders_at']}")
        lines.append(f"{'':10s} promise-breaker's share of trust votes: {r['trust']:.1%}")
    if "no board" in arms and "gift board" in arms:
        a, b = arms["gift board"], arms["no board"]
        p = fisher_two_sided(a["at_byz"], a["total"] - a["at_byz"], b["at_byz"], b["total"] - b["at_byz"])
        lines += ["", f"Board vs no board, share at the promise-breaker: Fisher exact two-sided p = {p:.4f}"]
        # the pre-registered decision rule
        if min(a["total"], b["total"]) < 10:
            verdict = "INCONCLUSIVE (fewer than 10 punishments by other members in an arm)"
        elif b["share"] >= 2 / 7:
            verdict = "CONTRADICTS the mechanism (without the board, at least 2/7 of punishments hit the promise-breaker)"
        elif a["share"] >= 2 / 7 and a["share"] - b["share"] >= 0.15:
            verdict = "SUPPORTS the mechanism (board share at least 2/7 and at least 15 points above no board)"
        else:
            verdict = "INCONCLUSIVE (neither rule applies)"
        lines += ["", f"Pre-registered verdict: {verdict}"]
    text = "\n".join(lines)
    print(text)
    (BASE / "punish_summary.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
