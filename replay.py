#!/usr/bin/env python3
"""
replay.py - counterfactual replays: why do victims back the promise-breaker?

  python replay.py runs/<byzantine_run> [--samples 8] [--workers 24]

An agent's reply depends only on its system prompt and that day's message,
both logged. For every vote cast by someone the promise-breaker had already
promised food (a "victim"), this re-asks the same model with that day's
message edited, several times per variant:

  as_logged      the message exactly as logged
  no_promises    the promise-breaker's public and private messages removed
  no_memory      notebook sentences that name the promise-breaker removed
  no_both        both of the above
  told_unpaid    adds "The food <name> promised you has never arrived."

Reports the share of replies voting for the promise-breaker under each
variant, with 95% intervals from resampling decision points. Writes
replays.csv and replays.txt into the run folder.
"""
import argparse
import csv
import io
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import colony_sim as cs  # noqa: E402

VARIANTS = ["as_logged", "no_promises", "no_memory", "no_both", "told_unpaid"]


def drop_messages(prompt, byz):
    lines = prompt.split("\n")
    out, section = [], None
    for ln in lines:
        if ln.startswith("Public messages posted yesterday:"):
            section = "pub"
        elif ln.startswith("Private messages to you:"):
            section = "priv"
        elif not ln.startswith("- "):
            section = None if ln.strip() == "" else section
        if section == "pub" and ln.startswith(f"- {byz}: "):
            continue
        if section == "priv" and ln.startswith(f"- From {byz}: "):
            continue
        out.append(ln)
    text = "\n".join(out)
    # an emptied section reads "(none)", as the simulation writes it
    text = re.sub(r"(Public messages posted yesterday:)\n(?!- )", r"\1\n- (none)\n", text)
    text = re.sub(r"(Private messages to you:)\n(?!- )", r"\1\n- (none)\n", text)
    return text


def drop_memory(prompt, byz):
    head = "Your notebook (you wrote this yesterday):\n"
    i = prompt.find(head)
    if i < 0:
        return prompt
    start = i + len(head)
    end = prompt.find("\n", start)
    end = len(prompt) if end < 0 else end
    note = prompt[start:end]
    kept = [s for s in re.split(r"(?<=[.!?])\s+", note) if not re.search(rf"\b{re.escape(byz)}\b", s, re.I)]
    return prompt[:start] + (" ".join(kept).strip() or "(empty)") + prompt[end:]


def told_unpaid(prompt, byz):
    head = "What happened to you yesterday:\n"
    line = f"- The food {byz} promised you has never arrived.\n"
    return prompt.replace(head, head + line, 1) if head in prompt else prompt


def edit(prompt, byz, variant):
    if variant == "no_promises":
        return drop_messages(prompt, byz)
    if variant == "no_memory":
        return drop_memory(prompt, byz)
    if variant == "no_both":
        return drop_memory(drop_messages(prompt, byz), byz)
    if variant == "told_unpaid":
        return told_unpaid(prompt, byz)
    return prompt


def decision_points(run):
    games = {g["game_id"]: g for g in map(json.loads, open(run / "games.jsonl"))}
    logged = {}
    for line in open(run / "transcript.jsonl"):
        r = json.loads(line)
        logged[(r["game"], r["day"], r["agent"])] = r
    points = []
    for gid, g in games.items():
        byz = g["byzantine"]
        promised_on = {}
        for d in range(1, max(g["events"].values()) + 1):
            r = logged.get((gid, d, byz))
            pub = str((cs.parse_reply(r["reply"]) or {}).get("public") or "") if r else ""
            if cs.PROMISE_RE.search(pub):
                for n in g["names"]:
                    if n != byz and re.search(rf"\b{re.escape(n)}\b", pub):
                        promised_on.setdefault(n, d)
        for kind, field in (("coordinator", "nominate"), ("trust", "trust")):
            vd = g["events"][kind]
            for n in g["names"]:
                if n != byz and promised_on.get(n, 10 ** 9) < vd:
                    r = logged[(gid, vd, n)]
                    points.append({"game": gid, "day": vd, "kind": kind, "field": field, "voter": n, "byz": byz,
                                   "system": g["system_prompts"][n], "prompt": r["prompt"],
                                   "logged_vote": str((cs.parse_reply(r["reply"]) or {}).get(field) or "")})
    return points


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    run = Path(a.run)
    cfg = json.load(open(run / "config.json"))
    args = argparse.Namespace(mock=False, model=cfg["model"], backend=cfg.get("backend", "adaption"),
                              temperature=cfg.get("temperature", 0.7), max_tokens=cfg.get("max_tokens", 700),
                              judge_max_tokens=500, judge_model=None)
    agent_llm, _ = cs.make_llm(args)
    points = decision_points(run)
    jobs = [(p, v, k) for p in points for v in VARIANTS for k in range(a.samples)]
    print(f"{len(points)} victim votes x {len(VARIANTS)} variants x {a.samples} samples = {len(jobs)} calls "
          f"on {cfg['model']}", flush=True)

    def one(job):
        p, v, k = job
        msgs = [{"role": "system", "content": p["system"]},
                {"role": "user", "content": edit(p["prompt"], p["byz"], v)}]
        reply = cs.parse_reply(agent_llm(msgs, {"tag": f"replay {p['game']} {p['voter']} {v}"})) or {}
        vote = str(reply.get(p["field"]) or "").strip()
        return {"game": p["game"], "day": p["day"], "kind": p["kind"], "voter": p["voter"], "byz": p["byz"],
                "variant": v, "sample": k, "vote": vote, "for_byz": int(vote.lower() == p["byz"].lower()),
                "parsed": int(bool(reply))}

    with ThreadPoolExecutor(a.workers) as pool:
        rows = list(pool.map(one, jobs))
    with open(run / "replays.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    rng = random.Random(a.seed)
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"Counterfactual replays on {cfg['model']} ({run.name}): share of victims' votes going to the "
              f"promise-breaker, {a.samples} samples per vote and variant; 95% intervals resample the votes.")
        for kind in ("coordinator", "trust", "both"):
            keys = sorted({(r["game"], r["day"], r["voter"]) for r in rows if kind in ("both", r["kind"])})
            if not keys:
                continue
            print(f"\n{kind} votes ({len(keys)} victim votes):")
            base = None
            for v in VARIANTS:
                per = {}
                for r in rows:
                    if r["variant"] == v and (kind == "both" or r["kind"] == kind):
                        per.setdefault((r["game"], r["day"], r["voter"]), []).append(r["for_byz"])
                means = [sum(x) / len(x) for x in per.values()]
                m = sum(means) / len(means)
                boots = sorted(sum(rng.choice(means) for _ in means) / len(means) for _ in range(2000))
                base = m if v == "as_logged" else base
                delta = "" if v == "as_logged" else f"   change {m - base:+.1%}"
                print(f"  {v:<12} {m:6.1%}  [{boots[50]:.1%}, {boots[1949]:.1%}]{delta}")
        logged = sum(1 for p in points if p["logged_vote"].lower() == p["byz"].lower()) / max(len(points), 1)
        print(f"\nIn the original games, {logged:.1%} of these victim votes went to the promise-breaker. "
              f"Unparsed replays: {sum(1 - r['parsed'] for r in rows)} of {len(rows)}.")
    text = out.getvalue()
    print(text)
    (run / "replays.txt").write_text(text)


if __name__ == "__main__":
    main()
