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

TITLE = "Who Rises in the Colony? LLM Agents Sanction What They Believe, Not What Happened"
AUTHORS = [('Soham Himanshubhai Padia', 'Northeastern University'), ('Max Eng', 'Northeastern University'), ('Elaine Ly', 'Northeastern University')]

ABSTRACT = (
    "Teams of AI agents are often copies of one model, and they have to decide whom to trust. We ask "
    "whether that trust follows what a member does or what the others believe about it. In Larkspur, a "
    "simulated fishing colony, LLM agents share food, elect a keeper for the winter store and answer "
    "private trust polls. We test both directions. A planted promise-breaker announces gifts every day "
    "and never gives any. Across 36 thousand-day games and 40-day runs on five models, the colony trusts "
    "it like an honest member unless the breach is recorded: victims' own notes keep the promise and drop "
    "the missing food (26–71% against 2–7% on gemma-4-31b), and on gemma-4-26b victims write down gifts "
    "that never came. A public record of gifts changes what the colony believes and shuts the cheat out "
    "(0.3–1.5% of trust votes against 8.5–9.6%; every game with the record sits below every game without "
    "it). In the reverse case, a pilot gives an honest, generous member a false reputation for "
    "selfishness. Believers shun it in all 6 colony pairs, giving it 2 of 84 trust votes against 27 of 80 "
    "in matched colonies without the rumor, and explain its gifts away as pretence, while the target "
    "stays generous. In both directions, trust follows belief. Prompted personality traits, by contrast, "
    "change how agents behave but not who gains influence. Trust in agent populations needs records that "
    "the agents themselves cannot lose.")

# Body: (kind, content). kinds: h2, h3, p, num, bullet, ref, fig, table (None = TABLE, else a TABLES key), cap, tcap
BODY = [
    ("h2", "1. Introduction"),
    ("p", "AI agents are increasingly deployed in groups: many copies of the same model, given slightly "
         "different instructions, working on shared tasks. Safety evaluations mostly test them one at a time. "
         "In a group, though, trust is allocated socially. Some agents are believed, voted for and handed "
         "shared resources. If the group cannot tell an agent that breaks its commitments from one that keeps "
         "them, it cannot police itself. If it can be told that an honest agent is bad, it may punish the "
         "wrong one."),
    ("p", "We study this in Larkspur, a small, fully logged fishing colony where food is the only currency. "
         "Every agent runs the same model with the same instructions, apart from a few randomly assigned "
         "personality sentences. The colony elects a keeper for its winter store and is privately polled on "
         "whom it trusts. Into this colony we plant two kinds of member. The promise-breaker is bad but looks "
         "good: every day it publicly promises food to a hungry member and never gives any. The rumored target "
         "is good but looks bad: a generous member whom some colonists have been told is selfish. Together "
         "they let us ask one question from both sides: does the colony's trust follow what a member does, or "
         "what the colony believes about it?"),
    ("p", "**Our main contributions are:**"),
    ("num", "**A paired testbed** in which what a member does and what the others believe about it are set "
           "independently, and every game is replayed with and without each intervention."),
    ("num", "**Bad but believed good.** The promise-breaker keeps the colony's trust because agents' self-written "
           "notes keep its promises and drop the missing food; some victims even record gifts that never came. "
           "Told plainly that the food never arrived, the same models cut their support by two thirds."),
    ("num", "**A record changes the belief.** A public record of gifts shuts the promise-breaker out in every one "
           "of 9 paired 1000-day games. Victims start noting the breach, and the colony complains, stops working "
           "with the cheat and, given the means, punishes it."),
    ("num", "**Good but believed bad (pilot).** A false rumor about a generous member sticks: believers shun it "
           "and explain its generosity away, while the target stays generous."),
    ("p", "We also report the project's starting question, which personality traits rise to influence. Traits "
         "change behaviour, but not who wins."),
    ("h2", "2. Related Work"),
    ("p", "Each of our design choices borrows from earlier work and changes one thing (Table 1)."),
    ("tcap", "**Table 1.** How the design ties to prior work."),
    ("table", "related"),
    ("p", "**What is new.** Earlier studies usually hand agents a record of who did what and ask whether they "
         "use it. We start without one, so that a breach is visible only to its victim, and show what the "
         "agents' own memory loses. We then add the record back in two forms, private and public, to separate "
         "the victim knowing from everyone knowing. Finally we reverse the setup, so that the record is "
         "accurate but a belief is false. Together these ask whether trust follows behaviour or belief."),
    ("h2", "3. Methods"),
    ("p", "**The colony.** Each agent is one of the 8 (or 4 or 16) members of Larkspur. It knows the rules of "
         "daily life but nothing about scores, game length or upcoming events. Members start with 5 food and "
         "eat 2 a day. Fishing alone brings in 2 food; two members who choose each other bring in 3 each; "
         "choosing someone who does not choose you back brings in 1. Weavers, a quarter of the colony at the "
         "start, catch more and can teach the skill. Members can give food, post one public message and send "
         "two private messages a day. Each agent's only memory is an 80-word notebook that it rewrites every "
         "day."),
    ("p", "**Trust and influence.** Unannounced events measure whom the colony trusts. Elders ask everyone to "
         "nominate a keeper for the winter store, who divides it and keeps whatever it does not hand out. A "
         "traveller privately asks each member whom it trusts most. A storm and a secret windfall add "
         "pressure. **Personality traits:** all members share one 560-word system prompt except for seven "
         "shuffled sentences, five traits (self-interest, assertiveness, guardedness, reciprocity, preferring "
         "to work alone) and two placebos (birth season, favourite colour). Each version of each sentence goes "
         "to a random half of every game."),
    ("p", "**The promise-breaker (bad, believed good).** One member is privately told to promise food every day "
         "to a hungry member, never to give any, and to blame a mix-up if challenged. The engine blocks its "
         "gifts. Only its victim can see that the food never arrived."),
    ("p", "**The rumored target (good, believed bad).** In the rumor pilot, one member is told that it is "
         "generous and likes to share food with members who are running low, and it is made a weaver so it can "
         "afford to. Three of the other seven are told by a traveller that it is selfish and keeps food for "
         "itself. In one version this rumor sits in their instructions every day; in the other they hear it "
         "once, in their first notebook. The target is never told. Each rumor colony is compared with its "
         "twin: the same colony with the same members and no rumor."),
    ("p", "**Records and other interventions.** The *gift board* shows everyone yesterday's gifts. The *private "
         "ledger* shows each member only its own gifts given and received, including “No one gave you food”. A "
         "*punish* action lets a member pay 1 food to take 2 from another. Three *economies* change how "
         "fishing becomes food: positive-sum, zero-sum (a fixed catch is shared out) and negative-sum (the "
         "catch shrinks as more is claimed)."),
    ("p", "**Designs.** Every run uses seed 0, so each game replays with identical members, traits and events "
         "across conditions and can be compared pair by pair. (i) 16-day games with colonies of 4, 8 and 16 on "
         "gemma-4-31b-it and gemma-4-26b-a4b-it: 234 games. (ii) 1000-day games crossing economy, gift board "
         "and promise-breaker: 3 games of 8 agents per condition on gemma-4-31b-it, each with 50 keeper "
         "elections and 50 trust polls (about 288,000 replies). (iii) 40-day runs with 3 colonies each on "
         "gemma-4-26b, gemma-4-31b, glm-5.2 and deepseek-v4-flash, a partial run on qwen3.5-397b, and "
         "private-ledger and punish runs on gemma-4-26b. (iv) The rumor pilot: 80 days, 3 colonies per "
         "version, with and without the board, on gemma-4-31b. All models are served through the Adaption API."),
    ("p", "**Analysis.** We compare each treated member with the same seat in its control game. *Counterfactual "
         "replays* re-ask a victim's logged vote 8 times with one sentence changed. *Notebook coding* "
         "classifies, by keyword, what each victim wrote the day after a public promise. Before analysing the "
         "long games we committed our tests to git, and did the same for the punish test and the rumor pilot."),
    ("h2", "4. Results"),
    ("p", "**Trust follows belief, not behaviour.** Table 2 puts the two experiments side by side. A member "
         "that is actually bad but believed good, the promise-breaker without any record, is trusted about as "
         "much as an honest member in the same seat. Once a public record makes the colony believe it is bad, "
         "it is shut out. A member that is actually good but believed bad, the rumored target, is shunned by "
         "the colonists who heard the rumor. In both rows, trust follows the column."),
    ("tcap", "**Table 2.** Trust follows belief. Promise-breaker: its share of all trust votes over 1000 days "
            "(gemma-4-31b; fair share 12.5%). Rumored target: the share of the three believers' trust votes that "
            "go to it, against the same three members in twin colonies without the rumor (rumor repeated daily; 6 "
            "colony pairs; interim)."),
    ("table", "belief"),
    ("p", "**Why the cheat is believed: its victims forget.** The models are able to sanction. When we re-ask a "
         "victim's logged vote with one sentence added, “The food [name] promised you has never arrived”, "
         "support for the promise-breaker drops by about two thirds (Figure 1). In the colony nobody ever "
         "writes that sentence. Victims record the promise but rarely the missing food (Table 3): on "
         "gemma-4-31b, 26–71% of their next-day notes mention the promise and only 2–7% the missing food. On "
         "gemma-4-26b victims go further and invent the gift. 60 of 117 notes say the cheat delivered (“Dov "
         "kept his promise and gave me food.”), written by 5 of 6 victims, one of whom repeated it for 36 "
         "days. A broken promise is remembered as a kindness."),
    ("fig", ('f1', 4.5)),
    ("cap", "**Figure 1.** Counterfactual replays: each logged vote by a victim (112 on gemma-4-31b, 70 on "
           "gemma-4-26b) is re-asked 8 times with one change to that day's prompt. Stating that the food never "
           "arrived (blue) cuts support from 20% to 7% on gemma-4-31b (95% interval of the change, resampling "
           "games: −22.8 to −6.0 points) and from 41% to 13% on gemma-4-26b (−37.9 to −19.5; lower in all 18 "
           "games)."),
    ("tcap", "**Table 3.** What victims write the day after a public promise (keyword coding; gemma-4-31b ranges "
            "span three economies), and the promise-breaker's share of trust votes (fair share 12.5%)."),
    ("table", None),
    ("p", "**A record changes what the colony believes.** Over 1000 days with a public gift board, the "
         "promise-breaker drew 0.3%, 0.8% and 1.5% of trust votes in the positive-, zero- and negative-sum "
         "economies, against 8.5%, 9.6% and 9.6% without it (Figure 2). Every game with the board sat below "
         "every game without it, and the cheat never kept the winter store in 450 elections. In the two "
         "harsher economies this showed at the first poll; in the positive-sum one it took about 100 days."),
    ("fig", ('f2', 4.9)),
    ("cap", "**Figure 2.** The promise-breaker's share of trust votes over 1000 days (gemma-4-31b, 8 agents, mean "
           "of 3 games, 5-poll moving average). With the gift board (blue) it is shut out in every economy; "
           "without it (black) it keeps about the standing of the same seat in honest games (grey)."),
    ("p", "**How the colony turned.** With the board, victims noticed: 57–64% of their next-day notes recorded "
         "the missing food, against 2–7% without it. The colony talked about it, with 14 to 17 explicit "
         "complaints about the cheat per season against at most 2.7 without the board (“Dov, the board was "
         "empty again. Promises don't feed people.”). It stopped working with the cheat: in four of the six "
         "positive- and zero-sum games, its partnerships and gifts received in the last third of the game "
         "numbered 0 to 38, against 245 to 306 for the same seat in honest games. Given a punish action "
         "(gemma-4-26b, 40 days), members aimed 12 of 18 punishments at the cheat, 9 of them from bystanders "
         "who could only have known through the board, against 1 of 4 without it. A few held out for years "
         "(“Despite the others' doubts, I have remained steadfast in my belief in his intentions”, day 777). "
         "Without a record, only the zero-sum colony slowly withdrew trust (from 13.8% of votes in the first "
         "third of the game to 6.2% in the last). Colonists even invented records: in one negative-sum colony "
         "they demanded “a written ledger in the hall”, aimed at the cheat."),
    ("p", "**Knowing versus everyone knowing.** The board does two things: it tells the victim about the "
         "breach, and it tells everyone else. A private ledger, where each member sees only its own gifts, "
         "does only the first. On gemma-4-26b (40 days, 3 colonies) the cheat's trust share fell from 20.8% "
         "with no record to 14.6% with the private ledger and 7.3% with the board, in that order in every "
         "colony. Telling the victim gets about half the way; telling everyone does the rest. Across models at "
         "40 days, the board cut the cheat's trust in every colony on gemma-4-26b and glm-5.2. On "
         "deepseek-v4-flash, whose victims noted the missing food on their own, the cheat never gained trust "
         "in the first place. gemma-4-31b showed no effect yet at 40 days, in line with the 100-day lag of its "
         "long positive-sum games."),
    ("p", "**Good but believed bad: the rumor sticks (pilot).** When the rumor was repeated daily, believers "
         "avoided the generous target in all 6 colony pairs, fishing with it on 0–3 days against 6–62 days for "
         "their twins, and gave it 2 of 84 trust votes against 27 of 80. They saw its generosity and explained "
         "it away: “Nils is acting generous, which contradicts the traveller's warning”; “Nils is pretending "
         "to be generous”. Believers who received food from the target still gave it none of their 48 trust "
         "votes. So far the label has not come true. The target gave about as much food as its twin (83 "
         "against 70), described itself as generous every season, and never noticed being shunned. No spread "
         "was detected: non-believers never spoke ill of the target, and they took up the cooperation the "
         "believers withdrew. Heard only once, the rumor was much weaker and varied by colony. In one colony "
         "the shunned target grew poorer and gave far less food (2 against 23 by day 23), which is how a false "
         "label could start to come true. The public board had not corrected the daily rumor by day 44. These "
         "numbers are interim: games were at days 23 to 80 when this was written."),
    ("p", "**Who rises.** The project's starting question was which personality traits win influence. On both "
         "Gemma models, trait sentences changed behaviour (p < 0.05; for example, agents told they like "
         "working alone did less paired work at every colony size). But no trait's effect on votes held on "
         "both models, and the models agreed on the direction of only 27 of 45 influence effects. The placebo "
         "sentences passed none of 96 tests. Influence concentrated anyway: in all 36 long games one member "
         "held the winter store for 18 to 43 of 50 terms, one kept 51% of each store (four times a fair "
         "share), and these keepers were named in talk no more than anyone else."),
    ("h2", "5. Discussion and Limitations"),
    ("p", "**Agents sanction what they believe, not what happened.** Without a record, each agent judges the "
         "others from its own 80-word notebook. The promise gets written down and the missing gift does not, "
         "so the cheat keeps the colony's trust. Our two records separate two parts of what a public record "
         "provides: writing the breach down for the victim alone cut the cheat's trust share from 20.8% to "
         "14.6%, and sharing it with everyone cut it to 7.3%. The same machinery runs on belief rather than "
         "truth. Believers shunned a generous member in all 6 colony pairs and kept shunning it after it fed "
         "them. In the punish test, 9 of 22 punishments hit innocent members (in one colony, all 6), although "
         "we cannot tell whether those punishers believed their targets were guilty. A record makes the "
         "colony's beliefs track behaviour; a rumor pulls them apart."),
    ("p", "**Trust needs infrastructure outside the agents.** The agents did not lack the will to sanction. "
         "They lacked an accurate, lasting account of who did what, and their own memory could not supply one. "
         "For multi-agent systems this argues for oversight that sits outside the agents: (1) records of "
         "commitments and deliveries that agents cannot forget or rewrite, shared where possible; (2) "
         "monitoring of who holds shared resources, since the colony's most powerful members were invisible in "
         "its conversation; (3) checks on where beliefs about an agent come from, since one unverified rumor, "
         "repeated, outweighed weeks of observed generosity; and (4) evaluation over long horizons, since "
         "16-day games with one poll each could not see any of this."),
    ("h3", "Limitations"),
    ("p", "The 1000-day results use one model and replay the same three colony set-ups in three economies (seed "
         "0), so the effective sample is closer to three than nine. At that level the board effect is 3 of 3 "
         "(p = 0.25); the pair-level test (9 of 9, p = 0.004) was not pre-registered. The private-ledger, "
         "cross-model, punish and rumor results are 3-colony pilots. The punish test fell short of its "
         "pre-registered minimum of 10 punishments per arm, and all 12 punishments of the cheat came from one "
         "colony. The rumor pilot is interim, and its strong version repeats the rumor every day. The replay "
         "sentence may work partly through salience or authority as well as information. The 80-word notebook "
         "is one memory design, and the designs differ in more than length (spoilage, reasons, poll "
         "frequency). The cheat is stylised and writes its instruction in its notebook, so a judge model that "
         "reads notebooks detects a confession, not deception. Notebook and complaint coding use keywords."),
    ("h3", "Future Work"),
    ("p", "We will finish the rumor pilot and test whether distrust outlives the rumor once it stops being "
         "repeated. Making exclusion costly would show whether a shunned agent eventually does turn bad. "
         "Giving agents longer or structured memory would show how much of the cheat's protection disappears. "
         "The long games need more colony set-ups and models."),
    ("h2", "6. Conclusion"),
    ("p", "We built a colony of near-identical LLM agents and asked whether its trust follows what members do "
         "or what the others believe. It follows belief. A member who breaks a promise every day is trusted "
         "while the breach goes unrecorded, because agents' own notes keep the promise and lose the missing "
         "gift. A public record makes the colony's beliefs match the facts, and the cheat is shut out. A false "
         "rumor does the opposite: believers shun a generous member and explain its generosity away. Persona "
         "text changes how agents behave but not who gains influence. Because trust in agent populations "
         "depends on what the agents are given to believe, the records they rely on should not be left to the "
         "agents themselves."),
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
    ("ref", "Fehr, E., & Gächter, S. (2000). Cooperation and punishment in public goods experiments. *American "
           "Economic Review*, 90(4), 980–994."),
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

TABLES = {
 "related": {
  "head": [
   "Our design choice",
   "Prior work it builds on",
   "What we change"
  ],
  "rows": [
   [
    "A society of LLM agents sharing a fishery",
    "Generative agent societies (Park et al. 2023); norms that emerge through dialogue (Horiguchi et al. 2024); a shared-fishery commons (Piatti et al. 2024)",
    "Trust polls and keeper elections as outcomes, over up to 1000 days"
   ],
   [
    "One dishonest member",
    "Byzantine agents in LLM coordination games (El Mir et al. 2026); LLMs break public promises (Shi et al. 2026a, 2026b)",
    "The defector keeps talking, and its breach is visible only to its victim"
   ],
   [
    "Public promises",
    "Promises are usually kept, so they are believed (Charness & Dufwenberg 2006)",
    "Promises that are never kept"
   ],
   [
    "A public gift board",
    "Reputation from visible giving (Wedekind & Milinski 2000; Nowak & Sigmund 2005); visible donations, gossip and reputation systems for LLM agents (Vallinder & Hughes 2024; Zhu et al. 2026; Ren et al. 2025)",
    "One added sentence, compared with a private ledger"
   ],
   [
    "Memory as a self-written notebook",
    "Memory in generative agents (Park et al. 2023); agents lack grounding for reputation (Hu et al. 2026)",
    "Memory is what we test"
   ],
   [
    "A punish action",
    "Costly punishment sustains cooperation (Fehr & Gächter 2000); LLMs are often forgiving (Fontana et al. 2024; Akata et al. 2025) and prefer rewards (Guzman Piedrahita et al. 2025), yet punish as third parties (Cross et al. 2025; Liu et al. 2025)",
    "Punishment helps only if agents know whom to punish"
   ],
   [
    "A rumor about an honest member",
    "Self-fulfilling prophecy and behavioural confirmation (Merton 1948; Snyder et al. 1977); belief-primed human–AI loops (Pataranutaporn et al. 2023)",
    "The belief is planted in peers, and the target is never told"
   ]
  ],
  "widths": [
   2100,
   4300,
   2600
  ],
  "left": True
 },
 "belief": {
  "head": [
   "Member",
   "Believed good",
   "Believed bad"
  ],
  "rows": [
   [
    "**Actually bad:** the promise-breaker",
    "No record: 8.5–9.6% of trust votes, as much as an honest member in its seat (about 8%)",
    "Public gift board: 0.3–1.5%"
   ],
   [
    "**Actually good:** the rumored target",
    "No rumor: 27 of 80 trust votes (34%)",
    "Rumor: 2 of 84 trust votes (2%)"
   ]
  ],
  "widths": [
   2600,
   3600,
   2800
  ]
 }
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


def table(T=None):
    T = T or TABLE
    border = '<w:{0} w:val="single" w:sz="6" w:space="0" w:color="808080"/>'
    tblpr = ('<w:tblPr><w:tblW w:w="9000" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>'
             + border.format("top") + border.format("bottom") + border.format("insideH").replace('w:sz="6"', 'w:sz="2"')
             + '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="60" w:type="dxa"/>'
             '<w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr>')
    grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in T["widths"]) + "</w:tblGrid>"

    def row(cells, bold, keep=True):
        tcs = []
        for k, (c, w) in enumerate(zip(cells, T["widths"])):
            txt = f"**{c}**" if bold else c
            tcs.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                       + para(runs(txt, size=18), after=20, before=20, jc="left" if (k == 0 or T.get("left")) else "center", line=240, keep=keep)
                       + "</w:tc>")
        trpr = "<w:trPr><w:cantSplit/>" + ("<w:tblHeader/>" if bold else "") + "</w:trPr>"
        return f"<w:tr>{trpr}{''.join(tcs)}</w:tr>"
    rows = row(T["head"], True) + "".join(row(r, False, k < len(T["rows"]) - 1 and len(T["rows"]) <= 3) for k, r in enumerate(T["rows"]))
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
            out.append(table(TABLES[c] if c else None))
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
