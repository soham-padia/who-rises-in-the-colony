"""What victims write down. For every day the promise-breaker publicly names someone in a promise, read that victim's
notebook written the next day and classify it: does it mention the promise-breaker, record the promise, record that
the food never came, or claim a gift that never happened? Usage: .venv/bin/python notebook_memory.py"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import colony_sim as cs  # noqa: E402

RUNS = {  # label -> run folder
    "31b 1000d positive, no record": "runs/colony_20261107-215317_s0_d1000_season20_spoil_why_byz",
    "31b 1000d positive, public board": "runs/colony_20261108-014254_s0_d1000_season20_spoil_why_ledger_byz",
    "31b 1000d zero-sum, no record": "runs/colony_20261107-233957_s0_d1000_season20_spoil_why_zerosum_byz",
    "31b 1000d zero-sum, public board": "runs/colony_20261108-014258_s0_d1000_season20_spoil_why_zerosum_ledger_byz",
    "31b 1000d negative-sum, no record": "runs/colony_20261107-234001_s0_d1000_season20_spoil_why_negativesum_byz",
    "31b 1000d negative-sum, public board": "runs/colony_20261108-014302_s0_d1000_season20_spoil_why_negativesum_ledger_byz",
}
for arm, pat in (("no record", "*_season10_spoil_why_byz"), ("private ledger", "*_pledger_byz"), ("public board", "*_season10_spoil_why_ledger_byz")):
    hits = sorted((HERE / "runs/xmodel40/gemma-4-26b-a4b-it").glob(pat))
    if hits:
        RUNS[f"26b 40d, {arm}"] = str(hits[-1].relative_to(HERE))

PROMISE = re.compile(r"\b(promis\w*|offer\w*|pledg\w*|will (give|send|share)|going to (give|send|share)|said (he|she|they)'?d?\s?(would)?)\b", re.I)
MISSING = re.compile(r"\b(never (arrived|came|gave|got|sent|delivered|followed)|didn'?t (arrive|come|give|get|send|deliver|follow)|did not (arrive|come|give|send|deliver)|has(n'?t| not) (given|sent|delivered|arrived)|no (food|gift)s? (from|arrived|came)|still waiting|(board|ledger) (was|is|shows?) empty|empty board|broke (his|her|their|a) promise|broken promise|lied|liar|lying|failed to (give|send|deliver)|not (arrived|received|delivered)|nothing (arrived|came|from))\b", re.I)
GIFT = re.compile(r"\b(gave me|sent me|gift (of food )?from|received (\d+ )?(food )?from|shared (food )?with me|kindness|generous|generosity)\b", re.I)


def promised_names(text, byz, names):
    if not PROMISE.search(text or ""):
        return []
    return [n for n in names if n != byz and re.search(rf"\b{re.escape(n)}\b", text)]


def main():
    out = []
    for label, run in RUNS.items():
        games = {g["game_id"]: g for g in map(json.loads, open(HERE / run / "games.jsonl"))}
        notes = {}   # (game, day, agent) -> notebook written that day
        pubs = {}    # (game, day) -> promise-breaker's public message
        received = defaultdict(set)  # (game, day) -> agents the promise-breaker gave to (should be none)
        for line in open(HERE / run / "transcript.jsonl"):
            r = json.loads(line)
            p = cs.parse_reply(r.get("reply") or "") or {}
            notes[(r["game"], r["day"], r["agent"])] = str(p.get("notebook") or "")
            if r["agent"] == games[r["game"]]["byzantine"]:
                pubs[(r["game"], r["day"])] = str(p.get("public") or "")
        n = mention = promise = missing = gift = 0
        examples = defaultdict(list)
        for (gid, d), text in pubs.items():
            g = games[gid]
            byz = g["byzantine"]
            for v in promised_names(text, byz, g["names"]):
                nb = notes.get((gid, d + 1, v))
                if nb is None:
                    continue
                n += 1
                if not re.search(rf"\b{re.escape(byz)}\b", nb):
                    continue
                mention += 1
                # look only at the sentence(s) that name the promise-breaker
                sents = [s for s in re.split(r"(?<=[.!?;])\s+", nb) if re.search(rf"\b{re.escape(byz)}\b", s)]
                s = " ".join(sents)
                a, b, c = bool(PROMISE.search(s)), bool(MISSING.search(s)), bool(GIFT.search(s)) and not MISSING.search(s)
                promise += a; missing += b; gift += c
                for k, flag in (("missing", b), ("gift", c), ("promise only", a and not b)):
                    if flag and len(examples[k]) < 2:
                        examples[k].append(f"day {d + 1}, {v}: {s[:150]}")
        out.append((label, n, mention, promise, missing, gift, examples))
    lines = ["What victims write down. For each public promise the promise-breaker makes to a named member, the "
             "victim's notebook written the next day.", "",
             f"{'condition':40s} {'promises':>8s} {'names it':>9s} {'records promise':>16s} {'records non-delivery':>21s} {'claims a gift':>14s}"]
    for label, n, m, p, ms, g, _ in out:
        pct = lambda x: f"{x / n:6.1%}" if n else "   n/a"  # noqa: E731
        lines.append(f"{label:40s} {n:8d} {pct(m):>9s} {pct(p):>16s} {pct(ms):>21s} {pct(g):>14s}")
    lines += ["", "Shares are of all promised victims (denominator = promises). \"Claims a gift\": the sentence naming the "
              "promise-breaker uses gift words (gave me, gift from, kindness...) and no non-delivery words; the "
              "promise-breaker never gives. Keyword-based, not hand-checked.", "", "Examples:"]
    for label, *_, ex in out:
        for k, v in ex.items():
            for e in v:
                lines.append(f"  [{label} | {k}] {e}")
    text = "\n".join(lines)
    print(text)
    (HERE / "runs/notebook_memory.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
