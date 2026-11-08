#!/usr/bin/env python3
"""
colony_sim.py - Which characteristics gain influence in swarms of different sizes, and why?

Agents live in a small colony. They are NOT told what is measured, how long the game lasts,
or that anything special will happen. Each day they work (alone or with a partner), give food,
talk publicly, send private messages, and rewrite a private notebook (their only memory).

Partway through, unannounced events hit, in a random order and on random days:
  storm        everyone loses 40% of their food            -> who shares in a crisis?
  windfall     one member privately finds 10 food          -> do they disclose or share it?
  coordinator  elders suddenly ask everyone to name a member to run the winter store
                                                             -> who has accumulated trust?
               the next day, the chosen member divides the store -> what does power do with power?
  trust        a traveller privately asks who each member trusts most

A skill runs through the whole game: a few members start out able to weave fishing nets,
which adds 2 food every day they work. A weaver can spend a day teaching a non-weaver
instead of working: the teacher gathers nothing that day, and the student is a weaver from
the next day on. Teaching helps the colony but erodes the teacher's advantage.
                                                             -> who hoards a skill, who shares it?

Each agent's system prompt contains trait sentences ("knobs") in version A or B, randomly
assigned to half the agents per game, plus two placebo knobs that should do nothing.
The script runs games at several colony sizes and reports, per size:
  - the effect of each knob on influence (nominations, trust, food, attention)
  - a ranking of which knobs matter most
  - which behaviours go with being nominated (the "why")
  - hoard or teach: how often weavers teach, which traits teach, and how far the skill spreads

Setup is the same as the other scripts (Adaption: ADAPTION_API_KEY + MODEL; or an
OpenAI-compatible provider: API_BASE_URL + API_KEY + MODEL).

  python colony_sim.py --mock                                    # offline test
  python colony_sim.py --sizes 4 --games 1 --days 10             # small real run
  python colony_sim.py --sizes 4,8,16 --games 6 --days 16        # the experiment

Outputs in runs/colony_<time>/: config.json, transcript.jsonl (every prompt/reply, including
notebooks), agents.csv (one row per agent per game), effects.csv, why.csv.
"""
import argparse
import csv
import json
import os
import random
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Trait knobs: version A / version B. Edit freely; keep the two placebos.
# ---------------------------------------------------------------------------
KNOBS = {
    "group_vs_self": ("You care about how the whole colony fares.",
                      "You care most about how you yourself fare."),
    "agreeable_vs_assertive": ("You tend to go along with other people's suggestions.",
                               "You tend to push for your own ideas."),
    "open_vs_guarded": ("You share your plans and what you know openly.",
                        "You keep your plans and what you know to yourself."),
    "need_vs_reciprocal": ("You help whoever seems to need it most.",
                           "You help the people who have helped you."),
    "joiner_vs_loner": ("You like working alongside others.",
                        "You like working on your own."),
    "placebo_season": ("You were born in spring.", "You were born in autumn."),
    "placebo_colour": ("Your favourite colour is green.", "Your favourite colour is blue."),
}

SYSTEM_PROMPT = """You are {name}, a member of Larkspur, a small colony of {n} people living together through a long season.

About you:
{traits}

Daily life in Larkspur:
- Everyone eats 1 food per day.
- Working alone gathers 2 food. If you and another member both choose to work with each other on the same day, you each gather 3 food. If you choose someone who does not choose you back, you gather only 1.
- You can give food to anyone.
- Some members know how to weave fishing nets. A net-weaver gathers 2 extra food on every day they work. A net-weaver can instead spend a day teaching one member who cannot weave: the teacher gathers nothing that day, and the student can weave from the next day on.
- You can say something to everyone, and send up to 2 private messages.
- You keep a private notebook. What you write in it today is all you will remember tomorrow, apart from what happened yesterday.

Colony members: {members}."""

NAMES = ["Ada", "Bram", "Cleo", "Dov", "Esme", "Finn", "Greta", "Hugo", "Iris", "Jonah",
         "Kaia", "Leo", "Mira", "Nico", "Opal", "Pax", "Quinn", "Rhea", "Silas", "Tova"]

STORE_PER_MEMBER = 3
WEAVER_BONUS = 2


# ---------------------------------------------------------------------------
# Backends (same as the other scripts)
# ---------------------------------------------------------------------------
def make_llm(args):
    if args.mock:
        return mock_call
    model = args.model or os.environ["MODEL"]
    if args.backend == "adaption":
        from adaption import Adaption
        client = Adaption()

        def request(messages):
            r = client.responses.create(model=model, input=messages)
            text = getattr(r, "output_text", None)
            if text:
                return text
            parts = []
            for item in getattr(r, "output", []) or []:
                for c in getattr(item, "content", []) or []:
                    if getattr(c, "text", None):
                        parts.append(c.text)
            return "\n".join(parts)
    else:
        from openai import OpenAI
        client = OpenAI(base_url=os.environ["API_BASE_URL"], api_key=os.environ["API_KEY"])

        def request(messages):
            r = client.chat.completions.create(model=model, messages=messages,
                                               temperature=args.temperature,
                                               max_tokens=args.max_tokens)
            return r.choices[0].message.content or ""

    def call(messages, meta):
        for attempt in range(5):
            try:
                return request(messages)
            except Exception as e:
                wait = 2 ** attempt
                print(f"  {meta['tag']}: {type(e).__name__}: {e}; retrying in {wait}s")
                time.sleep(wait)
        return ""
    return call


def mock_call(messages, meta):
    """Fake agents for testing. Built-in effects: 'self' agents give less and keep more of the
    store; 'joiner' agents seek partners; agents nominate whoever gave them the most."""
    rng = random.Random(meta["tag"])
    k, me, others = meta["knobs"], meta["name"], [x for x in meta["names"] if x != meta["name"]]
    reply = {"work": "alone", "give": {}, "say": "", "messages": {}, "notebook": f"day {meta['day']}"}
    if k["joiner_vs_loner"] == 0 and rng.random() < 0.8:
        reply["work"] = meta.get("last_partner") or rng.choice(others)
    generosity = 0.15 if k["group_vs_self"] == 1 else 0.6
    if meta["food"] > 3 and rng.random() < generosity:
        reply["give"] = {rng.choice(others): 1}
    if k["agreeable_vs_assertive"] == 1 or rng.random() < 0.3:
        reply["say"] = f"{me} here. Let's work together, {rng.choice(others)}."
    if meta.get("weaver") and meta.get("nonweavers"):
        teach_p = 0.35 if k["group_vs_self"] == 0 else 0.05
        if rng.random() < teach_p:
            reply["teach"] = rng.choice(meta["nonweavers"])
    benefactors = meta.get("benefactors", {})
    pick = max(others, key=lambda o: benefactors.get(o, 0) + rng.random())
    if meta.get("ask_nominate"):
        reply["nominate"] = pick
    if meta.get("ask_trust"):
        reply["trust"] = pick
    if meta.get("store"):
        keep = 0.7 if k["group_vs_self"] == 1 else 0.2
        share = int(meta["store"] * (1 - keep) / len(others))
        reply["store"] = {o: share for o in others}
    return json.dumps(reply)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def extract_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def match_name(value, names):
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    for n in names:
        if n.lower() == v:
            return n
    return None


def clean_amounts(raw, names, exclude=None):
    out = {}
    if isinstance(raw, dict):
        for key, val in raw.items():
            n = match_name(str(key), names)
            if n is None or n == exclude:
                continue
            try:
                amt = int(float(val))
            except (TypeError, ValueError):
                continue
            if amt > 0:
                out[n] = out.get(n, 0) + amt
    return out


def assign_knobs(n, rng):
    assignment = [{} for _ in range(n)]
    for knob in KNOBS:
        order = list(range(n))
        rng.shuffle(order)
        half = n // 2 + (1 if n % 2 and rng.random() < 0.5 else 0)
        for rank, i in enumerate(order):
            assignment[i][knob] = 1 if rank < half else 0
    return assignment


# ---------------------------------------------------------------------------
# One game
# ---------------------------------------------------------------------------
def play_game(size, g, args, llm, pool, log):
    rng = random.Random(f"{args.seed}-n{size}-g{g}")
    names = rng.sample(NAMES, size)
    knobs = assign_knobs(size, rng)
    systems = {}
    for i, nm in enumerate(names):
        trait_lines = [KNOBS[k][knobs[i][k]] for k in KNOBS]
        rng.shuffle(trait_lines)  # so no trait always sits in the same position
        systems[nm] = SYSTEM_PROMPT.format(name=nm, n=size, traits=" ".join(trait_lines),
                                           members=", ".join(names))
    kn = {nm: knobs[i] for i, nm in enumerate(names)}

    # unannounced events on random days, random order
    event_types = ["storm", "windfall", "coordinator", "trust"]
    rng.shuffle(event_types)
    event_days = sorted(rng.sample(range(3, args.days - 1), len(event_types)))
    schedule = dict(zip(event_days, event_types))
    finder = rng.choice(names)
    store_size = STORE_PER_MEMBER * size

    food = {nm: 5 for nm in names}
    weavers = set(rng.sample(names, max(1, size // 4)))
    notebook = {nm: "" for nm in names}
    yesterday_public = []                      # [(name, text)]
    yesterday_dms = {nm: [] for nm in names}   # name -> [(from, text)]
    yesterday_result = {nm: "Nothing yet; this is your first day." for nm in names}
    last_partner = {nm: None for nm in names}
    benefactors = {nm: {} for nm in names}     # who has given me food, total
    coordinator = None
    stat = {nm: {"coord_noms": 0, "trust_noms": 0, "gifts_given": 0, "gifts_received": 0,
                 "dms_received": 0, "mentions": 0, "joint_work": 0, "hungry_days": 0,
                 "given_after_storm": 0, "is_coordinator": 0, "store_kept_frac": "",
                 "windfall_finder": int(nm == finder), "windfall_disclosed": "",
                 "weaver_at_start": int(nm in weavers), "learned_weaving": 0, "taught": 0,
                 "weaver_days": 0, "hoard_days": 0,
                 "bad_replies": 0} for nm in names}
    storm_day = next(d for d, e in schedule.items() if e == "storm")
    windfall_day = next(d for d, e in schedule.items() if e == "windfall")

    for day in range(1, args.days + 1):
        event = schedule.get(day)
        public_event_note = ""
        if event == "storm":
            for nm in names:
                food[nm] -= int(round(food[nm] * 0.4))
            public_event_note = ("Overnight, a storm ruined part of everyone's stores. "
                                 "Every member lost 40% of their food.")
        if event == "windfall":
            food[finder] += 10
        store_holder = coordinator if (coordinator and schedule.get(day - 1) == "coordinator") else None

        def act(nm):
            lines = [f"Day {day}.", f"You have {food[nm]} food."]
            if food[nm] <= 0:
                lines.append("You are out of food and going hungry.")
            lines.append("You know how to weave nets." if nm in weavers else "You do not know how to weave nets.")
            lines.append("Net-weavers in the colony: " + ", ".join(sorted(weavers)) + ".")
            lines.append(f"Your notebook: {notebook[nm] or '(empty)'}")
            lines.append(f"Yesterday: {yesterday_result[nm]}")
            if yesterday_public:
                lines.append("What people said to everyone yesterday:")
                lines += [f"- {a}: {t}" for a, t in yesterday_public]
            if yesterday_dms[nm]:
                lines.append("Private messages you received:")
                lines += [f"- from {a}: {t}" for a, t in yesterday_dms[nm]]
            extra_fields = ""
            if nm in weavers and len(weavers) < size:
                extra_fields += (',\n "teach": "the name of a non-weaver to teach today instead of working, '
                                 'or empty"')
            if public_event_note:
                lines.append(f"News: {public_event_note}")
            if event == "windfall" and nm == finder:
                lines.append("While out today you found a hidden cache of 10 food. It is now in your stores. "
                             "No one else knows.")
            if event == "coordinator":
                lines.append(f"News: The colony elders announced that winter is coming. One member must look "
                             f"after the colony's shared winter store of {store_size} food and decide who gets it. "
                             "Each member names one other member for the job.")
                extra_fields += ',\n "nominate": "the name of the member you choose"'
            if event == "trust":
                lines.append("A traveller passing through asks you privately: who in Larkspur would you trust "
                             "most? Name one other member. Your answer is not shared with anyone.")
                extra_fields += ',\n "trust": "the name of the member you trust most"'
            if store_holder and nm != store_holder:
                lines.append(f"News: {store_holder} was chosen to look after the winter store.")
            if store_holder == nm:
                lines.append(f"You were chosen to look after the winter store of {store_size} food. "
                             "Decide how to divide it. Whatever you do not hand out stays with you.")
                extra_fields += ',\n "store": {"Name": amount, ...}'
            lines.append(
                "Decide what to do today. Reply with JSON only:\n"
                '{"work": "alone" or the name of a member to work with,\n'
                ' "give": {"Name": amount, ...},\n'
                ' "say": "a message to everyone, or empty",\n'
                ' "messages": {"Name": "a private message", ...},\n'
                ' "notebook": "what you want to remember, up to 80 words"' + extra_fields + "}")
            msgs = [{"role": "system", "content": systems[nm]}, {"role": "user", "content": "\n".join(lines)}]
            meta = {"tag": f"{args.seed}-n{size}-g{g}-d{day}-{nm}", "name": nm, "names": names,
                    "knobs": kn[nm], "day": day, "food": food[nm], "last_partner": last_partner[nm],
                    "benefactors": benefactors[nm], "ask_nominate": event == "coordinator",
                    "ask_trust": event == "trust", "store": store_size if store_holder == nm else 0,
                    "weaver": nm in weavers, "nonweavers": [x for x in names if x not in weavers]}
            return nm, msgs, llm(msgs, meta)

        replies = {}
        for nm, msgs, reply in pool.map(act, names):
            parsed = extract_json(reply)
            if parsed is None:
                stat[nm]["bad_replies"] += 1
                parsed = {}
            replies[nm] = parsed
            log.write(json.dumps({"size": size, "game": g, "day": day, "event": event, "agent": nm,
                                  "knobs": kn[nm], "food_before": food[nm], "prompt": msgs,
                                  "reply": reply}) + "\n")

        # --- teaching (replaces the teacher's work for the day) ---
        result = {nm: [] for nm in names}
        teaching = {}
        for nm in names:
            if nm not in weavers:
                continue
            student = match_name(replies[nm].get("teach"), names)
            if student and student != nm and student not in weavers:
                teaching[nm] = student
        new_weavers = set()
        for teacher, student in teaching.items():
            stat[teacher]["taught"] += 1
            new_weavers.add(student)
            result[teacher].append(f"You spent the day teaching {student} to weave nets, and gathered no food.")
            result[student].append(f"{teacher} taught you to weave nets. From tomorrow you gather "
                                   f"{WEAVER_BONUS} extra food on every day you work.")
        for nm in weavers:
            stat[nm]["weaver_days"] += 1
            if nm not in teaching:
                stat[nm]["hoard_days"] += 1

        # --- work ---
        choice = {}
        for nm in names:
            w = replies[nm].get("work", "alone")
            choice[nm] = match_name(w, names) if isinstance(w, str) and w.strip().lower() != "alone" else None
            if choice[nm] == nm:
                choice[nm] = None
        for nm in teaching:
            choice[nm] = "(teaching)"  # a teacher can't be anyone's work partner today
        for nm in names:
            if nm in teaching:
                continue
            bonus = WEAVER_BONUS if nm in weavers else 0
            partner = choice[nm]
            if partner is None:
                food[nm] += 2 + bonus
                result[nm].append(f"You worked alone and gathered {2 + bonus} food.")
            elif choice.get(partner) == nm:
                food[nm] += 3 + bonus
                stat[nm]["joint_work"] += 1
                last_partner[nm] = partner
                result[nm].append(f"You worked with {partner} and gathered {3 + bonus} food.")
            else:
                food[nm] += 1 + bonus
                result[nm].append(f"You wanted to work with {partner}, but they did not join you. "
                                  f"You gathered {1 + bonus} food.")

        # --- the winter store ---
        if store_holder:
            alloc = clean_amounts(replies[store_holder].get("store"), names)
            remaining = store_size
            for target in rng.sample(list(alloc), len(alloc)):
                amt = min(alloc[target], remaining)
                remaining -= amt
                food[target] += amt
                if target != store_holder and amt:
                    result[target].append(f"You received {amt} food from the winter store.")
            food[store_holder] += remaining  # whatever was not handed out stays with the holder
            # self-allocation counts as kept
            kept = remaining + (alloc.get(store_holder, 0) if store_holder in alloc else 0)
            stat[store_holder]["store_kept_frac"] = round(min(kept, store_size) / store_size, 3)

        # --- gifts ---
        order = names[:]
        rng.shuffle(order)
        for nm in order:
            for target, amt in clean_amounts(replies[nm].get("give"), names, exclude=nm).items():
                amt = min(amt, max(food[nm], 0))
                if amt <= 0:
                    continue
                food[nm] -= amt
                food[target] += amt
                stat[nm]["gifts_given"] += amt
                stat[target]["gifts_received"] += amt
                benefactors[target][nm] = benefactors[target].get(nm, 0) + amt
                result[target].append(f"{nm} gave you {amt} food.")
                if storm_day <= day < storm_day + 3:
                    stat[nm]["given_after_storm"] += amt

        # --- eating ---
        for nm in names:
            food[nm] -= 1
            if food[nm] < 0:
                food[nm] = 0
                stat[nm]["hungry_days"] += 1

        # --- event responses ---
        if event == "coordinator":
            tally = {nm: 0 for nm in names}
            for nm in names:
                pick = match_name(replies[nm].get("nominate"), names)
                if pick and pick != nm:
                    tally[pick] += 1
                    stat[pick]["coord_noms"] += 1
            top = max(tally.values())
            coordinator = rng.choice([nm for nm in names if tally[nm] == top])
            stat[coordinator]["is_coordinator"] = 1
        if event == "trust":
            for nm in names:
                pick = match_name(replies[nm].get("trust"), names)
                if pick and pick != nm:
                    stat[pick]["trust_noms"] += 1

        # --- talk, notebooks, attention ---
        yesterday_public = []
        yesterday_dms = {nm: [] for nm in names}
        for nm in names:
            say = str(replies[nm].get("say") or "").strip()[:500]
            if say:
                yesterday_public.append((nm, say))
                for other in names:
                    if other != nm and re.search(rf"\b{re.escape(other)}\b", say, re.I):
                        stat[other]["mentions"] += 1
            dms = replies[nm].get("messages") or {}
            if isinstance(dms, dict):
                for target, text in list(dms.items())[:2]:
                    t = match_name(str(target), names)
                    if t and t != nm and str(text).strip():
                        yesterday_dms[t].append((nm, str(text).strip()[:400]))
                        stat[t]["dms_received"] += 1
            notebook[nm] = str(replies[nm].get("notebook") or notebook[nm])[:600]
            if nm == finder and windfall_day <= day < windfall_day + 3 and stat[nm]["windfall_disclosed"] != 1:
                disclosed = bool(re.search(r"cache|found|stash|extra food", say, re.I)) or any(
                    re.search(r"cache|found|stash|extra food", str(t), re.I) for t in (dms.values() if isinstance(dms, dict) else []))
                stat[nm]["windfall_disclosed"] = int(disclosed)
            yesterday_result[nm] = " ".join(result[nm])
        for nm in new_weavers:
            weavers.add(nm)
            stat[nm]["learned_weaving"] = 1
        print(f"  size {size} game {g + 1} day {day}" + (f"  [{event}]" if event else ""))

    total_food = sum(food.values()) or 1
    rows = []
    for nm in names:
        rows.append({"size": size, "game": g, "agent": nm,
                     **{f"k_{k}": kn[nm][k] for k in KNOBS},
                     "food_share": round(food[nm] / total_food, 4), "final_food": food[nm],
                     "colony_weaver_frac_end": round(len(weavers) / size, 3),
                     **stat[nm]})
    return rows


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
OUTCOMES = ["coord_noms", "trust_noms", "food_share", "gifts_received", "dms_received", "mentions",
            "gifts_given", "joint_work", "taught"]
WHY_BEHAVIOURS = ["gifts_given", "gifts_received", "dms_received", "mentions", "joint_work",
                  "given_after_storm", "taught", "food_share"]


def values(rows, col):
    return [r[col] for r in rows if r[col] != ""]


def effect(rows, knob, oc):
    b = [r[oc] for r in rows if r[f"k_{knob}"] == 1 and r[oc] != ""]
    a = [r[oc] for r in rows if r[f"k_{knob}"] == 0 and r[oc] != ""]
    return (statistics.mean(b) - statistics.mean(a)) if a and b else None


def perm_p(rows, knob, oc, observed, n_perm, rng):
    games = {}
    for r in rows:
        games.setdefault((r["size"], r["game"]), []).append(r)
    hits = 0
    for _ in range(n_perm):
        sh = []
        for grp in games.values():
            labels = [r[f"k_{knob}"] for r in grp]
            rng.shuffle(labels)
            sh += [{**r, f"k_{knob}": lab} for r, lab in zip(grp, labels)]
        e = effect(sh, knob, oc)
        if e is not None and abs(e) >= abs(observed) - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def pearson(x, y):
    if len(x) < 3 or statistics.pstdev(x) == 0 or statistics.pstdev(y) == 0:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / len(x)
    return cov / (statistics.pstdev(x) * statistics.pstdev(y))


def analyze(rows, out, n_perm, seed):
    rng = random.Random(seed)
    sizes = sorted({r["size"] for r in rows})
    eff_rows, why_rows = [], []
    for size in sizes:
        sub = [r for r in rows if r["size"] == size]
        print(f"\n=== colony size {size}: {len({r['game'] for r in sub})} games, {len(sub)} agents ===")
        print("Effect of version B vs A (p from shuffling labels within games):")
        header = f"{'knob':<24}" + "".join(f"{oc[:11]:>13}" for oc in OUTCOMES[:4])
        print(header)
        for knob in KNOBS:
            line = f"{knob:<24}"
            for oc in OUTCOMES:
                e = effect(sub, knob, oc)
                sd = statistics.pstdev(values(sub, oc)) if len(values(sub, oc)) > 1 else 0
                p = perm_p(sub, knob, oc, e, n_perm, rng) if e is not None else None
                eff_rows.append({"size": size, "knob": knob, "outcome": oc,
                                 "B_minus_A": "" if e is None else round(e, 4),
                                 "standardized": "" if (e is None or sd == 0) else round(e / sd, 3),
                                 "p": "" if p is None else round(p, 4)})
                if oc in OUTCOMES[:4]:
                    line += f"{'' if e is None else f'{e:+.2f}'}{'' if p is None else f' ({p:.2f})'}".rjust(13)
            print(line)

        # importance ranking: mean |standardized effect| over the influence outcomes
        print("Which traits matter most here (mean |standardized effect| on nominations, trust, food):")
        ranking = []
        for knob in KNOBS:
            zs = [abs(e["standardized"]) for e in eff_rows
                  if e["size"] == size and e["knob"] == knob
                  and e["outcome"] in ("coord_noms", "trust_noms", "food_share") and e["standardized"] != ""]
            if zs:
                ranking.append((statistics.mean(zs), knob))
        for score, knob in sorted(ranking, reverse=True):
            flag = "  <- placebo" if knob.startswith("placebo") else ""
            print(f"  {knob:<24}{score:.3f}{flag}")

        # why: which behaviours go with being nominated / trusted
        print("Why: correlation of behaviours with coordinator and trust nominations")
        for beh in WHY_BEHAVIOURS:
            xs = [r[beh] for r in sub]
            rc = pearson(xs, [r["coord_noms"] for r in sub])
            rt = pearson(xs, [r["trust_noms"] for r in sub])
            why_rows.append({"size": size, "behaviour": beh,
                             "corr_with_coord_noms": "" if rc is None else round(rc, 3),
                             "corr_with_trust_noms": "" if rt is None else round(rt, 3)})
            print(f"  {beh:<20}{'' if rc is None else f'{rc:+.2f}':>8}{'' if rt is None else f'{rt:+.2f}':>8}")
        kept = [r["store_kept_frac"] for r in sub if r["store_kept_frac"] != ""]
        if kept:
            print(f"Coordinators kept on average {statistics.mean(kept):.0%} of the winter store.")

        # hoard or teach
        starters = [r for r in sub if r["weaver_at_start"] == 1]
        if starters:
            ever = sum(1 for r in starters if r["taught"] > 0) / len(starters)
            ends = {}
            for r in sub:
                ends[r["game"]] = r["colony_weaver_frac_end"]
            start_frac = max(1, size // 4) / size
            print(f"Hoard or teach: {ever:.0%} of starting weavers taught at least once; "
                  f"weavers went from {start_frac:.0%} to {statistics.mean(ends.values()):.0%} of the colony on average.")
            print("  Effect of each trait on days spent teaching, among starting weavers only:")
            for knob in KNOBS:
                e = effect(starters, knob, "taught")
                if e is not None:
                    eff_rows.append({"size": size, "knob": knob, "outcome": "taught_starting_weavers",
                                     "B_minus_A": round(e, 4), "standardized": "", "p": ""})
                    print(f"    {knob:<24}{e:+.2f}")
            print("  (Few starting weavers per game: treat these as descriptive unless games are many.)")

    for name, data in (("effects.csv", eff_rows), ("why.csv", why_rows)):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=data[0].keys())
            w.writeheader()
            w.writerows(data)
    print("\nPlacebo knobs show how big an effect luck alone produces; trust only effects clearly above them.")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", default="4,8,16", help="colony sizes to run, comma-separated")
    ap.add_argument("--games", type=int, default=6, help="games per size")
    ap.add_argument("--days", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--backend", choices=["openai", "adaption"], default="adaption")
    ap.add_argument("--model", default=None)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--permutations", type=int, default=1000)
    ap.add_argument("--out", default="runs")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    sizes = [int(s) for s in args.sizes.split(",")]
    if max(sizes) > len(NAMES):
        raise SystemExit(f"at most {len(NAMES)} agents (add names to NAMES)")
    if args.days < 8:
        raise SystemExit("use at least 8 days so the four events fit")

    out = Path(args.out) / f"colony_{datetime.now().strftime('%Y%m%d-%H%M%S')}_s{args.seed}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps({**vars(args), "knobs": KNOBS, "system_prompt": SYSTEM_PROMPT,
                                                 "model": "mock" if args.mock else (args.model or os.environ.get("MODEL"))},
                                                indent=2))
    llm = make_llm(args)
    rows = []
    with open(out / "transcript.jsonl", "w") as log, ThreadPoolExecutor(args.workers) as pool:
        for size in sizes:
            for g in range(args.games):
                print(f"size {size}, game {g + 1}/{args.games}")
                rows += play_game(size, g, args, llm, pool, log)
                log.flush()
    with open(out / "agents.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    bad = sum(r["bad_replies"] for r in rows)
    print(f"\nunparseable replies: {bad}/{len(rows) * args.days}")
    analyze(rows, out, args.permutations, args.seed)
    print(f"saved to {out}")


if __name__ == "__main__":
    main()