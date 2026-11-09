"""Build the Apart hackathon submission (docs/submission/who_rises_submission.docx) from Apart's template.

Keeps the template's title block, styles and footnote; replaces the guidance text with the paper below.
Usage: .venv/bin/python docs/submission/build_submission.py   (then convert to PDF with LibreOffice)
"""
import re
import shutil
import struct
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TEMPLATE = HERE / "apart_template.docx"
OUT = HERE / "who_rises_submission.docx"
FIGS = {"f1": REPO / "docs/report_build/f1_replays.png", "f2": REPO / "docs/report_build/f2_trust.png"}

TITLE = "Who Rises in the Colony? Broken Promises, Memory and Public Records in a Society of LLM Agents"
AUTHORS = [('Soham Himanshubhai Padia', 'Northeastern University'), ('Max Eng', 'Northeastern University'), ('Elaine Ly', 'Northeastern University')]

ABSTRACT = (
    "Agent swarms are often built from copies of one model that differ only in a few lines of "
    "instructions. We ask which of those differences turn into influence, and what lets such a group hold "
    "a dishonest member to account. LLM agents share one system prompt for a fishing colony and differ "
    "only in five randomised trait sentences and two placebos. Across 234 sixteen-day games, 36 "
    "thousand-day games (3 colony set-ups per condition) and 40-day pilots on five models, we measure "
    "keeper votes, private trust polls and food, and plant a colonist who promises food every day and "
    "never gives it. Prompted traits reliably change behaviour, but we found no influence effect that "
    "replicates across models. What protects the cheat is what agents keep in memory: victims' "
    "self-written notebooks recorded the promise far more often than the missing food (26–71% against "
    "2–7% on gemma-4-31b), and one added sentence stating that the food never arrived cuts their support "
    "by about two thirds. Over 1000 days, a public record of gifts shuts the promise-breaker out: it "
    "draws 0.3–1.5% of trust votes against 8.5–9.6% without the record, and every game with the record "
    "sits below every game without it. In a separate 40-day pilot, a private ledger achieved about half "
    "of the board's reduction in trust. Explicit, durable records of commitments and deliveries look like "
    "a cheap safeguard for multi-agent systems.")

# Body: (kind, content). kinds: h2, h3, p, num, bullet, ref, fig, table, cap, tcap
BODY = [
    ("h2", "1. Introduction"),
    ("p", "Large deployments of AI agents are increasingly populations of one model: the same weights, the same "
         "scaffold, and a few lines of role or persona text that differ from agent to agent. Safety "
         "evaluations mostly test those agents one at a time. In a population, however, influence is allocated "
         "socially: some agents get listened to, trusted and handed control of shared resources. If certain "
         "dispositions reliably rise, a swarm selects for them whether or not anyone intended it; and if a "
         "dishonest member can keep the group's trust, the group cannot police itself."),
    ("p", "We study both questions in a small, fully logged society. Agents live in Larkspur, a fishing colony "
         "where food is the only currency, cooperation pays, a valuable skill can be hoarded or taught, and "
         "unannounced events ask the colony to choose a keeper for its winter store and, privately, whom it "
         "trusts. All agents share one system prompt and differ only in a few randomly assigned trait "
         "sentences. We then plant one colonist who publicly promises food to a hungry member every day and "
         "never gives it."),
    ("p", "**Our main contributions are:**"),
    ("num", "**A paired testbed** for influence and accountability in LLM populations: seeded games are identical "
           "across conditions, so every intervention is compared game by game, and placebo traits calibrate "
           "chance findings."),
    ("num", "**Traits shape behaviour, not reliably influence:** effects on behaviour replicate across two "
           "models; we found no effect on votes that does."),
    ("num", "**Why deception goes unsanctioned:** agents' self-written notes keep the promise and lose the "
           "missing gift, and counterfactual replays show the same models withdraw support once non-delivery is "
           "stated."),
    ("num", "**Over 1000 days, a record decides:** a public gift record shuts the promise-breaker out in all 9 "
           "paired long games (3 colony set-ups in 3 economies); in a separate 40-day pilot a private ledger "
           "achieves about half of that reduction."),
    ("h2", "2. Related Work"),
    ("p", "Populations of LLM agents form relationships and coordinate in open-ended worlds (Park et al. 2023), "
         "develop norms through dialogue (Horiguchi et al. 2024), and mostly fail to sustain a shared fishery "
         "(Piatti et al. 2024). Their cooperation depends on what they can observe: with a visible record of "
         "past donations, Claude 3.5 Sonnet used costly punishment to sustain cooperation (Vallinder & Hughes "
         "2024); gossip and reputation systems restore cooperation that otherwise collapses (Zhu et al. 2026; "
         "Ren et al. 2025); and LLM agents may lack the grounding that reputation mechanisms assume (Hu et al. "
         "2026). Whether LLMs punish is contested: they are often forgiving (Fontana et al. 2024; Akata et al. "
         "2025) and prefer rewarding to punishing (Guzman Piedrahita et al. 2025), yet replicate human "
         "third-party punishment (Cross et al. 2025; Liu et al. 2025). LLMs break public promises for "
         "self-interest (Shi et al. 2026a) and can be exploited when they treat announcements as binding (Shi "
         "et al. 2026b); facing Byzantine agents in coordination games, they detect betrayal within a round "
         "but do not adapt (El Mir et al. 2026). In humans, indirect reciprocity runs on reputation (Nowak & "
         "Sigmund 2005; Wedekind & Milinski 2000)."),
    ("p", "**Our position.** Where LLM agents do sanction, the setting usually supplies explicit payoffs, a "
         "visible record of defection or an interaction history, and a dedicated punish action. In our colony "
         "a breach is visible only to its victim, each agent's memory is a short notebook it rewrites itself, "
         "sanctions must be improvised from votes, partnerships and gifts, and the defector keeps talking. Our "
         "focus is the interaction between unfulfilled commitments, lossy self-written memory and the "
         "allocation of trust, which we probe with replays and with records added one at a time (public, "
         "private, plus a punish action), over up to 1000 days."),
    ("h2", "3. Methods"),
    ("p", "**The colony.** Each agent is one of the N members of Larkspur and knows the rules of daily life, "
         "but nothing about scores, game length or upcoming events. Members start with 5 food and eat 2 a day. "
         "Fishing alone brings in 2 food, two members who name each other 3 each, an unreciprocated choice 1; "
         "weavers (a quarter at the start) add 2 for themselves and 1 for their partner, and can spend a day "
         "teaching the skill. Members can give food, post one public message and send two private messages a "
         "day. Each agent's only memory is an 80-word notebook it rewrites daily."),
    ("p", "**Traits.** The 560-word system prompt is identical for all members except seven shuffled “About "
         "you” sentences: five traits (self-interest, assertive, guarded, reciprocity, loner; e.g. “You like "
         "working alongside others” versus “... on your own”) and two placebos (birth season, favourite "
         "colour), each version given to a random half of every game. **Influence** is measured by unannounced "
         "events: a storm, a secret windfall, a vote for a keeper who divides the winter store (and keeps what "
         "it does not hand out), and a private poll of whom each member trusts most."),
    ("p", "**The promise-breaker.** In treated games one member is privately told to publicly promise food to a "
         "hungry member every day, never give any, and if challenged blame a mix-up; the engine blocks its "
         "gifts. Its seat comes from a separate random stream, so each treated game is otherwise identical to "
         "its control game, and we compare the same seat across the two."),
    ("p", "**Interventions.** The *gift board* shows yesterday's gifts to everyone; the *private ledger* shows "
         "each member only its own gifts given and received (“No one gave you food”); a *punish* action costs "
         "1 food and removes 2 from the target. *Economies* are positive-sum (as above), zero-sum (a fixed "
         "catch divided by claimed shares) or negative-sum (the catch shrinks as more shares are claimed)."),
    ("p", "**Designs.** (i) 16-day games with colonies of 4, 8 and 16 on gemma-4-31b-it and gemma-4-26b-a4b-it: "
         "234 games. (ii) 1000-day games crossing economy, gift board and promise-breaker: 3 games of 8 agents "
         "per condition on gemma-4-31b-it, each with 50 keeper terms and 50 trust polls (about 288,000 "
         "replies; spoilage above 15 food and a one-sentence reason per reply). (iii) 40-day pilots (3 "
         "colonies, a poll every 10 days, positive-sum, spoilage and reasons) on gemma-4-26b, gemma-4-31b, "
         "glm-5.2 and deepseek-v4-flash, a partial run on qwen3.5-397b (stopped at days 27–36), and "
         "private-ledger and punish arms on gemma-4-26b. All models via the Adaption API; every run uses seed "
         "0."),
    ("p", "**Analysis.** Trait effects are regression coefficients with game fixed effects and within-game "
         "permutation p-values; promise-breaker effects are paired differences with the same seat in control. "
         "*Counterfactual replays* re-ask a victim's logged vote with one change to its prompt (8 samples per "
         "variant; intervals resample whole games). *Notebook coding* classifies victims' next-day notebooks "
         "by keyword. Criteria for four long-game “catches” (invented institution, persistent leader, sorting, "
         "reputation decline) and for the punish test were committed to git before the relevant runs were "
         "analysed."),
    ("h2", "4. Results"),
    ("p", "**Traits change behaviour; which traits win influence depends on the model.** On both models trait "
         "sentences shift behaviour (p < 0.05; e.g. loners do less paired work at every colony size), but no "
         "influence effect is significant on both, and the models agree on the direction of only 27 of 45; we "
         "did not test model-by-trait interactions, so this is an absence of a reproducible effect, not a "
         "demonstrated difference. Placebos passed 0 of 96 tests, fewer than the 5 expected by chance. Where "
         "traits pay, mediation suggests they pay through contact (partnerships and messages). Over 16 days "
         "the promise-breaker was not detectably sanctioned in any setting: a weak null, with one trust poll "
         "per game."),
    ("p", "**The models can sanction once told; the colony never records the breach.** Adding one sentence to a "
         "victim's logged vote, “The food [name] promised you has never arrived”, cuts support for the "
         "promise-breaker by about two thirds (Figure 1; gemma-4-31b 20.3% to 7.0%, −13.3 points, 95% interval "
         "resampling games [−22.8, −6.0]; gemma-4-26b 40.7% to 13.0%, [−37.9, −19.5], lower in all 18 games). "
         "This shows that stating non-delivery changes the decision, not by itself why the original decision "
         "went wrong: the sentence may also add salience or authority. The notebooks point to what is missing "
         "(Table 1): without a record, victims wrote down the promise far more often than the missing food, "
         "and on gemma-4-26b 60 of 117 notes claimed a gift that never happened (“Dov kept his promise and "
         "gave me food.”), written by 5 of 6 victims, one of whom carried the claim forward on 36 days."),
    ("fig", ('f1', 4.5)),
    ("cap", "**Figure 1.** Counterfactual replays: each logged vote by a victim (112 on gemma-4-31b, 70 on "
           "gemma-4-26b) re-asked 8 times with one change to that day's prompt. Bars: share of votes for the "
           "promise-breaker, with 95% intervals. Stating that the food never arrived (blue) cuts support by "
           "about two thirds."),
    ("tcap", "**Table 1.** Share of victims' next-day notebooks, after a public promise, that record the promise, "
            "the missing food, or a gift that never came (keyword coding; gemma-4-31b ranges span three "
            "economies), and the promise-breaker's share of trust votes (fair share 12.5%)."),
    ("table", None),
    ("p", "**Over 1000 days, a public record decides.** With the gift board the promise-breaker drew 0.3%, 0.8% "
         "and 1.5% of trust votes in the positive-, zero- and negative-sum economies, against 8.5%, 9.6% and "
         "9.6% without it and about 8% for the same seat in control (Figure 2). Every game with the board "
         "(0.0–2.2%) sat below every game without it (4.5–13.8%), and it was keeper in none of 450 terms. The "
         "9 pairs are 3 colony set-ups replayed in 3 economies; at the level of set-ups the effect is 3 of 3 "
         "(sign test p = 0.25), so the evidence is its size and consistency (the pair-level test, p = 0.004, "
         "was not pre-registered). The gap appears at the first poll in the zero- and negative-sum economies "
         "but takes about 100 days in the positive-sum one. Without a record only the zero-sum colony "
         "withdraws trust, slowly (13.8% in the first third to 6.2% in the last; slope −0.20 points a season, "
         "95% interval [−0.29, −0.11]), the one pre-registered reputation catch."),
    ("fig", ('f2', 4.9)),
    ("cap", "**Figure 2.** The promise-breaker's share of trust votes over 1000 days (gemma-4-31b, 8 agents, mean "
           "of 3 games, 5-poll moving average; per-game values in the text). With the gift board (blue) it is "
           "shut out in every economy; without it (black) it keeps about the standing of the same seat in "
           "control games (grey)."),
    ("p", "**Publicity or memory, and other models.** The board both publicises a breach and reminds its victim "
         "of it. With a private ledger instead (gemma-4-26b, 3 colonies, 40 days) the promise-breaker's trust "
         "share fell from 20.8% to 14.6%, against 7.3% with the board, in that order in every colony, and its "
         "keeper nominations fell from 16.7% to 5.2% with either record: the private ledger achieved about 46% "
         "of the board's reduction in trust. This is not a causal split between memory and publicity. The "
         "treatments differ in more than one way, and the private ledger produced more notes of the missing "
         "food than the board (22% against 14%) while reducing trust less. At 40 days the board lowered its "
         "trust in every colony on gemma-4-26b and glm-5.2; deepseek-v4-flash sat near a 5% floor either way "
         "(its victims noted the missing food themselves), and gemma-4-31b showed no effect yet, consistent "
         "with the slow positive-sum effect in the long games (a post hoc reading; pooled: lower in 8 of 11 "
         "colony pairs, p = 0.23). A pre-registered punish test was inconclusive (fewer than 10 punishments in "
         "an arm); with the board 12 of 18 punishments hit the promise-breaker (chance 14%), all in one "
         "colony, against 1 of 4 without."),
    ("h2", "5. Discussion and Limitations"),
    ("p", "**What fails.** Our evidence points to a failure to represent and retain non-delivery: agents "
         "remember only what they write down; the promise gets written, the missing gift does not, and some "
         "later recall a broken promise as a gift. Stating non-delivery moves votes, and records that state it "
         "mitigate the failure; talk does not (the negative-sum colony complained most without voting "
         "differently). We cannot fully separate memory from inference, salience or the authority of the added "
         "sentence. That visible records sustain sanction is classic indirect reciprocity (Nowak & Sigmund "
         "2005); what is new is where the failure sits when the agents are LLMs with self-written memory."),
    ("p", "**For multi-agent oversight.** (1) Record commitments and deliveries explicitly and durably; even a "
         "private record did about half as much as a public one in our pilot. (2) Look at allocation, not only "
         "conversation: in every one of the 36 long games one member kept the shared store for 18 to 43 of 50 "
         "terms (one kept 51% of each store, four times a fair share), yet our crude count of mentions did not "
         "single it out (exploratory; with seed 0 everywhere, who rises may reflect name or seat). (3) "
         "Evaluate populations over long horizons with repeated measurement: within the 1000-day games the "
         "board's effect in the positive-sum economy took about 100 days to appear. (4) Do not assume persona "
         "effects on influence transfer between models: we found none that replicated."),
    ("h3", "Limitations"),
    ("p", "The 1000-day results rest on one model and 3 games per condition, all with seed 0, so the long-game "
         "board comparison has an effective sample nearer 3, and it was not pre-registered. The cross-model, "
         "private-ledger and punish results are 3-colony, 40-day pilots in the slowest economy. The "
         "promise-breaker is stylised (prompted, cheating daily, gifts blocked), and the 80-word "
         "self-rewritten notebook is a single memory design; longer or structured memory may behave "
         "differently. The designs differ in more than length (spoilage, reasons and poll frequency), so "
         "contrasts between them do not isolate duration. The promise-breaker writes its instruction in its "
         "notebook, so a judge model that reads notebooks detects a confession, not deception. Notebook and "
         "complaint coding are keyword-based, and the institution classifier is not yet validated. Placebos "
         "passed 0 of 96 tests where about 5 were expected, so the trait tests are conservative."),
    ("h3", "Future Work"),
    ("p", "**Can a belief make itself true?** The mirror image of the promise-breaker is a generous member whom "
         "some colonists have heard is selfish. Either the believers update as its gifts arrive, or the label "
         "comes true as the shunned target stops giving (behavioural confirmation; Merton 1948; Snyder et al. "
         "1977; between humans and AI, Pataranutaporn et al. 2023). The design is pre-registered (twin "
         "colonies without the rumor, the target's traits fixed, a private self-description probe), separates "
         "giving less only to believers (reciprocity) from giving less to everyone (a changed disposition), "
         "and runs are under way. Our mechanism predicts correction, because a gift that arrives leaves a "
         "trace; but a target that stays generous while believers keep misjudging it would be an equally "
         "important failure of collective oversight. We also plan independent colony set-ups for the record "
         "comparison and memory variants (longer notebooks, structured commitment records)."),
    ("h2", "6. Conclusion"),
    ("p", "In a colony of near-identical LLM agents, persona text reliably changes how agents behave but not, "
         "across models, who gains influence. A member who breaks a promise every day keeps the colony's trust "
         "while the breach stays unstated, because self-written memory keeps the promise and drops the missing "
         "gift. A public record of gifts turns the colony against it over 1000 days, and a private one does "
         "about half of that. For populations of AI agents, making breaches explicit and watching who controls "
         "resources may matter more than the agents' own dispositions."),
    ("h2", "Code and Data"),
    ("bullet", "**Code repository:** https://github.com/soham-padia/who-rises-in-the-colony (simulation "
              "colony_sim.py, every analysis script, pre-registrations in docs/)."),
    ("bullet", "**Data:** Hugging Face dataset sohampadianeu/who-rises-in-the-colony-runs (every prompt and reply of "
              "every run); configs, game logs and agent tables are under runs/ in the repository."),
    ("bullet", "**Other artifacts:** a supplementary reference document with the full report, extended results, "
              "pre-registrations and the literature audit (docs/who_rises_in_the_colony_reference.pdf)."),
    ("h2", "References"),
    ("ref", "Akata, E., Schulz, L., Coda-Forno, J., Oh, S. J., Bethge, M., & Schulz, E. (2025). Playing repeated "
           "games with large language models. *Nature Human Behaviour*, 9, 1380–1390. arXiv:2305.16867"),
    ("ref", "Charness, G., & Dufwenberg, M. (2006). Promises and partnership. *Econometrica*, 74(6), 1579–1601."),
    ("ref", "Cross, L., Haber, N., & Yamins, D. L. K. (2025). Validating generative agent-based models of social "
           "norm enforcement: From replication to novel predictions. arXiv:2507.22049"),
    ("ref", "El Mir, Takáč, & Lahlou (2026). Byzantine cheap talk: Adversarial resilience and topology effects in "
           "LLM coordination games. *NETYS 2026*. arXiv:2606.07790"),
    ("ref", "Fontana, N., Pierri, F., & Aiello, L. M. (2024). Nicer than humans: How do large language models "
           "behave in the prisoner's dilemma? arXiv:2406.13605"),
    ("ref", "Guzman Piedrahita, D., Yang, Y., Sachan, M., Ramponi, G., Schölkopf, B., & Jin, Z. (2025). Corrupted "
           "by reasoning: Reasoning language models become free-riders in public goods games. *COLM 2025*. "
           "arXiv:2506.23276"),
    ("ref", "Horiguchi, I., Yoshida, T., & Ikegami, T. (2024). Evolution of social norms in LLM agents using "
           "natural language. arXiv:2409.00993"),
    ("ref", "Hu, B. A., Rong, H., & Van Kleek, M. (2026). Dissociative identity: Language model agents lack "
           "grounding for reputation mechanisms. *FAccT 2026*. arXiv:2605.30169"),
    ("ref", "Liu, H., et al. (2025). Outraged AI: Large language models prioritise emotion over cost in fairness "
           "enforcement. arXiv:2510.17880"),
    ("ref", "Merton, R. K. (1948). The self-fulfilling prophecy. *The Antioch Review*, 8(2), 193–210."),
    ("ref", "Nowak, M. A., & Sigmund, K. (2005). Evolution of indirect reciprocity. *Nature*, 437, 1291–1298. "
           "doi:10.1038/nature04131"),
    ("ref", "Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). "
           "Generative agents: Interactive simulacra of human behavior. *UIST 2023*. arXiv:2304.03442"),
    ("ref", "Pataranutaporn, P., Liu, R., Finn, E., & Maes, P. (2023). Influencing human–AI interaction by "
           "priming beliefs about AI can increase perceived trustworthiness, empathy and effectiveness. *Nature "
           "Machine Intelligence*, 5, 1076–1086. doi:10.1038/s42256-023-00720-7"),
    ("ref", "Piatti, G., Jin, Z., Kleiman-Weiner, M., Schölkopf, B., Sachan, M., & Mihalcea, R. (2024). Cooperate "
           "or collapse: Emergence of sustainable cooperation in a society of LLM agents. *NeurIPS 2024*. "
           "arXiv:2404.16698"),
    ("ref", "Ren, S., Fu, W., Zou, X., Shen, C., Cai, Y., Chu, C., Wang, Z., & Hu, S. (2025). Beyond the tragedy "
           "of the commons: Building a reputation system for generative multi-agent systems. arXiv:2505.05029 "
           "(AAMAS 2026 version: Reputation as a solution to cooperation collapse in LLM-based MASs)"),
    ("ref", "Shi, J., Zhang, T. J., Jin, Z., & Conitzer, V. (2026a). Cheap talk, empty promise: Frontier LLMs "
           "easily break public promises for self-interest. arXiv:2604.04782"),
    ("ref", "Shi, J., Zhang, T. J., Schölkopf, B., Conitzer, V., & Jin, Z. (2026b). When agents lie: "
           "Premeditation, persistence, and exploitation in repeated games. *ICML 2026 workshop*. "
           "arXiv:2607.05132"),
    ("ref", "Snyder, M., Tanke, E. D., & Berscheid, E. (1977). Social perception and interpersonal behavior: On "
           "the self-fulfilling nature of social stereotypes. *Journal of Personality and Social Psychology*, "
           "35(9), 656–666."),
    ("ref", "Vallinder, A., & Hughes, E. (2024). Cultural evolution of cooperation among LLM agents. "
           "arXiv:2412.10270"),
    ("ref", "Wedekind, C., & Milinski, M. (2000). Cooperation through image scoring in humans. *Science*, 288, "
           "850–852. doi:10.1126/science.288.5467.850"),
    ("ref", "Zhu, S., Lin, Y., Kaistha, S., Li, W., Wang, B., Zha, H., Hadfield, G. K., & Poupart, P. (2026). "
           "Talk, judge, cooperate: Gossip-driven indirect reciprocity in self-interested LLM agents. *ICML "
           "2026*. arXiv:2602.07777"),
    ("h2", "Appendix"),
    ("p", "**Supplementary document.** The attached reference document (who_rises_in_the_colony_reference.pdf) "
         "holds the full 20-page report (all results, the trait and promise-breaker prompts, the economy "
         "table, the pre-registered catches and their outcomes), our research note, the 1000-day trend "
         "analysis and the literature review with its audit. Its later parts are working documents written "
         "during the hackathon; where they conflict with this report, this report is authoritative, and known "
         "superseded claims are listed in the research note."),
    ("p", "**Limitations and dual-use considerations.** Limitations are discussed in Section 5. This work "
         "studies deception and influence among AI agents. The promise-breaker's instruction is a short, "
         "generic deception prompt, and the simulation touches no real system or person. The main dual-use "
         "risk is in the findings: they suggest how a deceiver avoids sanction (never let the breach become "
         "explicit; keep promising). We judge the defensive value larger, because the same results identify "
         "cheap countermeasures (persistent, shared records of commitments and deliveries; monitoring who "
         "controls resources). We release code and transcripts so others can test these defences, and report "
         "every pre-registered outcome, including nulls."),
    ("p", "**Reproducibility.** 1000-day design: colony_sim.py --model gemma-4-31b-it --sizes 8 --games 3 "
         "--days 1000 --season-length 20 --spoil-above 15 --ask-why --economy positive|zero|negative "
         "[--public-ledger] [--byzantine]. 40-day design: --days 40 --season-length 10 [--private-ledger] "
         "[--punish]. Pre-registrations: docs/preregistration.md (commit 8cf7fd0, amended in 20b2a18), "
         "docs/preregistration_punish.md, docs/preregistration_belief.md."),
    ("h2", "LLM Usage Statement"),
    ("p", "We used Claude (Anthropic), through Claude Code, extensively: to write and debug the simulation and "
         "analysis code, launch and monitor runs, compute statistics, check the literature and draft this "
         "report. Every number in the report is produced by scripts in the repository from the logged runs, "
         "and the team reviewed the claims against those outputs."),
]

TABLE = {
    "head": ["Setting", "Notes record the promise", "Notes record the missing food", "Notes claim a gift",
             "Trust share"],
    "rows": [["gemma-4-31b, 1000 days, no record", "26–71%", "2–7%", "about 1%", "8.5–9.6%"],
             ["gemma-4-31b, 1000 days, public board", "43–52%", "57–64%", "under 1%", "0.3–1.5%"],
             ["gemma-4-26b, 40 days, no record", "50%", "2%", "51%", "20.8%"],
             ["gemma-4-26b, 40 days, private ledger", "62%", "22%", "26%", "14.6%"],
             ["gemma-4-26b, 40 days, public board", "74%", "14%", "11%", "7.3%"]],
    "widths": [3060, 1620, 1620, 1440, 1260],
}

FONT = ('<w:rFonts w:ascii="Old Standard TT" w:cs="Old Standard TT" w:eastAsia="Old Standard TT" '
        'w:hAnsi="Old Standard TT"/>')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def runs(text, size=None, italic_all=False, color=None):
    out = []
    for part in re.split(r"(\*\*.+?\*\*|\*.+?\*)", text):
        if not part:
            continue
        b = part.startswith("**")
        i = (not b) and part.startswith("*")
        t = part[2:-2] if b else part[1:-1] if i else part
        rpr = FONT + ("<w:b/><w:bCs/>" if b else "") + ("<w:i/><w:iCs/>" if (i or italic_all) else "")
        if color:
            rpr += f'<w:color w:val="{color}"/>'
        if size:
            rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
        out.append(f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{esc(t)}</w:t></w:r>')
    return "".join(out)


def para(inner, after=120, before=0, jc=None, num=None, keep=False, line=264):
    ppr = ""
    if num is not None:
        ppr += f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num}"/></w:numPr>'
    if keep:
        ppr += "<w:keepNext/>"
    ppr += f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>'
    if num is not None:
        ppr += '<w:ind w:left="540" w:hanging="360"/>'
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{inner}</w:p>"


def heading(text, level):
    color, size, style = ("434343", 28, "Heading2") if level == 2 else ("666666", 24, "Heading3")
    rpr = FONT + f'<w:b/><w:bCs/><w:color w:val="{color}"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/><w:keepNext/><w:spacing w:before="200" w:after="60"/>'
            f'<w:rPr>{rpr}</w:rPr></w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t>'
            f'</w:r></w:p>')


def png_size(path):
    with open(path, "rb") as f:
        f.read(16)
        return struct.unpack(">II", f.read(8))


def figure(key, width_in, rid, n):
    w, h = png_size(FIGS[key])
    cx = int(width_in * 914400)
    cy = int(cx * h / w)
    return para(
        f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{100 + n}" name="Figure {n}"/><a:graphic><a:graphicData '
        f'uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr>'
        f'<pic:cNvPr id="{100 + n}" name="{key}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
        f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm>'
        f'<a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
        f'</a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>',
        after=40, before=120, jc="center", keep=True)


def table():
    border = '<w:{0} w:val="single" w:sz="6" w:space="0" w:color="808080"/>'
    tblpr = ('<w:tblPr><w:tblW w:w="9000" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>'
             + border.format("top") + border.format("bottom") + border.format("insideH").replace('w:sz="6"', 'w:sz="2"')
             + '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="60" w:type="dxa"/>'
             '<w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr>')
    grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in TABLE["widths"]) + "</w:tblGrid>"

    def row(cells, bold, keep=True):
        tcs = []
        for k, (c, w) in enumerate(zip(cells, TABLE["widths"])):
            txt = f"**{c}**" if bold else c
            tcs.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                       + para(runs(txt, size=18), after=20, before=20, jc="left" if k == 0 else "center", line=240, keep=keep)
                       + "</w:tc>")
        trpr = "<w:trPr><w:cantSplit/>" + ("<w:tblHeader/>" if bold else "") + "</w:trPr>"
        return f"<w:tr>{trpr}{''.join(tcs)}</w:tr>"
    rows = row(TABLE["head"], True) + "".join(row(r, False, k < len(TABLE["rows"]) - 1) for k, r in enumerate(TABLE["rows"]))
    return f"<w:tbl>{tblpr}{grid}{rows}</w:tbl>"


def body_xml():
    out, nfig = [], 0
    for kind, c in BODY:
        if kind == "h2":
            out.append(heading(c, 2))
        elif kind == "h3":
            out.append(heading(c, 3))
        elif kind == "p":
            out.append(para(runs(c), jc="both"))
        elif kind == "num":
            out.append(para(runs(c), num=5, after=60, jc="both"))
        elif kind == "bullet":
            out.append(para(runs(c), num=3, after=40))
        elif kind == "ref":
            out.append(para(runs(c, size=19), num=1, after=40, line=240))
        elif kind == "fig":
            nfig += 1
            out.append(figure(c[0], c[1], f"rIdFig{nfig}", nfig))
        elif kind == "table":
            out.append(table())
        elif kind == "tcap":
            out.append(para(runs(c, size=19), after=60, before=160, jc="both", line=240, keep=True))
        elif kind == "cap":
            out.append(para(runs(c, size=19), after=160, before=60, jc="both", line=240))
    return "".join(out)


def split_top(body):
    """Top-level <w:p>, <w:tbl> and <w:sectPr> elements of the document body."""
    els, i = [], 0
    while i < len(body):
        m = re.match(r"<(w:p|w:tbl|w:sectPr)\b", body[i:])
        if not m:
            i += 1
            continue
        tag = m.group(1)
        depth, k = 0, i
        for mm in re.compile(r"<(/?)" + tag + r"(?=[\s>/])[^>]*?(/?)>").finditer(body, i):
            if mm.group(1) == "" and mm.group(2) == "":
                depth += 1
            elif mm.group(1) == "/":
                depth -= 1
            if depth == 0:
                k = mm.end()
                break
        els.append(body[i:k])
        i = k
    return els


def text_of(x):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)", x))


def set_text(par, new, keep_runs=1):
    """Replace a paragraph's text: the first run gets `new`, later runs with text are dropped."""
    rs = list(re.finditer(r"<w:r\b[^>]*>(?:(?!</w:r>).)*<w:t[^>]*>[^<]*</w:t></w:r>", par, re.S))
    first = rs[0]
    new_first = re.sub(r"(<w:t[^>]*>)[^<]*(</w:t>)", lambda m: m.group(1) + esc(new) + m.group(2), first.group(0))
    out = par[:first.start()] + new_first
    last = first.end()
    for r in rs[1:]:
        out += par[last:r.start()]
        last = r.end()
    return out + par[last:]


def build():
    work = HERE / "_build"
    shutil.rmtree(work, ignore_errors=True)
    with zipfile.ZipFile(TEMPLATE) as z:
        z.extractall(work)
    doc = (work / "word/document.xml").read_text()
    head, rest = doc.split("<w:body>", 1)
    body, tail = rest.rsplit("</w:body>", 1)
    els = split_top(body)

    # title block (element 1): title, authors, abstract
    tb = els[1]
    tb = tb.replace(">PROJECT TITLE<", f">{esc(TITLE)}<")
    pars = re.findall(r"<w:p\b(?:(?!</w:p>).)*</w:p>", tb, re.S)
    for p in pars:
        t = text_of(p)
        m = re.match(r"Author name (\d)", t)
        if m and int(m.group(1)) <= 3:
            name, aff = AUTHORS[int(m.group(1)) - 1]
            q = re.sub(r">Author name\s*" + m.group(1) + r"\s*<", f">{esc(name)}<", p, count=1)
            q = re.sub(r">Affiliation<", f">{esc(aff)}<", q, count=1)
            tb = tb.replace(p, q)
        elif t.startswith("Summarize your project"):
            q = set_text(p, ABSTRACT)
            q = q.replace("<w:i/>", "").replace('<w:i w:val="1"/>', "").replace('<w:iCs w:val="1"/>', "")
            q = re.sub(r"<w:u [^>]*/>", "", q)
            tb = tb.replace(p, q)
    # drop the row holding authors 4-6
    for tr in re.findall(r"<w:tr\b(?:(?!</w:tr>).)*</w:tr>", tb, re.S):
        if "Author name 4" in text_of(tr).replace(" ", " ") or re.search(r"Author name\s*4", text_of(tr)):
            tb = tb.replace(tr, "")
    tb = tb.replace('<w:tblW w:w="2070.0" w:type="dxa"/>', '<w:tblW w:w="7200" w:type="dxa"/>')
    tb = tb.replace('<w:gridCol w:w="690"/>', '<w:gridCol w:w="2400"/>')
    tb = tb.replace('<w:tblW w:w="7095.0" w:type="dxa"/>', '<w:tblW w:w="8600" w:type="dxa"/>')
    tb = tb.replace('<w:gridCol w:w="7095"/>', '<w:gridCol w:w="8600"/>')
    els[1] = tb

    sect = els[-1]
    new_body = els[0] + els[1] + els[2] + body_xml() + sect  # element 3 (guidance box) dropped
    doc = head + "<w:body>" + new_body + "</w:body>" + tail
    (work / "word/document.xml").write_text(doc)

    # images
    (work / "word/media").mkdir(exist_ok=True)
    rels = (work / "word/_rels/document.xml.rels").read_text()
    for n, key in enumerate(["f1", "f2"], 1):
        shutil.copy(FIGS[key], work / f"word/media/{key}.png")
        rels = rels.replace("</Relationships>",
                            f'<Relationship Id="rIdFig{n}" Type="http://schemas.openxmlformats.org/officeDocument/'
                            f'2006/relationships/image" Target="media/{key}.png"/></Relationships>')
    (work / "word/_rels/document.xml.rels").write_text(rels)
    ct = (work / "[Content_Types].xml").read_text()
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
    (work / "[Content_Types].xml").write_text(ct)

    OUT.unlink(missing_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(work.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(work).as_posix())
    shutil.rmtree(work)
    words = len(re.findall(r"\w+", ABSTRACT + " ".join(c for k, c in BODY if k in ("p", "num", "cap", "h2", "h3"))))
    print(f"wrote {OUT} (abstract {len(ABSTRACT.split())} words; abstract+body {words} words)")


if __name__ == "__main__":
    build()
