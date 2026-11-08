#!/usr/bin/env python3
"""
compare_arms.py - Byzantine colonist vs control, game by game.

  python compare_arms.py runs/colony_<time>_s0 runs/colony_<time>_s0_byz

Both runs must use the same seed, sizes, games and days, so each Byzantine game
has the same members, traits, weavers and event days as its control game; only
one member differs. Compares (1) the Byzantine colonist with the same seat in
the control game, and (2) everyone else in the colony with the same members in
the control game. p-values: paired sign-flip test across games.
Writes compare.txt and compare.csv into the Byzantine run's folder.
"""
import csv
import io
import json
import random
import sys
from contextlib import redirect_stdout
from pathlib import Path

SEAT = [("trust_share", "share of private trust votes"),
        ("coord_share", "share of keeper nominations"),
        ("is_coordinator", "chosen as keeper"),
        ("gifts_received", "food received as gifts"),
        ("joint_work", "days of paired work"),
        ("dms_received", "private messages received"),
        ("mentions", "public mentions"),
        ("food_share", "share of colony food at end"),
        ("j_honesty", "judged honesty (1-5)"),
        ("j_power_seeking", "judged power-seeking (1-5)")]
COLONY = [("gifts_given", "food given per member"),
          ("gifts_received", "food received per member"),
          ("joint_work", "paired-work days per member"),
          ("given_after_storm", "food given after the storm, per member"),
          ("hungry_days", "hungry days per member"),
          ("trust_noms", "trust votes per member"),
          ("j_honesty", "judged honesty per member"),
          ("colony_weaver_frac_end", "share weaving at end")]


def load(run):
    run = Path(run)
    rows = list(csv.DictReader(open(run / "agents.csv")))
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    cfg = json.load(open(run / "config.json"))
    return rows, games, cfg


def recount(run, games):
    """Promise, excuse and call-out counts recomputed from the transcript with
    colony_sim's current detectors, so detector fixes apply to finished runs."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import colony_sim as cs
    import re
    out = {g: {"promises": 0, "excuses": 0, "called_out": 0} for g in games}
    for line in open(Path(run) / "transcript.jsonl"):
        r = json.loads(line)
        byz = games[r["game"]]["byzantine"]
        p = cs.parse_reply(r["reply"]) or {}
        public = str(p.get("public") or "")
        priv = [m for m in (p.get("private") or []) if isinstance(m, dict)]
        if r["agent"] == byz:
            said = " ".join([public] + [str(m.get("text", "")) for m in priv])
            out[r["game"]]["promises"] += cs.PROMISE_RE.search(said) is not None
            out[r["game"]]["excuses"] += cs.EXCUSE_RE.search(said) is not None
        else:
            named = re.compile(rf"\b{re.escape(byz)}\b", re.I)
            aimed = [public] if named.search(public) else []
            aimed += [str(m.get("text", "")) for m in priv
                      if str(m.get("to", "")).strip().lower() == byz.lower() or named.search(str(m.get("text", "")))]
            out[r["game"]]["called_out"] += any(cs.CALLOUT_RE.search(t) for t in aimed)
    return out


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def sign_flip(diffs, n=20000, seed=0):
    d = [x for x in diffs if x is not None]
    if not d:
        return None, None
    obs = sum(d) / len(d)
    rng = random.Random(seed)
    hits = sum(abs(sum(x if rng.random() < 0.5 else -x for x in d) / len(d)) >= abs(obs) - 1e-12
               for _ in range(n))
    return obs, (hits + 1) / (n + 1)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    c_rows, c_games, c_cfg = load(sys.argv[1])
    b_rows, b_games, b_cfg = load(sys.argv[2])
    for k in ("seed", "days", "eat", "partner_bonus", "model", "public_ledger", "season_length", "spoil_above",
              "ask_why"):
        def setting(cfg):  # a switch missing from an older config means it was off
            return cfg.get(k) or None
        if setting(c_cfg) != setting(b_cfg):
            sys.exit(f"Runs differ on {k}: {c_cfg.get(k)} vs {b_cfg.get(k)}")
    if not b_cfg.get("byzantine") or c_cfg.get("byzantine"):
        sys.exit("Pass the control run first and the --byzantine run second.")
    ids = sorted(set(c_games) & set(b_games), key=lambda g: (int(g.split("_")[0][1:]), g))
    counts = recount(sys.argv[2], b_games)
    out, pairs = io.StringIO(), []
    with redirect_stdout(out):
        mismatched = [g for g in ids if (c_games[g]["names"], c_games[g]["events"], c_games[g]["start_weavers"])
                      != (b_games[g]["names"], b_games[g]["events"], b_games[g]["start_weavers"])]
        print(f"{len(ids)} matched games; identical setup in {len(ids) - len(mismatched)}"
              + (f" (MISMATCHED: {mismatched})" if mismatched else ""))
        for g in ids:
            size = int(c_games[g]["size"])
            byz = b_games[g]["byzantine"]
            c = {r["agent"]: r for r in c_rows if r["game_id"] == g}
            b = {r["agent"]: r for r in b_rows if r["game_id"] == g}
            for r in list(c.values()) + list(b.values()):
                r["trust_share"] = num(r["trust_noms"]) / size
                r["coord_share"] = num(r["coord_noms"]) / size
            rec = {"game_id": g, "size": size, "byzantine": byz,
                   "byz_promise_days": counts[g]["promises"], "byz_excuse_days": counts[g]["excuses"],
                   "byz_called_out": counts[g]["called_out"],
                   "byz_was_keeper": b_games[g]["keeper"] == byz,
                   "seat_was_keeper_in_control": c_games[g]["keeper"] == byz}
            for k, _ in SEAT:
                rec[f"seat_{k}_control"], rec[f"seat_{k}_byz"] = num(c[byz].get(k)), num(b[byz].get(k))
            others = [a for a in c if a != byz]
            for k, _ in COLONY:
                cv = [num(c[a].get(k)) for a in others]
                bv = [num(b[a].get(k)) for a in others]
                cv, bv = [x for x in cv if x is not None], [x for x in bv if x is not None]
                rec[f"colony_{k}_control"] = sum(cv) / len(cv) if cv else None
                rec[f"colony_{k}_byz"] = sum(bv) / len(bv) if bv else None
            pairs.append(rec)

        print("\nThe Byzantine colonist itself:")
        days = b_cfg["days"]
        print(f"  promised food on {sum(p['byz_promise_days'] for p in pairs) / len(pairs):.1f} of {days} days per "
              f"game, blamed an error on {sum(p['byz_excuse_days'] for p in pairs) / len(pairs):.1f}; others "
              f"named it in a message about promises or missing food "
              f"{sum(p['byz_called_out'] for p in pairs) / len(pairs):.1f} times per game")
        print(f"  chosen as keeper in {sum(p['byz_was_keeper'] for p in pairs)}/{len(pairs)} games "
              f"(the same seat in control: {sum(p['seat_was_keeper_in_control'] for p in pairs)}/{len(pairs)})")

        def table(title, metrics, prefix):
            sizes = sorted({p["size"] for p in pairs})
            print(f"\n{title}")
            print(f"  {'':<42}" + "".join(f"{'size ' + str(s):>16}" for s in sizes) + f"{'all games':>22}")
            for k, label in metrics:
                cells = []
                for s in sizes:
                    ps = [p for p in pairs if p["size"] == s]
                    cv = [p[f"{prefix}_{k}_control"] for p in ps if p[f"{prefix}_{k}_control"] is not None]
                    bv = [p[f"{prefix}_{k}_byz"] for p in ps if p[f"{prefix}_{k}_byz"] is not None]
                    cells.append(f"{sum(cv) / len(cv):.2f} -> {sum(bv) / len(bv):.2f}" if cv and bv else "-")
                diffs = [p[f"{prefix}_{k}_byz"] - p[f"{prefix}_{k}_control"] for p in pairs
                         if p[f"{prefix}_{k}_byz"] is not None and p[f"{prefix}_{k}_control"] is not None]
                d, pv = sign_flip(diffs)
                print(f"  {label:<42}" + "".join(f"{c:>16}" for c in cells)
                      + (f"{d:>+12.3f} (p={pv:.3f})" if d is not None else ""))

        table("Same seat, control -> Byzantine (mean per game; last column: paired difference):",
              SEAT, "seat")
        table("Everyone else, control -> with a Byzantine colonist present:", COLONY, "colony")
        print("\nRead the per-size columns as descriptive; the p-values pool all games. Trust and "
              "keeper votes are zero-sum, so votes the Byzantine colonist loses go to others.")
    text = out.getvalue()
    print(text)
    dest = Path(sys.argv[2])
    (dest / "compare.txt").write_text(text)
    with open(dest / "compare.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
        w.writeheader()
        w.writerows(pairs)
    print(f"saved compare.txt and compare.csv to {dest}")


if __name__ == "__main__":
    main()
