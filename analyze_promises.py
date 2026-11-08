#!/usr/bin/env python3
"""
analyze_promises.py - why doesn't the colony punish the Byzantine colonist?

  python analyze_promises.py runs/<byzantine_run> [runs/<another_byzantine_run> ...]

Traces each broken promise in a --byzantine run: whom it targeted, whether the
target noticed and remembered it, who spoke up, how targets voted, how many
promises had been broken before each vote, and how much the target needed food.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import colony_sim as cs  # noqa: E402

GIFT_WORDS = re.compile(r"\b(gift|food|promis\w*|tally|owe|owed)\b", re.I)


def analyze(run):
    run = Path(run)
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    by_game = defaultdict(lambda: defaultdict(dict))  # game -> day -> agent -> record
    for line in open(run / "transcript.jsonl"):
        r = json.loads(line)
        r["p"] = cs.parse_reply(r["reply"]) or {}
        by_game[r["game"]][r["day"]][r["agent"]] = r
    T = defaultdict(list)  # tallies across games
    for gid, days in by_game.items():
        g = games[gid]
        byz, names = g["byzantine"], g["names"]
        others = [n for n in names if n != byz]
        named = {n: re.compile(rf"\b{re.escape(n)}\b", re.I) for n in names}
        promised = defaultdict(list)  # target -> days promised
        for d in sorted(days):
            pub = str(days[d][byz]["p"].get("public") or "")
            if cs.PROMISE_RE.search(pub):
                for n in others:
                    if named[n].search(pub):
                        promised[n].append(d)
        T["games"].append(gid)
        T["targets_per_game"].append(len(promised))
        T["max_promises_one_target"].append(max((len(v) for v in promised.values()), default=0))
        T["promises_total"].append(sum(len(v) for v in promised.values()))
        # awareness and memory: does the target's notebook mention the colonist or the gift the next day?
        for n, ds in promised.items():
            for d in ds:
                nxt = days.get(d + 1, {}).get(n)
                if not nxt:
                    continue
                nb = str(nxt["p"].get("notebook") or "")
                T["target_notebook_mentions_byz"].append(bool(named[byz].search(nb)))
                T["target_notebook_mentions_unpaid"].append(
                    bool(named[byz].search(nb) and re.search(r"didn'?t|never|not (arrive|come|get|receive)|"
                                                             r"no (gift|food)|waiting|still|promis", nb, re.I)))
                T["target_food_when_promised"].append(days[d][n]["food_end"])
        # who speaks up
        for d in sorted(days):
            for n in others:
                p = days[d][n]["p"]
                pub = str(p.get("public") or "")
                priv = [m for m in (p.get("private") or []) if isinstance(m, dict)]
                aimed = ([pub] if named[byz].search(pub) else []) + [
                    str(m.get("text", "")) for m in priv
                    if str(m.get("to", "")).strip().lower() == byz.lower() or named[byz].search(str(m.get("text", "")))]
                if any(cs.CALLOUT_RE.search(t) for t in aimed):
                    was_target = any(x <= d for x in promised.get(n, []))
                    T["callout_by_target" if was_target else "callout_by_third_party"].append((gid, d, n))
                # third parties who saw a public call-out the day before: do they echo it?
        # votes: did people who had been promised (and stiffed) before the vote still back the colonist?
        for kind, field in (("coordinator", "nominate"), ("trust", "trust")):
            vd = g["events"][kind]
            T[f"broken_before_{kind}"].append(sum(1 for v in promised.values() for x in v if x < vd))
            for n in others:
                choice = str(days[vd][n]["p"].get(field) or "").strip().lower()
                victim = any(x < vd for x in promised.get(n, []))
                T[f"{kind}_vote_for_byz_{'victim' if victim else 'non_victim'}"].append(choice == byz.lower())
        T["vote_day_coordinator"].append(g["events"]["coordinator"])
        T["vote_day_trust"].append(g["events"]["trust"])
        T["byz_was_keeper"].append(g["keeper"] == byz)
        T["colony_size"].append(int(g["size"]))
        T["all_food"].extend(days[d][n]["food_end"] for d in days for n in others)
    return T


def pct(xs):
    return f"{100 * sum(xs) / len(xs):.0f}% (n={len(xs)})" if xs else "n/a"


def avg(xs):
    return f"{sum(xs) / len(xs):.1f}" if xs else "n/a"


def report(run, T):
    print(f"\n===== {run}  ({len(T['games'])} games)")
    print("Spread of promises")
    print(f"  broken promises per game: {avg(T['promises_total'])}; different members targeted per game: "
          f"{avg(T['targets_per_game'])}; most promises to one member: {avg(T['max_promises_one_target'])}")
    print("Does the target notice and remember? (target's notebook the day after a broken promise)")
    print(f"  names the colonist at all: {pct(T['target_notebook_mentions_byz'])}")
    print(f"  records the gift as missing/owed: {pct(T['target_notebook_mentions_unpaid'])}")
    print("Who speaks up (message naming the colonist alongside promises / missing food)")
    t, o = len(T["callout_by_target"]), len(T["callout_by_third_party"])
    print(f"  by someone it promised: {t}; by a third party: {o}; "
          f"games with any call-out: {len({g for g, _, _ in T['callout_by_target'] + T['callout_by_third_party']})}"
          f"/{len(T['games'])}")
    print("Timing of the only formal sanctions (votes)")
    print(f"  coordinator vote on day {avg(T['vote_day_coordinator'])} on average, after "
          f"{avg(T['broken_before_coordinator'])} broken promises; trust poll on day {avg(T['vote_day_trust'])}, "
          f"after {avg(T['broken_before_trust'])}")
    print("Do victims withdraw support? (share of voters backing the colonist)")
    for kind in ("coordinator", "trust"):
        print(f"  {kind:<11}: victims {pct(T[f'{kind}_vote_for_byz_victim'])}, "
              f"everyone else {pct(T[f'{kind}_vote_for_byz_non_victim'])}")
    print(f"  colonist chosen as keeper in {sum(T['byz_was_keeper'])}/{len(T['games'])} games")
    print("Stakes")
    print(f"  target's food on the day it was promised: {avg(T['target_food_when_promised'])}; "
          f"average food held by honest members across all days: {avg(T['all_food'])}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for run in sys.argv[1:]:
        report(run, analyze(run))


if __name__ == "__main__":
    main()
