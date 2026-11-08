#!/usr/bin/env python3
"""
mediation.py - trait -> behaviour -> influence chains.

  python mediation.py runs/<run> [runs/<run> ...] [--boot 1000]

For each trait T (version B vs A), behaviour M and influence outcome Y
(keeper-nomination share, trust-vote share = votes / colony size):

  a        effect of T on M        (M ~ all traits + one indicator per game)
  b        effect of M on Y        (Y ~ M + all traits + game indicators)
  indirect a x b: the part of T's effect on Y that runs through M
  total    effect of T on Y        (Y ~ all traits + game indicators)

95% intervals resample whole games with replacement. Only the five real
traits are tested; behaviours are counted from what agents did, plus
judge ratings marked as judged. A planted Byzantine colonist is dropped.
Prints chains whose interval excludes zero and writes mediation.csv and
mediation.txt into the first run's folder.
"""
import argparse
import csv
import io
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

TRAITS = ["self_interest", "assertive", "guarded", "reciprocity", "loner"]
PLACEBOS = ["placebo_season", "placebo_colour"]
MEDIATORS = ["joint_work", "gifts_given", "given_after_storm", "dms_received", "mentions", "taught",
             "j_leadership", "j_generosity", "j_power_seeking"]
OUTCOMES = [("coord_share", "keeper-nomination share"), ("trust_share", "trust-vote share")]


def load(run):
    rows = [r for r in csv.DictReader(open(Path(run) / "agents.csv")) if r.get("is_byzantine", "0") != "1"]
    for r in rows:
        size = float(r["size"])
        r["coord_share"] = float(r["coord_noms"]) / size
        r["trust_share"] = float(r["trust_noms"]) / size
    return rows


def fit(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def design(rows, games):
    T = np.array([[float(r[f"k_{t}"]) for t in TRAITS + PLACEBOS] for r in rows])
    G = np.array([[1.0 if r["_g"] == g else 0.0 for g in games] for r in rows])
    return T, G


def chains(rows):
    """Point estimates for every trait x mediator x outcome."""
    games = sorted({r["_g"] for r in rows})
    T, G = design(rows, games)
    out = {}
    for m in MEDIATORS:
        M = np.array([float(r[m]) if r.get(m) not in (None, "") else np.nan for r in rows])
        ok = ~np.isnan(M)
        if ok.sum() < T.shape[1] + len(games) + 5:
            continue
        a = fit(np.hstack([T, G])[ok], M[ok])[: len(TRAITS)]
        for yk, _ in OUTCOMES:
            Y = np.array([r[yk] for r in rows])
            b = fit(np.hstack([M[:, None], T, G])[ok], Y[ok])[0]
            tot = fit(np.hstack([T, G])[ok], Y[ok])[: len(TRAITS)]
            for ti, t in enumerate(TRAITS):
                out[(t, m, yk)] = (a[ti], b, a[ti] * b, tot[ti])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rows = []
    for k, run in enumerate(a.runs):
        for r in load(run):
            r["_g"] = f"{k}:{r['game_id']}"  # games from different runs stay separate
            rows.append(r)
    point = chains(rows)
    by_game = {}
    for r in rows:
        by_game.setdefault(r["_g"], []).append(r)
    gids = sorted(by_game)
    rng = np.random.default_rng(a.seed)
    boots = {k: [] for k in point}
    for _ in range(a.boot):
        sample = []
        for j, g in enumerate(rng.choice(gids, size=len(gids), replace=True)):
            for r in by_game[g]:
                sample.append({**r, "_g": f"{g}#{j}"})  # a game drawn twice counts as two games
        est = chains(sample)
        for k in point:
            if k in est:
                boots[k].append(est[k][2])
    results = []
    for (t, m, yk), (av, bv, ind, tot) in point.items():
        lo, hi = np.percentile(boots[(t, m, yk)], [2.5, 97.5])
        results.append({"trait": t, "mediator": m, "outcome": yk, "a": round(av, 4), "b": round(bv, 4),
                        "indirect": round(ind, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4),
                        "total": round(tot, 4), "share_of_total": round(ind / tot, 2) if abs(tot) > 1e-9 else None})
    dest = Path(a.runs[0])
    with open(dest / "mediation.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"Mediation on {len(rows)} agents in {len(gids)} games from: {', '.join(Path(r).name for r in a.runs)}")
        print("Chains whose 95% interval (games resampled) excludes zero; outcome = votes received / colony size.")
        print("j_ behaviours are judge ratings, which can echo the trait sentence itself; treat them with care.\n")
        sig = [r for r in results if r["ci_low"] > 0 or r["ci_high"] < 0]
        for yk, label in OUTCOMES:
            print(f"{label}:")
            rows_y = sorted((r for r in sig if r["outcome"] == yk), key=lambda r: -abs(r["indirect"]))
            for r in rows_y:
                share = f", {r['share_of_total']:.0%} of its total effect" if r["share_of_total"] is not None \
                    and abs(r["total"]) > 0.005 else ""
                print(f"  {r['trait']:<14} -> {r['mediator']:<18} -> {label}: indirect {r['indirect']:+.4f} "
                      f"[{r['ci_low']:+.4f}, {r['ci_high']:+.4f}]  (a {r['a']:+.2f}, b {r['b']:+.4f}{share})")
            if not rows_y:
                print("  none")
        n = len(results)
        print(f"\n{len(sig)} of {n} chains exclude zero; about {0.05 * n:.0f} would by chance.")
    text = out.getvalue()
    print(text)
    (dest / "mediation.txt").write_text(text)


if __name__ == "__main__":
    main()
