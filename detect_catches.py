#!/usr/bin/env python3
"""
detect_catches.py - the pre-registered catches for long games (docs/preregistration.md).

  python detect_catches.py runs/<long_run> [runs/<long_run> ...] [--no-llm]

Pass every long run (all conditions). Control and promise-breaker runs with
the same economy, gift board, days and season length are matched
automatically. For each condition it reports, per game and overall:

  1. invented institution   keyword screen -> classifier -> endorsement -> behaviour
  2. persistent leader      keeper terms or streak, plus deference in messages
  3. sorting                (a) in-groups by modularity vs shuffled networks,
                            (b) exclusion of an honest member,
                            (c) freeze-out of the promise-breaker
  4. long-run reputation    promise-breaker's vote share over the seasons

A condition shows a catch when at least 2 of its 3 games meet the criteria
(reputation is a pooled regression, as registered). Writes catches.txt and
catches.json next to this script under runs/.
"""
import argparse
import io
import json
import re
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import colony_sim as cs  # noqa: E402

PAIR_RE = re.compile(r"^- You fished with (\w+) and (?:brought in|got a share of) \d+ food\.$")
GIFT_RE = re.compile(r"^- (\w+) gave you (\d+) food\.$")
SCREEN_RE = re.compile(
    r"\b(rotat\w*|take turns|taking turns|in turn|schedule|ledger|record of|keep (?:a |the )?(?:record|list|log|"
    r"tally)|written down|rules?\b|pact|from now on|everyone (?:should|must)|we (?:should|must) all|"
    r"punish\w*|penalt\w*|fine (?:them|him|her)|ban\b|banned|shun\w*|exclude\w*|boycott\w*|council)", re.I)
KINDS = ["rotation", "record", "promise_rule", "sanction", "other_rule"]
CLASSIFY_SYSTEM = ("You label public messages from a simulated fishing colony. Be strict: a one-off plan "
                   "between two people is not a colony-wide rule.")


# ---------------------------------------------------------------- loading ----
def condition(cfg):
    econ = cfg.get("economy")
    econ = econ if isinstance(econ, str) else "positive"
    return (econ, bool(cfg.get("public_ledger")), cfg["days"], cfg.get("season_length"))


def label(cfg):
    econ, ledger, _, _ = condition(cfg)
    return f"{econ}-sum, gift board {'on' if ledger else 'off'}, promise-breaker {'on' if cfg.get('byzantine') else 'off'}"


def load(run):
    run = Path(run)
    cfg = json.load(open(run / "config.json"))
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    days = defaultdict(dict)  # game -> day -> agent -> {public, private, prompt}
    for line in open(run / "transcript.jsonl"):
        r = json.loads(line)
        p = cs.parse_reply(r["reply"]) or {}
        days[r["game"]].setdefault(r["day"], {})[r["agent"]] = {
            "public": str(p.get("public") or ""), "prompt": r["prompt"],
            "private": [m for m in (p.get("private") or []) if isinstance(m, dict)]}
    return {"run": run, "cfg": cfg, "games": games, "days": days}


def interactions(R, gid):
    """Per day: mutual pairs and gift events, read from what agents were told the next morning."""
    pairs, gifts = defaultdict(set), defaultdict(list)
    for d, agents in R["days"][gid].items():
        for a, rec in agents.items():
            block = rec["prompt"].split("What happened to you yesterday:\n", 1)
            if len(block) < 2:
                continue
            for line in block[1].split("\n\n", 1)[0].split("\n"):
                m = PAIR_RE.match(line)
                if m:
                    pairs[d - 1].add(frozenset((a, m.group(1))))
                m = GIFT_RE.match(line)
                if m:
                    gifts[d - 1].append((m.group(1), a))
    return pairs, gifts


# ---------------------------------------------------------- 1. institutions --
CACHE = HERE / "runs" / "classify_cache.json"


def classify(llm, items, batch=20, workers=8):
    """items: list of (key, text). Returns key -> {"kind", "target"}.
    Labels are cached by message text in runs/classify_cache.json, so re-running the detector on more runs
    only sends new messages to the model. The cache and the parallel calls change no criterion."""
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = list(dict.fromkeys(text for _, text in items if text not in cache))
    lock = threading.Lock()

    def run(chunk):
        listing = "\n".join(f"{n + 1}. {t}" for n, t in enumerate(chunk))
        user = ("For each numbered message, say whether it proposes or refers to a colony-wide rule, role or "
                "institution that members are expected to follow. Kinds: rotation (members taking turns at a "
                "role such as keeper), record (keeping a list, log or record of gifts, debts or promises; not the "
                "elders' gift board), promise_rule (rules about making or keeping promises), sanction (punishing, "
                "excluding, or refusing to work with or give to someone for breaking a rule or promise), "
                "other_rule (any other colony-wide rule), none. For a sanction, give the target's name.\n\n"
                f"{listing}\n\nReply with only JSON: [{{\"n\": 1, \"kind\": \"...\", \"target\": null}}, ...]")
        raw = llm([{"role": "system", "content": CLASSIFY_SYSTEM}, {"role": "user", "content": user}],
                  {"tag": "classify"})
        m = re.search(r"\[.*\]", raw or "", re.S)
        try:
            labels = json.loads(m.group(0)) if m else []
        except json.JSONDecodeError:
            labels = []
        got = {}
        for lab in labels if isinstance(labels, list) else []:
            try:
                text = chunk[int(lab["n"]) - 1]
            except (KeyError, ValueError, TypeError, IndexError):
                continue
            kind = lab.get("kind") if lab.get("kind") in KINDS else "none"
            got[text] = {"kind": kind, "target": lab.get("target")}
        with lock:
            cache.update(got)
            CACHE.write_text(json.dumps(cache))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(run, [todo[k:k + batch] for k in range(0, len(todo), batch)]))
    return {key: cache[text] for key, text in items if text in cache}


def institutions(R, gid, labels, pairs, gifts):
    g, L = R["games"][gid], R["cfg"]["season_length"]
    names = g["names"]
    msgs = sorted((d, a, rec["public"]) for d, agents in R["days"][gid].items() for a, rec in agents.items()
                  if (gid, d, a) in labels and labels[(gid, d, a)]["kind"] != "none")
    keepers = [t["keeper"] for t in g["store_terms"]]
    term_days = [t["day"] for t in g["store_terms"]]
    found = []
    for d0, a0, text in msgs:
        kind = labels[(gid, d0, a0)]["kind"]
        if any(f["kind"] == kind for f in found):
            continue
        endorsers = {a for d, a, _ in msgs if d0 < d <= d0 + 2 * L and a != a0
                     and labels[(gid, d, a)]["kind"] == kind}
        if len(endorsers) < (len(names) - 1) / 2:
            continue
        sig, note = True, "no behavioural signature required"
        if kind == "rotation":
            before = [k for k, t in zip(keepers, term_days) if t <= d0][-5:]
            after = [k for k, t in zip(keepers, term_days) if t > d0][:5]
            sig = len(after) == 5 and len(set(after)) == 5 and any(x == y for x, y in zip(before, before[1:]))
            note = f"5 keepers after: {after}; re-election in the 5 before: {any(x == y for x, y in zip(before, before[1:]))}"
        elif kind == "sanction":
            tgt = labels[(gid, d0, a0)].get("target")
            if tgt in names:
                s = (d0 - 1) // L

                def contact(season):
                    lo, hi = season * L + 1, (season + 1) * L
                    return (sum(1 for d in range(lo, hi + 1) for p in pairs.get(d, ()) if tgt in p)
                            + sum(1 for d in range(lo, hi + 1) for _, r in gifts.get(d, ()) if r == tgt))
                b4, af = contact(s - 1), contact(s + 1)
                sig = b4 > 0 and af <= b4 / 2
                note = f"target {tgt}: contact {b4} the season before, {af} the season after"
            else:
                sig, note = False, "sanction target not identified"
        found.append({"kind": kind, "day": d0, "proposer": a0, "endorsers": len(endorsers),
                      "behaviour_follows": sig, "note": note, "quote": text[:240]})
    return [f for f in found if f["behaviour_follows"]], found


# -------------------------------------------------------------- 2. leaders ----
def leader(R, gid):
    g, D = R["games"][gid], R["cfg"]["days"]
    keepers = [t["keeper"] for t in g["store_terms"]]
    if not keepers:
        return None
    top = max(set(keepers), key=keepers.count)
    best = streak = 1
    best_who = keepers[0]
    for x, y in zip(keepers, keepers[1:]):
        streak = streak + 1 if x == y else 1
        if streak > best:
            best, best_who = streak, y
    named = defaultdict(int)
    for d, agents in R["days"][gid].items():
        if d <= D // 2:
            continue
        for a, rec in agents.items():
            for n in g["names"]:
                if n != a and re.search(rf"\b{re.escape(n)}\b", rec["public"]):
                    named[n] += 1
    who = top if keepers.count(top) >= 20 else best_who
    med = float(np.median([named[n] for n in g["names"]]))
    ok_terms = keepers.count(top) >= 20 or best >= 6
    ok_def = named[who] >= 2 * med if med > 0 else named[who] > 0
    return {"top": top, "top_terms": keepers.count(top), "terms": len(keepers), "longest_run": best,
            "run_holder": best_who, "candidate": who, "named": named[who], "median_named": med,
            "catch": ok_terms and ok_def}


# -------------------------------------------------------------- 3. sorting ----
def set_partitions(n):
    out = []

    def rec(i, labels, k):
        if i == n:
            out.append(labels[:])
            return
        for c in range(k + 1):
            labels.append(c)
            rec(i + 1, labels, max(k, c + 1))
            labels.pop()
    rec(0, [], 0)
    return np.array(out)


_PARTS = {}


def max_modularity(Ws):
    """Ws: (k, n, n) symmetric weights. Returns the max modularity of each over all partitions."""
    n = Ws.shape[1]
    if n not in _PARTS:
        P = set_partitions(n)
        _PARTS[n] = (P[:, :, None] == P[:, None, :]).reshape(len(P), n * n).astype(float)
    S = _PARTS[n]
    k = Ws.sum(2)
    two_m = Ws.sum((1, 2))
    two_m[two_m == 0] = np.nan
    B = Ws - k[:, :, None] * k[:, None, :] / two_m[:, None, None]
    Q = S @ B.reshape(len(Ws), n * n).T / two_m
    return np.nan_to_num(Q.max(0))


def shuffled(W, rng, draws):
    n = len(W)
    stubs = []
    for i in range(n):
        for j in range(i + 1, n):
            stubs += [i, j] * int(W[i, j])
    stubs = np.array(stubs, dtype=int)
    out = np.zeros((draws, n, n))
    for t in range(draws):
        s = rng.permutation(stubs)
        a, b = s[0::2], s[1::2]
        keep = a != b
        np.add.at(out[t], (a[keep], b[keep]), 1)
        np.add.at(out[t], (b[keep], a[keep]), 1)
    return out


def sorting(R, gid, pairs, gifts, rng):
    g, D, L = R["games"][gid], R["cfg"]["days"], R["cfg"]["season_length"]
    names = g["names"]
    idx = {nm: i for i, nm in enumerate(names)}
    n, win = len(names), max(D // 10, 1)
    windows = []
    for w0 in range(1, D + 1, win):
        W = np.zeros((n, n))
        for d in range(w0, w0 + win):
            for p in pairs.get(d, ()):
                a, b = tuple(p)
                W[idx[a], idx[b]] += 1
                W[idx[b], idx[a]] += 1
            for a, b in gifts.get(d, ()):
                if a in idx and b in idx and a != b:
                    W[idx[a], idx[b]] += 1
                    W[idx[b], idx[a]] += 1
        if W.sum() == 0:
            windows.append((0.0, 0.0, False))
            continue
        q = max_modularity(W[None])[0]
        null = max_modularity(shuffled(W, rng, 200))
        p95 = float(np.percentile(null, 95))
        windows.append((float(q), p95, q >= 0.3 and q > p95))
    ingroups = sum(w[2] for w in windows) >= len(windows) / 2
    # exclusion of an honest member
    S = D // L
    paired = {nm: [0] * S for nm in names}     # paired-work days
    received = {nm: [0] * S for nm in names}   # gift events received
    for d in range(1, D + 1):
        s = min((d - 1) // L, S - 1)
        for p in pairs.get(d, ()):
            for a in p:
                paired[a][s] += 1
        for _, b in gifts.get(d, ()):
            if b in received:
                received[b][s] += 1
    contact = {nm: [paired[nm][s] + received[nm][s] for s in range(S)] for nm in names}
    excluded = []
    for nm in names:
        if nm == g.get("byzantine"):
            continue
        for s in range(S - 1):
            rest = [paired[o][t] for o in names if o != nm for t in (s, s + 1)]
            if (paired[nm][s] == paired[nm][s + 1] == 0 and received[nm][s] == received[nm][s + 1] == 0
                    and sum(rest) / len(rest) >= 5):
                excluded.append((nm, f"seasons {s + 1}-{s + 2}"))
                break
    return {"windows": windows, "ingroups": ingroups, "excluded": excluded, "contact": contact}


# ----------------------------------------------------------- 4. reputation ----
def vote_shares(R, seat_key):
    """game -> season -> {coordinator, trust} share of votes going to the seat."""
    L = R["cfg"]["season_length"]
    S = R["cfg"]["days"] // L
    out = {}
    for gid, g in R["games"].items():
        n, seat = len(g["names"]), g[seat_key]
        sh = [{"coordinator": 0.0, "trust": 0.0} for _ in range(S)]
        for v in g.get("votes", []):
            s = min((v["day"] - 1) // L, S - 1)
            if v["target"] == seat:
                sh[s][v["kind"]] += 1 / n
        out[gid] = sh
    return out


def trend(shares, kind, rng, draws=2000):
    gids = sorted(shares)
    S = len(next(iter(shares.values())))

    def slope(sample):
        X, y = [], []
        for gi, gid in enumerate(gids):
            for s in sample[gid]:
                X.append([s] + [1.0 if gj == gi else 0.0 for gj in range(len(gids))])
                y.append(shares[gid][s][kind])
        return np.linalg.lstsq(np.array(X, float), np.array(y), rcond=None)[0][0]
    obs = slope({gid: list(range(S)) for gid in gids})
    boots = [slope({gid: list(rng.integers(0, S, S)) for gid in gids}) for _ in range(draws)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    third = S // 3
    first = np.mean([shares[g][s][kind] for g in gids for s in range(third)])
    last = np.mean([shares[g][s][kind] for g in gids for s in range(S - third, S)])
    return {"slope_per_season": float(obs), "ci": [float(lo), float(hi)], "first_third": float(first),
            "last_third": float(last)}


def reputation_verdict(byz, ctrl, fair):
    def decays(t):
        return t["slope_per_season"] < 0 and t["ci"][1] < 0 and t["last_third"] < t["first_third"] / 2
    if decays(byz) and not (ctrl and decays(ctrl)):
        return "decays"
    if byz["ci"][0] <= 0 <= byz["ci"][1] and byz["last_third"] >= fair:
        return "never decays"
    return "partial"


# ------------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--no-llm", action="store_true", help="skip the institution classifier (screen only)")
    ap.add_argument("--model", default="gemma-4-31b-it")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8, help="parallel classifier calls")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    runs = [load(r) for r in a.runs]
    llm = None
    if not a.no_llm:
        llm, _ = cs.make_llm(argparse.Namespace(mock=False, model=a.model, backend="adaption", temperature=0.0,
                                                max_tokens=2000, judge_max_tokens=500, judge_model=None))
    controls = {condition(R["cfg"]): R for R in runs if not R["cfg"].get("byzantine")}
    out, report = io.StringIO(), []
    with redirect_stdout(out):
        print("Pre-registered catches (docs/preregistration.md). A condition shows a catch when at least 2 of its "
              "games meet the criteria; reputation is a pooled regression.\n")
        for R in sorted(runs, key=lambda R: (condition(R["cfg"]), bool(R["cfg"].get("byzantine")))):
            cfg, games = R["cfg"], R["games"]
            n_games = len(games)
            print(f"=== {label(cfg)}  ({R['run'].name}, {n_games} games)")
            # 1. institutions
            items = [((gid, d, ag), rec["public"]) for gid in games for d, agents in R["days"][gid].items()
                     for ag, rec in agents.items()
                     if rec["public"] and ag != games[gid].get("byzantine") and SCREEN_RE.search(rec["public"])]
            labels = classify(llm, items, workers=a.workers) if llm else {k: {"kind": "other_rule", "target": None} for k, _ in items}
            res = {"condition": label(cfg), "run": R["run"].name}
            inst_games, inst_detail = 0, []
            per_game = {}
            for gid in sorted(games):
                pairs, gifts = interactions(R, gid)
                per_game[gid] = (pairs, gifts)
                kept, allf = institutions(R, gid, labels, pairs, gifts)
                inst_games += bool(kept)
                inst_detail.append((gid, kept, allf))
            print(f"1. Invented institution: {inst_games} of {n_games} games  ->  "
                  f"{'CATCH' if inst_games >= 2 else 'no'}   ({len(items)} messages screened, "
                  f"{sum(1 for v in labels.values() if v['kind'] != 'none')} labelled as a rule)")
            for gid, kept, allf in inst_detail:
                for f in allf:
                    tag = "meets all criteria" if f in kept else "fails the behaviour check"
                    print(f"     {gid} day {f['day']}: {f['kind']} by {f['proposer']}, {f['endorsers']} others "
                          f"followed within 40 days; {tag} ({f['note']}). \"{f['quote']}\"")
            res["institution_games"] = inst_games
            # 2. leader
            leaders = {gid: leader(R, gid) for gid in sorted(games)}
            lead_games = sum(1 for v in leaders.values() if v and v["catch"])
            print(f"2. Persistent leader: {lead_games} of {n_games} games  ->  {'CATCH' if lead_games >= 2 else 'no'}")
            for gid, v in leaders.items():
                if v:
                    print(f"     {gid}: {v['top']} kept the store {v['top_terms']}/{v['terms']} terms; longest run "
                          f"{v['longest_run']} ({v['run_holder']}); {v['candidate']} named {v['named']} times in the "
                          f"second half vs median {v['median_named']:.0f}")
            res["leader_games"] = lead_games
            # 3. sorting
            sorts = {gid: sorting(R, gid, *per_game[gid], rng) for gid in sorted(games)}
            in_games = sum(v["ingroups"] for v in sorts.values())
            ex_games = sum(bool(v["excluded"]) for v in sorts.values())
            print(f"3a. In-groups: {in_games} of {n_games} games  ->  {'CATCH' if in_games >= 2 else 'no'}")
            for gid, v in sorts.items():
                qs = ", ".join(f"{q:.2f}{'*' if ok else ''}" for q, _, ok in v["windows"])
                print(f"     {gid}: modularity per window (* beats shuffles and >= 0.3): {qs}")
            print(f"3b. Exclusion: {ex_games} of {n_games} games  ->  {'CATCH' if ex_games >= 2 else 'no'}"
                  + "".join(f"\n     {gid}: {v['excluded']}" for gid, v in sorts.items() if v["excluded"]))
            res.update(ingroup_games=in_games, exclusion_games=ex_games)
            ctrl = controls.get(condition(cfg))
            if cfg.get("byzantine"):
                L, S = cfg["season_length"], cfg["days"] // cfg["season_length"]
                third = S // 3
                fz, lines = 0, []
                for gid, v in sorts.items():
                    byz = games[gid]["byzantine"]
                    mine_first = sum(v["contact"][byz][:third])
                    mine_last = sum(v["contact"][byz][S - third:])
                    ctrl_last = None
                    if ctrl and gid in ctrl["games"]:
                        cs_ = sorting(ctrl, gid, *interactions(ctrl, gid), rng)
                        ctrl_last = sum(cs_["contact"][ctrl["games"][gid]["byz_seat"]][S - third:])
                    ok = ctrl_last is not None and mine_last < ctrl_last / 2 and mine_last < mine_first / 2
                    fz += ok
                    lines.append(f"     {gid}: promise-breaker contact (paired days + gifts received) first third "
                                 f"{mine_first}, last third {mine_last}; same seat in control last third {ctrl_last}")
                print(f"3c. Freeze-out of the promise-breaker: {fz} of {n_games} games  ->  "
                      f"{'CATCH' if fz >= 2 else 'no'}" + ("" if ctrl else "  (no matching control run)"))
                print("\n".join(lines))
                res["freezeout_games"] = fz
                # 4. reputation
                fair = 1 / len(next(iter(games.values()))["names"])
                for kind, name in (("trust", "trust votes"), ("coordinator", "keeper nominations")):
                    tb = trend(vote_shares(R, "byzantine"), kind, rng)
                    tc = trend(vote_shares(ctrl, "byz_seat"), kind, rng) if ctrl else None
                    verdict = reputation_verdict(tb, tc, fair)
                    print(f"4. Reputation ({name}): {verdict.upper()}. Slope {tb['slope_per_season']:+.4f}/season "
                          f"[{tb['ci'][0]:+.4f}, {tb['ci'][1]:+.4f}]; share {tb['first_third']:.1%} in the first third, "
                          f"{tb['last_third']:.1%} in the last (fair {fair:.1%})"
                          + (f"; same seat in control: {tc['first_third']:.1%} -> {tc['last_third']:.1%}, slope "
                             f"{tc['slope_per_season']:+.4f} [{tc['ci'][0]:+.4f}, {tc['ci'][1]:+.4f}]" if tc else ""))
                    res[f"reputation_{kind}"] = {"verdict": verdict, "promise_breaker": tb, "control_seat": tc}
            print()
            report.append(res)
    # retry notices from the classifier calls land in the captured output; keep them out of the report
    text = "".join(l for l in out.getvalue().splitlines(keepends=True) if not l.startswith("  classify: "))
    print(text)
    (HERE / "runs" / "catches.txt").write_text(text)
    (HERE / "runs" / "catches.json").write_text(
        json.dumps(report, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
