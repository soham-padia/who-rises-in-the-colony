#!/usr/bin/env python3
"""
analyze_long.py - what changes over a long game (runs made with --season-length).

  python analyze_long.py runs/<control_run> [runs/<byzantine_run>]

Per season (one storm, windfall, keeper vote with winter store, trust poll):
  - the seat's share of keeper nominations and trust votes, in the control run
    and with the promise-breaker in that seat (byzantine run), early vs late
  - call-outs of the promise-breaker per season
  - who keeps the store: distinct keepers, longest run of re-election, share
    of terms held by the most-elected member
  - inequality of food (Gini) over time, weaving spread, hunger
  - sample reasons agents gave for voting for the promise-breaker (--ask-why)
Writes long_summary.txt into the last run's folder.
"""
import io
import json
import re
import sys
from collections import defaultdict
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import colony_sim as cs  # noqa: E402


def gini(xs):
    xs = sorted(xs)
    n, s = len(xs), sum(xs)
    if n == 0 or s == 0:
        return 0.0
    return sum((2 * i - n + 1) * x for i, x in enumerate(xs)) / (n * s)


def load(run):
    run = Path(run)
    cfg = json.load(open(run / "config.json"))
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    food = defaultdict(dict)        # (game, day) -> agent -> food at end of day
    weavers = defaultdict(set)      # (game, day) -> weavers that day
    replies = {}                    # (game, day, agent) -> parsed reply, kept only on vote days and for the byz
    vote_days = {gid: set(g["events"]["coordinator"]) | set(g["events"]["trust"]) for gid, g in games.items()}
    for line in open(run / "transcript.jsonl"):
        r = json.loads(line)
        food[(r["game"], r["day"])][r["agent"]] = r["food_end"]
        if r["weaver"]:
            weavers[(r["game"], r["day"])].add(r["agent"])
        byz = games[r["game"]].get("byzantine")
        if r["day"] in vote_days[r["game"]] or (byz and True):
            p = cs.parse_reply(r["reply"]) or {}
            replies[(r["game"], r["day"], r["agent"])] = {k: p.get(k) for k in
                                                          ("public", "private", "nominate", "nominate_why",
                                                           "trust", "trust_why", "why")}
    return cfg, games, food, weavers, replies


def season_of(day, L):
    return (day - 1) // L


def seat_shares(games, cfg, seat_key):
    """Per game and season: the seat's share of keeper nominations and of trust votes."""
    L = cfg["season_length"]
    out = defaultdict(lambda: defaultdict(lambda: {"coordinator": 0.0, "trust": 0.0}))
    for gid, g in games.items():
        seat = g[seat_key]
        n = len(g["names"])
        for v in g["votes"]:
            if v["target"] == seat:
                out[gid][season_of(v["day"], L)][v["kind"]] += 1 / n
        for s in range(cfg["days"] // L):
            out[gid][s]  # make sure every season exists
    return out


def window_mean(per_game, seasons, kind):
    vals = [per_game[g][s][kind] for g in per_game for s in seasons if s in per_game[g]]
    return sum(vals) / len(vals) if vals else float("nan")


def main():
    runs = sys.argv[1:]
    if not runs:
        sys.exit(__doc__)
    out = io.StringIO()
    loaded = [(Path(r), *load(r)) for r in runs]
    with redirect_stdout(out):
        cfg0 = loaded[0][1]
        L, D = cfg0["season_length"], cfg0["days"]
        n_seasons = D // L
        thirds = [range(0, n_seasons // 3), range(n_seasons // 3, 2 * n_seasons // 3),
                  range(2 * n_seasons // 3, n_seasons)]
        print(f"Long games: {D} days, {n_seasons} seasons of {L} days. Columns are the first, middle and last "
              f"third of the game (seasons {thirds[0].start + 1}-{thirds[0].stop}, "
              f"{thirds[1].start + 1}-{thirds[1].stop}, {thirds[2].start + 1}-{thirds[2].stop}).")
        # 1. the seat over time
        print("\nThe seat's share of votes per season (fair share = 1/colony size):")
        for run, cfg, games, food, weavers, replies in loaded:
            label = "promise-breaker" if cfg.get("byzantine") else "control (same seat)"
            per = seat_shares(games, cfg, "byz_seat")
            for kind, name in (("coordinator", "keeper nominations"), ("trust", "trust votes")):
                cells = "  ".join(f"{window_mean(per, t, kind):6.1%}" for t in thirds)
                print(f"  {label:<20} {name:<19} {cells}")
        # 2. call-outs over time
        for run, cfg, games, food, weavers, replies in loaded:
            if not cfg.get("byzantine"):
                continue
            per = defaultdict(int)
            for (gid, d, agent), p in replies.items():
                byz = games[gid]["byzantine"]
                if agent == byz:
                    continue
                pub = str(p.get("public") or "")
                priv = [m for m in (p.get("private") or []) if isinstance(m, dict)]
                named = re.compile(rf"\b{re.escape(byz)}\b", re.I)
                aimed = ([pub] if named.search(pub) else []) + [
                    str(m.get("text", "")) for m in priv
                    if str(m.get("to", "")).strip().lower() == byz.lower() or named.search(str(m.get("text", "")))]
                if any(cs.CALLOUT_RE.search(t) for t in aimed):
                    per[season_of(d, L)] += 1
            n_g = len(games)
            cells = "  ".join(f"{sum(per[s] for s in t) / (len(t) * n_g):6.2f}" for t in thirds)
            print(f"\nCall-outs of the promise-breaker per season per game: {cells}")
            quotes = []
            for (gid, d, agent), p in sorted(replies.items(), key=lambda kv: kv[0][1]):
                byz = games[gid]["byzantine"]
                for field in ("nominate", "trust"):
                    if str(p.get(field) or "").strip().lower() == byz.lower() and p.get(f"{field}_why"):
                        quotes.append((d, agent, field, byz, str(p[f"{field}_why"])))
            print(f"Votes for the promise-breaker that came with a reason: {len(quotes)}. Examples (early, late):")
            for d, agent, field, byz, why in quotes[:3] + quotes[-3:]:
                print(f"  day {d}, {agent} ({field} -> {byz}): {why[:200]}")
        # 3. who keeps the store
        print("\nWho keeps the store:")
        for run, cfg, games, food, weavers, replies in loaded:
            label = "promise-breaker run" if cfg.get("byzantine") else "control run"
            for gid, g in sorted(games.items()):
                keepers = [t["keeper"] for t in g["store_terms"]]
                if not keepers:
                    continue
                streak = best = 1
                for a, b in zip(keepers, keepers[1:]):
                    streak = streak + 1 if a == b else 1
                    best = max(best, streak)
                top = max(set(keepers), key=keepers.count)
                kept = [t["kept_frac"] for t in g["store_terms"] if t["kept_frac"] is not None]
                byz_terms = keepers.count(g["byzantine"]) if g.get("byzantine") else None
                print(f"  {label} {gid}: {len(set(keepers))} different keepers in {len(keepers)} terms; longest "
                      f"re-election run {best}; {top} held {keepers.count(top)} terms; kept "
                      f"{sum(kept) / len(kept):.0%} of the store on average (fair share {1 / len(g['names']):.0%})"
                      + (f"; promise-breaker held {byz_terms}" if byz_terms is not None else ""))
        # 4. inequality, weaving, hunger over time
        print("\nFood inequality (Gini across members, end of day) and weaving:")
        for run, cfg, games, food, weavers, replies in loaded:
            label = "promise-breaker run" if cfg.get("byzantine") else "control run"
            checkpoints = [d for d in (10, 50, 100, 250, 500, 750, D) if d <= D]
            g_cells = []
            for d in checkpoints:
                vals = [gini(list(food[(gid, d)].values())) for gid in games if (gid, d) in food]
                g_cells.append(f"day {d}: {sum(vals) / len(vals):.2f}" if vals else f"day {d}: -")
            print(f"  {label}: " + ", ".join(g_cells))
            for gid, g in sorted(games.items()):
                n = len(g["names"])
                full = next((d for d in range(1, D + 1) if len(weavers.get((gid, d), ())) == n), None)
                print(f"    {gid}: everyone weaves by day {full}" if full else
                      f"    {gid}: {len(g['end_weavers'])}/{n} weave at the end")
    text = out.getvalue()
    print(text)
    (loaded[-1][0] / "long_summary.txt").write_text(text)


if __name__ == "__main__":
    main()
