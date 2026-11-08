#!/usr/bin/env python3
"""
environment_summary.py - does changing the environment make the colony punish broken promises?

  python environment_summary.py "original=runs/CTRL,runs/BYZ" "gift board=runs/CTRL2,runs/BYZ2" ...

Each argument is label=control_run,byzantine_run (same seed, so games pair up).
For each setting: what the promise-breaker paid relative to the same seat in
the control games (paired sign-flip p-values), who called it out, and how its
victims voted. Writes environment_summary.txt next to this script's runs/.
"""
import csv
import io
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_promises as ap  # noqa: E402
from compare_arms import sign_flip  # noqa: E402

PAIRED = [("seat_trust_share", "trust-vote share"), ("seat_coord_share", "keeper-nomination share"),
          ("seat_gifts_received", "food received as gifts"), ("seat_joint_work", "days of paired work"),
          ("colony_gifts_given", "others: food given per member"),
          ("colony_hungry_days", "others: hungry days per member")]


def paired(rows, key):
    diffs = []
    for r in rows:
        try:
            diffs.append(float(r[f"{key}_byz"]) - float(r[f"{key}_control"]))
        except (TypeError, ValueError):
            pass
    d, p = sign_flip(diffs)
    return "-" if d is None else f"{d:+.2f} (p={p:.2f})"


def share(xs):
    return f"{100 * sum(xs) / len(xs):.0f}%" if xs else "-"


def main():
    conds = []
    for arg in sys.argv[1:]:
        label, runs = arg.split("=", 1)
        ctrl, byz = runs.split(",")
        subprocess.run([sys.executable, str(HERE / "compare_arms.py"), ctrl, byz], check=True,
                       stdout=subprocess.DEVNULL)
        rows = list(csv.DictReader(open(Path(byz) / "compare.csv")))
        conds.append((label, rows, ap.analyze(byz)))
    if not conds:
        sys.exit(__doc__)
    w = 34
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"{'':<{w}}" + "".join(f"{c[0]:>24}" for c in conds))

        def line(label, cells):
            print(f"{label:<{w}}" + "".join(f"{c:>24}" for c in cells))

        print("The promise-breaker")
        line("  games", [str(len(r)) for _, r, _ in conds])
        line("  days it promised food", [f"{sum(float(x['byz_promise_days']) for x in r) / len(r):.1f}"
                                         for _, r, _ in conds])
        line("  days it blamed an error", [f"{sum(float(x['byz_excuse_days']) for x in r) / len(r):.1f}"
                                           for _, r, _ in conds])
        print("Who calls it out (messages per game)")
        line("  victims", [f"{len(T['callout_by_target']) / len(T['games']):.2f}" for _, _, T in conds])
        line("  third parties", [f"{len(T['callout_by_third_party']) / len(T['games']):.2f}" for _, _, T in conds])
        line("  games with any call-out", [
            f"{len({g for g, _, _ in T['callout_by_target'] + T['callout_by_third_party']})}/{len(T['games'])}"
            for _, _, T in conds])
        print("Victims' memory (notebook the next day)")
        line("  records the gift as missing", [share(T["target_notebook_mentions_unpaid"]) for _, _, T in conds])
        print("What it costs (vs the same seat in control games; paired difference)")
        for key, label in PAIRED:
            line(f"  {label}", [paired(r, key) for _, r, _ in conds])
        print("How victims vote (share backing the promise-breaker)")
        for kind in ("coordinator", "trust"):
            line(f"  {kind}: victims", [share(T[f"{kind}_vote_for_byz_victim"]) for _, _, T in conds])
            line(f"  {kind}: everyone else", [share(T[f"{kind}_vote_for_byz_non_victim"]) for _, _, T in conds])
        line("  chosen as keeper", [f"{sum(T['byz_was_keeper'])}/{len(T['games'])}" for _, _, T in conds])
        print("Stakes")
        line("  victim's food when promised", [ap.avg(T["target_food_when_promised"]) for _, _, T in conds])
    text = out.getvalue()
    print(text)
    (HERE / "runs" / "environment_summary.txt").write_text(text)


if __name__ == "__main__":
    main()
