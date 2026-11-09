"""Figures for the project PDF, computed from the run folders. Run from the repo root with the project venv."""
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import analyze_long as al  # noqa: E402

OUT = Path(__file__).resolve().parent
ACCENT, DARK, MID, LIGHT, GRID = "#1f6feb", "#3d3d3d", "#8a8a8a", "#c4c4c4", "#e6e6e6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MID, "axes.labelcolor": DARK,
                     "xtick.color": DARK, "ytick.color": DARK, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "legend.frameon": False, "savefig.dpi": 220, "savefig.bbox": "tight"})
R = lambda p: REPO / "runs" / p  # noqa: E731
LONG = {  # economy -> (control, promise-breaker, control + board, promise-breaker + board)
    "Positive-sum": ("colony_20261107-215315_s0_d1000_season20_spoil_why", "colony_20261107-215317_s0_d1000_season20_spoil_why_byz",
                     "colony_20261108-014252_s0_d1000_season20_spoil_why_ledger", "colony_20261108-014254_s0_d1000_season20_spoil_why_ledger_byz"),
    "Zero-sum": ("colony_20261107-233955_s0_d1000_season20_spoil_why_zerosum", "colony_20261107-233957_s0_d1000_season20_spoil_why_zerosum_byz",
                 "colony_20261108-014256_s0_d1000_season20_spoil_why_zerosum_ledger", "colony_20261108-014258_s0_d1000_season20_spoil_why_zerosum_ledger_byz"),
    "Negative-sum": ("colony_20261107-233959_s0_d1000_season20_spoil_why_negativesum", "colony_20261107-234001_s0_d1000_season20_spoil_why_negativesum_byz",
                     "colony_20261108-014300_s0_d1000_season20_spoil_why_negativesum_ledger", "colony_20261108-014302_s0_d1000_season20_spoil_why_negativesum_ledger_byz"),
}
summary = {}


def games_of(run):
    return {g["game_id"]: g for g in map(json.loads, open(R(run) / "games.jsonl"))}


def trust_series(run):
    cfg = json.load(open(R(run) / "config.json"))
    per = al.seat_shares(games_of(run), cfg, "byz_seat")
    raw = [sum(per[g][s]["trust"] for g in per) / len(per) for s in range(50)]
    return [sum(raw[max(0, s - 2): s + 3]) / len(raw[max(0, s - 2): s + 3]) for s in range(50)], raw


# ---------------------------------------------------------------- F1 replays
def fig_replays():
    runs = {"gemma-4-31b": "colony_20261107-191740_s0_byz", "gemma-4-26b": "colony_20261107-200746_s0_byz"}
    variants = [("as_logged", "As\nlogged"), ("no_memory", "Notes\nremoved"), ("no_promises", "Promises\nremoved"),
                ("no_both", "Both\nremoved"), ("told_unpaid", "Told: food\nnever came")]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    rng = random.Random(0)
    summary["replays"] = {}
    for ax, (model, run) in zip(axes, runs.items()):
        votes = defaultdict(lambda: defaultdict(list))
        for r in csv.DictReader(open(R(run) / "replays.csv")):
            if r["parsed"] == "1":
                votes[(r["game"], r["day"], r["kind"], r["voter"])][r["variant"]].append(int(r["for_byz"]))
        keys = [k for k in votes if all(v in votes[k] for v, _ in variants)]
        means, los, his = [], [], []
        for v, _ in variants:
            per = [sum(votes[k][v]) / len(votes[k][v]) for k in keys]
            m = sum(per) / len(per)
            boots = sorted(sum(rng.choice(per) for _ in per) / len(per) for _ in range(1000))
            means.append(m); los.append(m - boots[25]); his.append(boots[974] - m)
        summary["replays"][model] = dict(zip([v for v, _ in variants], means)) | {"votes": len(keys)}
        colors = [MID, LIGHT, LIGHT, LIGHT, ACCENT]
        x = range(len(variants))
        ax.bar(x, [m * 100 for m in means], color=colors, width=0.62, zorder=2)
        ax.errorbar(x, [m * 100 for m in means], yerr=[[l * 100 for l in los], [h * 100 for h in his]], fmt="none",
                    ecolor=DARK, elinewidth=0.9, capsize=2.5, zorder=3)
        for i, m in enumerate(means):
            ax.text(i, m * 100 + his[i] * 100 + 1.5, f"{m * 100:.0f}%", ha="center", va="bottom", fontsize=8, color=DARK)
        ax.set_xticks(list(x)); ax.set_xticklabels([lab for _, lab in variants], fontsize=6.3)
        ax.set_title(f"{model} ({len(keys)} victim votes)", fontsize=9, color=DARK, loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Victims' votes for the promise-breaker")
    axes[0].set_ylim(0, 58)
    axes[0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    fig.savefig(OUT / "f1_replays.png"); plt.close(fig)


# ---------------------------------------------------------------- F2 trust over 1000 days
def fig_trust():
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), sharey=True)
    days = [20 * (s + 1) for s in range(50)]
    summary["trust"] = {}
    for ax, (econ, (ctrl, byz, ctrl_b, byz_b)) in zip(axes, LONG.items()):
        c, _ = trust_series(ctrl); b, braw = trust_series(byz); bb, bbraw = trust_series(byz_b)
        ax.axhline(12.5, color=MID, lw=0.8, ls=(0, (3, 3)))
        ax.plot(days, [v * 100 for v in c], color=LIGHT, lw=1.6, label="Same seat, control games")
        ax.plot(days, [v * 100 for v in b], color=DARK, lw=1.6, label="Promise-breaker, no gift board")
        ax.plot(days, [v * 100 for v in bb], color=ACCENT, lw=1.8, label="Promise-breaker, gift board")
        ax.set_title(econ, fontsize=9, loc="left", color=DARK)
        ax.set_xticks([0, 500, 1000]); ax.set_xlabel("Day")
        summary["trust"][econ] = {"byz_mean": sum(braw) / 50, "board_mean": sum(bbraw) / 50}
    axes[0].set_ylabel("Share of trust votes")
    axes[0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    axes[0].set_yticks([0, 5, 10, 15])
    axes[0].plot([], [], color=MID, lw=0.8, ls=(0, (3, 3)), label="Fair share (12.5%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.09), fontsize=7.5)
    fig.savefig(OUT / "f2_trust.png"); plt.close(fig)


# ---------------------------------------------------------------- F3 call-outs
def fig_callouts():
    econs = list(LONG)
    explicit = {"off": [0.54, 0.71, 2.65], "on": [17.18, 15.09, 13.73]}   # computed in the session from transcripts
    broad = {"off": [0.79, 1.47, 7.95], "on": [47.66, 46.85, 28.38]}
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    w = 0.36
    for i, e in enumerate(econs):
        for j, (board, col) in enumerate((("off", MID), ("on", ACCENT))):
            x = i + (j - 0.5) * w
            ax.bar(x, broad[board][i], width=w * 0.92, color=col, alpha=0.28, zorder=2)
            ax.bar(x, explicit[board][i], width=w * 0.92, color=col, zorder=3)
            ax.text(x, broad[board][i] + 0.8, f"{explicit[board][i]:.1f}\n({broad[board][i]:.1f})", ha="center",
                    va="bottom", fontsize=7, color=DARK)
    ax.set_xticks(range(3)); ax.set_xticklabels(econs)
    ax.set_ylabel("Call-outs per game per season")
    ax.set_ylim(0, 62)
    ax.grid(axis="x", visible=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=MID, label="No gift board"), Patch(color=ACCENT, label="Gift board"),
                       Patch(color=MID, alpha=0.28, label="Pale: any mention with \"promise\" (broad detector)")],
              loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=7.5)
    fig.savefig(OUT / "f3_callouts.png"); plt.close(fig)


# ---------------------------------------------------------------- F4 keeper concentration
def fig_keepers():
    rows = []
    for econ, runs in LONG.items():
        for run, lab in zip(runs, ("control", "promise-breaker", "control + board", "promise-breaker + board")):
            for gid, g in games_of(run).items():
                terms = g.get("store_terms", [])
                cnt = defaultdict(int)
                for t in terms:
                    cnt[t["keeper"]] += 1
                top, n = max(cnt.items(), key=lambda kv: kv[1])
                rows.append((n, top, econ, lab, gid))
    rows.sort(reverse=True)
    summary["keepers"] = {"min": rows[-1][0], "max": rows[0][0], "n": len(rows)}
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    ax.bar(range(len(rows)), [r[0] for r in rows], color=[ACCENT if r[1] in ("Runa", "Pell") else MID for r in rows],
           width=0.8, zorder=2)
    ax.axhline(50 / 8, color=DARK, lw=0.8, ls=(0, (3, 3)), label="Expected if keepers were picked at random (6.25)")
    ax.legend(loc="upper right", fontsize=7.5)
    ax.set_ylabel("Terms held by the top keeper (of 50)")
    ax.set_xticks([]); ax.set_xlabel("36 thousand-day games, sorted (blue: Runa or Pell)")
    ax.grid(axis="x", visible=False)
    fig.savefig(OUT / "f4_keepers.png"); plt.close(fig)


# ---------------------------------------------------------------- F5 inequality
def gini(xs):
    xs = sorted(xs); n = len(xs); s = sum(xs)
    return 0.0 if s == 0 else sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(xs)) / (n * s)


def fig_gini():
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    styles = {"Positive-sum": (ACCENT, "-"), "Zero-sum": (DARK, "-"), "Negative-sum": (MID, "-")}
    summary["gini"] = {}
    for econ, runs in LONG.items():
        food = defaultdict(dict)
        for run in (runs[0], runs[2]):           # the two control runs (board off and on)
            for line in open(R(run) / "transcript.jsonl"):
                r = json.loads(line)
                if r["day"] % 10 == 0:
                    food[(run, r["game"], r["day"])][r["agent"]] = r["food_end"]
        by_day = defaultdict(list)
        for (_, _, d), f in food.items():
            by_day[d].append(gini(list(f.values())))
        days = sorted(by_day)
        vals = [sum(by_day[d]) / len(by_day[d]) for d in days]
        sm = [sum(vals[max(0, i - 2): i + 3]) / len(vals[max(0, i - 2): i + 3]) for i in range(len(vals))]
        col, ls = styles[econ]
        ax.plot(days, sm, color=col, ls=ls, lw=1.6, label=econ)
        summary["gini"][econ] = sum(vals[-10:]) / 10
    ax.set_ylabel("Food inequality (Gini)"); ax.set_xlabel("Day")
    ax.legend(loc="upper right", fontsize=8)
    fig.savefig(OUT / "f5_gini.png"); plt.close(fig)


# ---------------------------------------------------------------- F6 cross-model
def fig_xmodel():
    path = REPO / "runs/xmodel40/cross_model.csv"
    pts = defaultdict(lambda: defaultdict(dict))
    for r in csv.DictReader(open(path)):
        if r["arm"] in ("byz", "byz_board"):
            name = r["model"] + (" (40 days)" if r["model"] == "gemma-4-31b-it" else "")
            pts[name][r["game"]][r["arm"]] = float(r["trust"])
    # gemma-4-31b: whole 1000-day positive-sum games (different design), for reference
    for arm, run in (("byz", LONG["Positive-sum"][1]), ("byz_board", LONG["Positive-sum"][3])):
        cfg = json.load(open(R(run) / "config.json"))
        per = al.seat_shares(games_of(run), cfg, "byz_seat")
        for g in per:
            pts["gemma-4-31b-it (1000 days)"][g][arm] = sum(per[g][s]["trust"] for s in range(50)) / 50
    models = [m for m in pts if all(len(v) == 2 for v in pts[m].values())]
    summary["xmodel"] = {m: {g: v for g, v in pts[m].items()} for m in models}
    fig, axes = plt.subplots(1, len(models), figsize=(2.3 * len(models) + 0.6, 2.5), sharey=True, squeeze=False)
    for ax, m in zip(axes[0], models):
        for g, v in pts[m].items():
            ax.plot([0, 1], [v["byz"] * 100, v["byz_board"] * 100], color=LIGHT, lw=1, zorder=1)
            ax.scatter([0], [v["byz"] * 100], color=DARK, s=18, zorder=2)
            ax.scatter([1], [v["byz_board"] * 100], color=ACCENT, s=18, zorder=2)
        mo = sum(v["byz"] for v in pts[m].values()) / len(pts[m]); mb = sum(v["byz_board"] for v in pts[m].values()) / len(pts[m])
        ax.plot([0, 1], [mo * 100, mb * 100], color=ACCENT, lw=2.2, zorder=3)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["No board", "Gift board"]); ax.set_xlim(-0.35, 1.35)
        ax.set_title(m, fontsize=8.5, loc="left", color=DARK)
        ax.axhline(12.5, color=MID, lw=0.8, ls=(0, (3, 3)))
        ax.grid(axis="x", visible=False)
    axes[0][0].set_ylabel("Promise-breaker's share of trust votes")
    axes[0][0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    fig.savefig(OUT / "f6_xmodel.png"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_replays, fig_trust, fig_callouts, fig_keepers, fig_gini, fig_xmodel):
        f()
        print("done", f.__name__)
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "xmodel"}, indent=1, default=str)[:2500])
