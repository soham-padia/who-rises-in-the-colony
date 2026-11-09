# Who Rises in the Colony? Research note (all findings, status, next steps)

Apart Swarm Alignment Hackathon, Track 2. Deadline: **Sunday 8 Nov 2026, 11:59 PM AoE (Monday 6:59 AM US Eastern)**.
Written Sunday ~9:10 PM ET as a handoff: everything a new session or teammate needs is here or linked from here.

## Where everything is

| What | Where |
|---|---|
| Shared doc (report draft, results, trends, team board) | https://claude.ai/artifact/7D1gE28p3cfw6jKdQp5CbH (tabs: Report draft, Team board, Results so far, Trends over 1000 days, Literature review) |
| Project PDF (20 pages, all findings) | `docs/who_rises_in_the_colony_report.pdf`; rebuild with `docs/report_build/` (see its docstring) |
| Code | `colony_sim.py` (every experiment), analysis: `compare_arms.py`, `replay.py`, `mediation.py`, `analyze_long.py`, `detect_catches.py`, `cross_model.py`, `notebook_memory.py`, `punish_analysis.py`, `belief_analysis.py` |
| Pre-registrations | `docs/preregistration.md` (long-game catches), `docs/preregistration_punish.md`, `docs/preregistration_belief.md` (with amendment) |
| Small run files | `runs/` (git). Full transcripts: Hugging Face dataset `sohampadianeu/who-rises-in-the-colony-runs` (private; last upload before the cross-model runs) |
| Literature | `docs/literature_review.md` |

## Setup in one paragraph

LLM agents live in Larkspur, a fishing colony (food is the only currency; pairing and weaving pay; a winter store is handed to an elected keeper; private trust polls). All share one 560-word system prompt and differ only in 5 randomised trait sentences + 2 placebos. A planted **promise-breaker** publicly promises food daily and never gives (engine blocks its gifts). Every run uses seed 0, so conditions replay the same colonies and compare game by game ("same seat" in control games). Settings: public **gift board** (`--public-ledger`), **private ledger** (`--private-ledger`), economies (`--economy positive|zero|negative`), `--punish`, `--target-good` + `--rumor`.

## Findings (with the caveats that matter)

1. **Traits shape behaviour, not reliably influence.** Behaviour effects replicate on gemma-4-31b and gemma-4-26b (loners pair less; assertive judged more persuasive); no influence effect is significant on both; directions agree 27/45. Placebos 0/96 (tests conservative → low power).
2. **Influence flows through contact** (mediation: loner/guarded → fewer partnerships and messages → fewer votes; chance baseline understated, chains correlated).
3. **Mechanism: victims remember the promise, not the missing gift** (`notebook_memory.py`, `runs/notebook_memory.txt`). 31b, no record: next-day notebooks record the promise 26/52/71% (pos/zero/neg) vs the missing food 3/2/7%; with the board 57–64% record non-delivery. On 26b, 5 of 6 victims at some point wrote a gift that never happened ("Gave 2 food to Dov. Dov kept his promise and gave me food."): 51% of notes no record, 26% private ledger, 11% board.
4. **Replays: the models can sanction once told.** Adding "the food X promised you has never arrived" to a victim's logged prompt cuts support ~2/3 (31b 20.3%→7.0%, 26b 40.7%→13.0%).
5. **Short (16-day) games could not detect a sanction** (one poll per game, little room to fall); the only detectable cost: −1.06 gifts under scarce food (p=0.03). Underpowered null, not "cheating is free".
6. **1000 days (31b, 12 pre-registered conditions): a public record shuts the cheat out.** With the board 0.3/0.8/1.5% of trust votes vs 8.5/9.6/9.6% without (9/9 paired games, p=0.004, post hoc; effective n≈3 colony set-ups), keeper in 0/450 terms. In zero/negative-sum the gap shows at the first poll; in positive-sum it takes ~100 days (first poll 4.2% vs 4.2%).
7. **Without a record only the zero-sum colony withdraws trust** (13.8%→6.2%, slope −0.20 pts/season; the one pre-registered reputation catch). Not explained by the notebook mechanism (zero-sum notes the missing food least) — open question.
8. **Private ledger (26b): memory does about half the board's work.** Trust share 20.8% (no record) → 14.6% (private) → 7.3% (board), same order in every colony; keeper nominations 16.7 → 5.2 → 5.2%.
9. **Cross-model (40-day, positive-sum, 3 colonies each):** 26b 20.8→7.3% (3/3); glm-5.2 9.4→4.2% (3/3; its cheat promised only ~half the days); deepseek-v4-flash ~5% either way (floor: its victims note the missing food themselves, 14%, never false gifts; no control run); gemma-4-31b 6.2→7.3% (no effect at 40 days; post-hoc: positive-sum is the slow economy); qwen3.5-397b stopped early, preliminary from transcripts 20.3→9.1% (2/3). Pooled: lower in 8/11 colony pairs (p=0.23). Every replication ran in the slowest economy → underpowered by design.
10. **Punish × board (26b, pre-registered): inconclusive.** No board: 4 punishments by others (1 at the cheat). Board: 18, 12 at the cheat (67%, chance 14%), 9 by bystanders. Rule needed ≥10 per arm; all 12 from one colony.
11. **Economies** (report draft §4.7): harsher → louder, not more punitive (explicit complaints 0.54/0.71/2.65 a season); with the board the cheat loses votes everywhere but keeps partners in negative-sum; invented institutions only in negative-sum (4 of 12 conditions; classifier unvalidated, labels 89% as rules); keepers keep 28/24/20% (fair 12.5%); Gini at day 1000 0.07/0.24/0.37 (partly mechanical: spoilage, universal weaving).
12. **Quiet incumbents (exploratory):** one member keeps the store 18–43/50 terms in all 36 long games but is not named more in talk; same members (Runa, Pell) across conditions — confounded by seed 0.
13. **Corrections made after review** (already in doc/PDF): "rotation never done" was wrong (proposals were fishing-partner schedules, sometimes followed); call-out counts inflated by the word "promise" (explicit-only counts used); judge reads notebooks (reads a confession, not evidence for oversight); "outside review" mentions removed.

## Running now: "Can you believe something into existence?"

A generous target (prosocial traits fixed, weaver) and 3 of 7 others who heard it is selfish (`--rumor prompt` daily, or `--rumor notebook` once). Twins = same colony without the rumor. gemma-4-31b, 6 colonies, 80 days, ± gift board: 6 runs in `runs/belief80/`, started 9:02 PM, ETA ~10:00–10:30 PM. Pre-registration + amendment committed before launch (`docs/preregistration_belief.md`, commits 69552f1, 0fa9ac1).
- When done: `.venv/bin/python belief_analysis.py runs/belief80` → `runs/belief80/belief_summary.txt`. Checks, per rumor mode, over 12 colony pairs: did the rumor take hold (days fishing with the target, first half), **global** confirmation (target gives non-believers less than its twin = the belief came true), relational (only to believers = reciprocity), correction (believer/non-believer gap shrinks), spread, self-concept drift (target's seasonal self-descriptions).
- Prediction: rumor takes hold; correction, not confirmation; board speeds correction; little spread.
- If the run log shows errors or it is still running at ~11 PM, report it as future work with the prediction (report draft already has a Future work section on this).

## Before submission (checklist)

1. Belief results → one paragraph + table in the report draft (doc) and PDF §8.3; commit `runs/belief80` small files.
2. Write the submission in Apart's template (`/Users/sohampadia/Downloads/Copy of Apart Research hackathon submission template.docx`: 4 pages excluding references and appendix; Introduction ~1p incl. related work, Methods + Results ~2.5p, Discussion/Limitations ~0.5p), condensed from the Report draft tab; attach `docs/who_rises_in_the_colony_reference.pdf` as the supplementary appendix. Cut the report draft to that limit; fill bracketed notes: July 2026 incident source (or drop), full titles for arXiv-only references, AI-use statement.
3. Hand-check the 30 classifier labels (`runs/classifier_check_sample.csv`) — required by the pre-registration before reporting the institution catch.
4. Rebuild the PDF (`docs/report_build`), push, re-upload transcripts to Hugging Face (`hf upload sohampadianeu/who-rises-in-the-colony-runs runs runs --repo-type dataset --exclude "*.log"`), make repo/dataset public, submit.

## Gotchas

- Adaption rate limit is per user (~40 replies/min on reasoning models). Its Terms of Service prohibit "attempting to circumvent usage limits, rate limits, or access controls" — no extra accounts; teammates' own accounts are fine.
- zsh doesn't split `$VAR` into words: wrap multi-flag commands in `bash -c '…'`.
- Never add draws to the game's main random stream in `Game.__init__` (breaks pairing); new features use their own streams.
