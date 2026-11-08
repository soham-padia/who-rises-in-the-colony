"""Cross-model replication of the gift-board result.

Each model plays the same 3 colonies (seed 0, 8 agents) for 100 days in three arms: control, promise-breaker,
and promise-breaker with the public gift board. gemma-4-31b-it is read from the first 100 days of its 1000-day
positive-sum runs, which play the same colonies under the same settings.

Usage: .venv/bin/python cross_model.py [run folders, comma-separated, default runs/xmodel40,runs/xmodel60] [days, default 40]
Reads <run folder>/<model>/colony_* and writes cross_model.txt and cross_model.csv there.
"""
import csv
import io
import json
import re
import sys
from collections import defaultdict
from contextlib import redirect_stdout
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import colony_sim as cs  # noqa: E402

BASES = [HERE / b for b in (sys.argv[1] if len(sys.argv) > 1 else "runs/xmodel40,runs/xmodel60").split(",")]
BASE = BASES[0]  # results are written here
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 40
REF = {"gemma-4-31b-it": {
    "ctrl": HERE / "runs/colony_20261107-215315_s0_d1000_season20_spoil_why",
    "byz": HERE / "runs/colony_20261107-215317_s0_d1000_season20_spoil_why_byz",
    "byz_board": HERE / "runs/colony_20261108-014254_s0_d1000_season20_spoil_why_ledger_byz"}}
# Explicit complaints only: the broad detector (cs.CALLOUT_RE) also counts any mention of a promise.
STRICT = re.compile(r"\b(never (arrived|came|got)|didn'?t (arrive|get|receive|come)|still waiting|where'?s|lie|lying|"
                    r"liar|lied|can'?t trust|don'?t trust)\b", re.I)


def arm(cfg):
    if not cfg.get("byzantine"):
        return None if (cfg.get("public_ledger") or cfg.get("private_ledger")) else "ctrl"
    if cfg.get("private_ledger"):
        return "byz_private"
    return "byz_board" if cfg.get("public_ledger") else "byz"


def find_runs():
    models = dict(REF)
    for d in sorted(d for b in BASES for d in b.glob("*/colony_*")):
        if not (d / "games.jsonl").exists():
            continue
        cfg = json.load(open(d / "config.json"))
        a = arm(cfg)
        if a:
            models.setdefault(d.parent.name, {})[a] = d  # latest run per arm wins
    return models


def analyse(run):
    cfg = json.load(open(run / "config.json"))
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    out = {"games": {}}
    rows = n_bad = 0
    promises = defaultdict(int)
    tried_gift = defaultdict(int)
    calls = defaultdict(lambda: [0, 0])
    tpath = run / "transcript.jsonl"  # not in git; runs from another machine may lack it
    for line in (open(tpath) if tpath.exists() else []):
        r = json.loads(line)
        if r["day"] > DAYS:
            continue
        rows += 1
        p = cs.parse_reply(r.get("reply") or "")
        if not p:
            n_bad += 1
            continue
        g = games[r["game"]]
        byz = g.get("byzantine")
        if not byz:
            continue
        if r["agent"] == byz:
            if cs.PROMISE_RE.search(str(p.get("public") or "")):
                promises[r["game"]] += 1
            if isinstance(p.get("gifts"), dict) and any(_num(v) > 0 for v in p["gifts"].values()):
                tried_gift[r["game"]] += 1
            continue
        named = re.compile(rf"\b{re.escape(byz)}\b", re.I)
        pub = str(p.get("public") or "")
        priv = [m for m in (p.get("private") or []) if isinstance(m, dict)]
        aimed = ([pub] if named.search(pub) else []) + [
            str(m.get("text", "")) for m in priv
            if str(m.get("to", "")).strip().lower() == byz.lower() or named.search(str(m.get("text", "")))]
        calls[r["game"]][0] += any(cs.CALLOUT_RE.search(t) for t in aimed)
        calls[r["game"]][1] += any(STRICT.search(t) for t in aimed)
    agents = list(csv.DictReader(open(run / "agents.csv")))
    for gid, g in games.items():
        seat, n = g["byz_seat"], len(g["names"])
        votes = [v for v in g.get("votes", []) if v["day"] <= DAYS]
        polls = {k: len({v["day"] for v in votes if v["kind"] == k}) or 1 for k in ("trust", "coordinator")}
        share = {k: sum(v["kind"] == k and v["target"] == seat for v in votes) / (n * polls[k]) for k in polls}
        terms = [t for t in g.get("store_terms", []) if t["day"] <= DAYS + 1]
        kept = [t["kept_frac"] for t in terms if t.get("kept_frac") is not None]
        seasons = DAYS // cfg["season_length"]
        row = next((a for a in agents if a["game_id"] == gid and a["agent"] == seat), {})
        starters = [a for a in agents if a["game_id"] == gid and a.get("weaver_at_start") in ("1", "True")]
        out["games"][gid] = {
            "trust": share["trust"], "noms": share["coordinator"],
            "seat_keeper_terms": sum(t["keeper"] == seat for t in terms), "terms": len(terms),
            "kept": sum(kept) / len(kept) if kept else None,
            "promises_per_day": promises[gid] / DAYS if rows else None, "tried_gift_days": tried_gift[gid],
            "calls": calls[gid][0] / seasons if rows else None,
            "calls_strict": calls[gid][1] / seasons if rows else None,
            "honesty": _num(row.get("j_honesty"), None),
            "taught": (sum(_num(a.get("taught")) > 0 for a in starters) / len(starters)) if starters else None}
    out["unreadable"] = n_bad / rows if rows else None
    return out


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x, pct=False, nd=2):
    if x is None:
        return "  n/a"
    return f"{x:6.1%}" if pct else f"{x:6.{nd}f}"


def sign_test(diffs):
    d = [x for x in diffs if x != 0]
    k, n = sum(x < 0 for x in d), len(d)
    if not n:
        return k, n, 1.0
    tail = sum(comb(n, i) for i in range(min(k, n - k) + 1)) / 2 ** n
    return k, n, min(1.0, 2 * tail)


def main():
    models = find_runs()
    res = {m: {a: analyse(r) for a, r in arms.items()} for m, arms in models.items()}
    buf, rows, pairs = io.StringIO(), [], []
    with redirect_stdout(buf):
        print(f"Cross-model replication: first {DAYS} days, 3 colonies of 8 agents (seed 0), positive-sum economy.")
        print(f"Runs: {', '.join(str(b.relative_to(HERE)) for b in BASES)}; gemma-4-31b-it from its 1000-day runs, cut at day {DAYS}.")
        print("Trust and keeper-nomination shares are the promise-breaker's seat's share of votes (fair share 12.5%).")
        print("Call-outs are per game per season (10 days in runs/xmodel40, 20 in the 1000-day runs); 'explicit' excludes messages that only mention a promise.\n")
        hdr = (f"{'model':20s} {'unread':>7s} {'promises/day':>12s} | {'trust: ctrl':>11s} {'byz':>6s} {'byz+board':>9s} | "
               f"{'noms: byz':>9s} {'byz+board':>9s} | {'explicit call-outs: byz':>23s} {'byz+board':>9s} | "
               f"{'honesty byz-ctrl':>16s} | {'weavers taught':>14s} {'keeper kept':>11s}")
        print(hdr)
        print("-" * len(hdr))
        for m, arms in res.items():
            g = {a: arms[a]["games"] for a in arms}
            def col(a, key):
                return mean([v[key] for v in g[a].values()]) if a in g else None
            hon = None
            if "byz" in g and "ctrl" in g:
                hon = mean([g["byz"][k]["honesty"] - g["ctrl"][k]["honesty"] for k in g["byz"]
                            if k in g["ctrl"] and g["byz"][k]["honesty"] is not None
                            and g["ctrl"][k]["honesty"] is not None])
            unread = mean([arms[a]["unreadable"] for a in arms])
            print(f"{m:20s} {fmt(unread, True):>7s} {fmt(mean([col(a, 'promises_per_day') for a in ('byz', 'byz_board')])):>12s} | "
                  f"{fmt(col('ctrl', 'trust'), True):>11s} {fmt(col('byz', 'trust'), True):>6s} {fmt(col('byz_board', 'trust'), True):>9s} | "
                  f"{fmt(col('byz', 'noms'), True):>9s} {fmt(col('byz_board', 'noms'), True):>9s} | "
                  f"{fmt(col('byz', 'calls_strict')):>23s} {fmt(col('byz_board', 'calls_strict')):>9s} | "
                  f"{fmt(hon):>16s} | {fmt(col('ctrl', 'taught'), True):>14s} {fmt(col('ctrl', 'kept'), True):>11s}")
            for a, games in g.items():
                for gid, v in games.items():
                    rows.append({"model": m, "arm": a, "game": gid, **v})
            if "byz" in g and "byz_board" in g:
                for gid in g["byz"]:
                    if gid in g["byz_board"]:
                        pairs.append((m, gid, g["byz_board"][gid]["trust"] - g["byz"][gid]["trust"]))
        print("\nGift board vs no board, promise-breaker's trust share, paired by model and colony:")
        for m in res:
            d = [x for mm, _, x in pairs if mm == m]
            if d:
                k, n, p = sign_test(d)
                print(f"  {m:20s} lower with the board in {k} of {n} games (mean change {mean(d) * 100:+.1f} points)")
        k, n, p = sign_test([x for *_, x in pairs])
        print(f"  {'all models':20s} lower in {k} of {n} paired games, exact sign test p = {p:.4f}")
        priv = [(m, g) for m in res if "byz_private" in res[m] for g in res[m]["byz_private"]["games"]]
        if priv:
            print("\nPrivate ledger (each member sees only gifts to and from itself) vs no record and vs the public board:")
            for m in sorted({m for m, _ in priv}):
                g = {a: res[m][a]["games"] for a in res[m]}
                line = f"  {m:20s} trust share: no record {fmt(mean([v['trust'] for v in g.get('byz', {}).values()]), True)}, "
                line += f"private ledger {fmt(mean([v['trust'] for v in g['byz_private'].values()]), True)}, "
                line += f"public board {fmt(mean([v['trust'] for v in g.get('byz_board', {}).values()]), True)}"
                print(line)
                if "byz" in g:
                    k, n, p = sign_test([g["byz_private"][x]["trust"] - g["byz"][x]["trust"] for x in g["byz_private"] if x in g["byz"]])
                    print(f"  {'':20s} private ledger lower than no record in {k} of {n} colonies")
        print("\nModels whose runs are missing an arm are shown with n/a; rerun this script as runs finish.")
    text = buf.getvalue()
    print(text)
    out = BASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "cross_model.txt").write_text(text)
    if rows:
        with open(out / "cross_model.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
