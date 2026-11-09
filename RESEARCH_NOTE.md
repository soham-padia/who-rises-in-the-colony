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
14. **Rumor pilot (interim):** a false "selfish" reputation sticks (believers shun the target and explain away its gifts) but has not come true; see the belief section below.

## Belief pilot: "Can you believe something into existence?" (running; interim results in the paper)

A generous target (prosocial traits fixed, made a weaver) and 3 of the 7 others told by a traveller that it is selfish, either `--rumor prompt` (in their system prompt every day) or `--rumor notebook` (once, in their first notebook). Twins: the same colony without the rumor. gemma-4-31b, 6 colonies, 80 days. Pre-registration: `docs/preregistration_belief.md`, plus amendments 1 (two rumor modes, fixed traits, 80 days), 2 (board arms dropped: 6 runs needed ~8.5 h at the ~45 replies/min account limit) and 3 (two board arms restored on a teammate's own account).

- **Runs in `runs/belief80/`:**
  - Soham's key, no board: none, prompt and notebook (started 9:02 PM; all 6 colonies ~1:50 AM).
  - Teammate's key (`ADAPTION_API_KEY_TEAMMATE` in `.env`, with permission; `run_belief_board.sh`), with the board: none and prompt (started 9:41 PM; ~1 AM).
  - Stopped partial board runs are in `runs/belief80/stopped/` (ignore them).
- **Analyse:**
  - `.venv/bin/python belief_interim.py` works on unfinished runs (it rebuilds the target and believers from the seed). The paper's numbers come from it; output is in `runs/belief80/belief_interim.txt`.
  - `.venv/bin/python belief_analysis.py runs/belief80` runs the pre-registered sign tests (needs finished games).
  - Then update the rumor paragraph in `docs/submission/build_submission.py` and rebuild.
- **Interim results (Sun ~10:40 PM; games at days 23–80):**
  - **Rumor in the prompt daily (6 colony pairs, 3 per board setting):** it takes hold completely.
    - Believers fished with the target on 0–3 days against 6–62 for their twins (6 of 6).
    - Believers named it negatively in 24% of replies (twins 0%) and gave it 2 of 84 trust votes (twins 27 of 80).
    - Believers explain its generosity away ("Nils is pretending to be generous"). Believers who got food from it still gave 0 of 48 trust votes.
    - The target has not turned bad so far: 83 against 70 food given; it calls itself generous every season; it never notes being shunned.
    - No spread was detected: non-believers 0 of 1,118 negative replies. They take up the cooperation and give it more trust (30 of 110 against 14 of 111).
    - The board has not corrected the belief by day 44.
  - **Rumor in the notebook once:** weak (3% negative mentions) and varies by colony. In colony 0 the shunned target got poorer (11 against 18 food) and gave 2 against 23 food by day 23: the poverty route to confirmation. Watch this colony.

## Before submission (checklist)

1. Belief results → one paragraph + table in the report draft (doc) and PDF §8.3; commit `runs/belief80` small files.
2. **Submission draft done (Sunday ~10:45 PM):** `docs/submission/who_rises_submission.docx` + `.pdf`, built from Apart's template by `docs/submission/build_submission.py` (all text lives in that script; PDF via Microsoft Word). Affiliations done (all Northeastern). Open items: the team's own rewrite (template asks that the final version be primarily team-written), belief results if they land. Original plan: write the submission in Apart's template (`/Users/sohampadia/Downloads/Copy of Apart Research hackathon submission template.docx`: 4 pages excluding references and appendix; Introduction ~1p incl. related work, Methods + Results ~2.5p, Discussion/Limitations ~0.5p), condensed from the Report draft tab; attach `docs/who_rises_in_the_colony_reference.pdf` as the supplementary appendix. Cut the report draft to that limit; fill bracketed notes: July 2026 incident source (or drop), full titles for arXiv-only references, AI-use statement.
3. Hand-check the 30 classifier labels (`runs/classifier_check_sample.csv`) — required by the pre-registration before reporting the institution catch.
4. Rebuild the PDF (`docs/report_build`), push, re-upload transcripts to Hugging Face (`hf upload sohampadianeu/who-rises-in-the-colony-runs runs runs --repo-type dataset --exclude "*.log"`), make repo/dataset public, submit.

## Gotchas

- Adaption rate limit is per user (~40 replies/min on reasoning models). Its Terms of Service prohibit "attempting to circumvent usage limits, rate limits, or access controls" — no extra accounts; teammates' own accounts are fine.
- zsh doesn't split `$VAR` into words: wrap multi-flag commands in `bash -c '…'`.
- Never add draws to the game's main random stream in `Game.__init__` (breaks pairing); new features use their own streams.

## Literature: audit of anon_lit_review.md (subagent, all 31 arXiv IDs checked; classics checked from memory only)

- **Add (cite and distinguish):** El Mir, Takáč & Lahlou 2026, "Byzantine Cheap Talk", NETYS, arXiv:2606.07790 (closest prior art: agents detect betrayal within a round but do not adapt); Piatti et al. 2024, GovSim, NeurIPS, arXiv:2404.16698 (nearest environment); Hu, Rong & Van Kleek 2026, FAccT, arXiv:2605.30169 (preconditions incl. memory, observability, sanction sensitivity); Tewolde et al. 2026, CoopEval, ICML, arXiv:2604.15267; Hammond et al. 2025, arXiv:2502.14143.
- **Belief study:** Merton 1948 (Antioch Review 8(2):193–210); Rosenthal & Jacobson 1968; Word, Zanna & Cooper 1974 (JESP 10(2):109–120); Snyder, Tanke & Berscheid 1977 (JPSP 35(9):656–666); Jussim & Harber 2005 (PSPR 9(2):131–155); Pataranutaporn et al. 2023, Nature Machine Intelligence, doi:10.1038/s42256-023-00720-7 (LLM behavioural-confirmation loop: so do not claim "no prior work"); Savcisens et al. 2026, arXiv:2607.27512; Dong et al. 2025 (memory injection), NeurIPS, arXiv:2503.03704 for dual-use.
- **Fix in our references:** Shi et al. 2026b is an ICML 2026 workshop paper; Ren et al. 2025's current title is "Reputation as a Solution to Cooperation Collapse in LLM-based MASs" (AAMAS 2026).
- **Do not use:** the review's drop-in Related Work paragraph; "Kemeklis & Vemuri 2026" (not found; only a LessWrong proposal: cite that post if using the omission-vs-commission framing); "LLMs punish readily/more harshly" (contradicts Guzman Piedrahita; only Liu et al. supports it); "forgive indefinitely", "board restores sanction from the first poll", and unhedged novelty claims.

## Superseded claims in the appended working documents

The reference PDF appends working documents written during the hackathon. Where they conflict with the submission or the report, the submission is authoritative. Known superseded claims:

- **Literature review tab:** "Victims' notebooks record the gift as missing 34% (31b) and 64% (26b) of the time, so they do remember." This was an early, broad keyword count on the 16-day games. The final measure (`notebook_memory.py`: the victim's notebook on the day after each public promise) gives 2–7% without a record on gemma-4-31b's long games and 2% on gemma-4-26b's 40-day games.
- **Report draft tab:** "loses almost all trust from the first poll onwards." In the positive-sum economy the gap takes about 100 days (first poll 4.2% in both arms).
- **Earlier drafts:** "rotation was never done" (the proposals were fishing-partner schedules, sometimes followed); call-out rates that counted the word "promise" (replaced by explicit-only counts); "10x" call-out claims; any reading of the judge's honesty rating as detected deception (it reads the promise-breaker's own notebook).
- **"Memory does half the work, publicity the rest":** the private ledger achieved about 46% of the board's reduction in trust in one 40-day gemma-4-26b pilot. That is a comparison of two treatments, not a causal decomposition.
- **"9 of 9 paired games, p = 0.004":** the 9 pairs are 3 colony set-ups in 3 economies. Every board game (0.0–2.2%) sits below every no-board game (4.5–13.8%), but at the set-up level the effect is 3 of 3 (p = 0.25).
- **Replay intervals that resample votes:** game-clustered intervals are gemma-4-31b −13.3 points [−22.8, −6.0] and gemma-4-26b −27.7 [−37.9, −19.5].
