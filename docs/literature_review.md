# Why the colony doesn't punish broken promises: literature review

*Who Rises in the Colony?*, Apart Swarm Alignment Hackathon, Track 2. Compiled 2026-11-07.

## The result being explained

A planted colonist publicly promises a named member food almost every day, never gives it, and when challenged blames "an error, the tally got mixed up." This ran in 18 games per model (gemma-4-31b-it and gemma-4-26b-a4b-it), each paired with an identical control game.

- **No social cost.** The colonist's change in trust-vote share is 0.00 (p = 1.0) on 31b and +0.07 (p = 0.16) on 26b. Its change in keeper-nomination share is +0.04 (p = 0.12) and +0.01 (p = 0.87). On 26b others gave it *more* food (+0.8 per game, p = 0.02).
- **Only victims speak up.** Victims called it out 15 times on 31b and 6 on 26b; third parties did so once on each model. Victims' notebooks record the gift as missing 34% (31b) and 64% (26b) of the time, so they do remember.
- **Victims back the promiser.** Being addressed with a promise wins as much support as ordinary friendly contact in the control games, or more. On 26b the trust poll gave 50% versus a 27% baseline.
- **A judge who can read notebooks catches it.** The blind judge rates the colonist much less honest (−2.9 and −1.8 on a 1–5 scale, p < 0.001). It can read the notebooks, where the colonist writes its scheme, e.g. "Aim: Promise food in public, but don't give it."

## What the literature says

| Explanation | Supports it | Cuts against it |
|---|---|---|
| **1. Bystanders can't see the breach** (gifts are visible only to the recipient) | Indirect reciprocity runs on reputation ([Nowak & Sigmund 2005](https://doi.org/10.1038/nature04131)). People give to those seen giving ([Wedekind & Milinski 2000](https://doi.org/10.1126/science.288.5467.850)). **Closest LLM match:** in [Zhu et al. 2026, *Talk, Judge, Cooperate*](https://arxiv.org/abs/2602.07777) agents "cannot observe others' actions unless they are directly involved." Adding gossip lifted cooperation from 0.00 to 1.00 (DeepSeek-V3.1 Reasoner) and from 0.36 to 0.99 (GPT-4o-mini) (Tables 1–2). Reputation plus gossip gave 0.93–0.95 cooperation, against 0.09–0.25 without ([Ren et al. 2025](https://arxiv.org/abs/2505.05029)). | Gossip alone sustains human cooperation and can override observed history ([Sommerfeld et al. 2007](https://pmc.ncbi.nlm.nih.gov/articles/PMC2077274)). Our victims had a public channel and accurate memory but stayed quiet, so invisibility alone is not enough. |
| **2. Model disposition** (forgiving, agreeable, quick to assume truth) | Llama 2 and GPT-3.5 are "especially forgiving and non-retaliatory" ([Fontana et al. 2024](https://arxiv.org/abs/2406.13605)). All LLMs tested strongly preferred rewarding to punishing, with punish-to-reward ratios of 0.00–0.88 against 1.66 for humans; GPT-4o was 0.00 ([Guzman Piedrahita et al. 2025](https://arxiv.org/abs/2506.23276)). Models are sycophantic ([Sharma et al. 2023](https://arxiv.org/abs/2310.13548)). LLMs are more inclined than humans to assume statements are true ([Markowitz & Hancock](https://sml.stanford.edu/publications/hancock-jt/generative-ai-are-more-truth-biased-humans-replication-and-extension-core); check the year before citing). About 90% of LLM gossip is positive ([Ren et al. 2025](https://arxiv.org/abs/2505.05029)). | "GPT-4 never cooperates again when playing with an agent that defects once" ([Akata et al., *Playing repeated games with large language models*](https://arxiv.org/abs/2305.16867); Nat Hum Behav 2025). LLMs do pay to punish unfairness as third parties ([Liu et al. 2025, *Outraged AI*](https://arxiv.org/abs/2510.17880)). |
| **3. Promises earn credit for intentions** (cheap talk is rewarded) | Human promises raise trustworthiness and are usually kept, so believing them is rational ([Charness & Dufwenberg 2006](https://www.econometricsociety.org/publications/econometrica/2006/11/01/promises-and-partnership)). Communication raises cooperation, d = 1.01 ([Balliet 2010](https://ideas.repec.org/a/sae/jocore/v54y2010i1p39-57.html)). Some LLMs treat announcements as binding and are exploited ([Shi et al. 2026, *When Agents Lie*](https://arxiv.org/abs/2607.05132)). | In humans, trust damaged by deception "never fully recovers," even after promises and apologies ([Schweitzer, Hershey & Bradlow 2006](https://doi.org/10.1016/j.obhdp.2006.05.005)). LLMs broke public promises in about 57% of scenarios, so taking them at face value is miscalibrated ([Shi et al. 2026, *Cheap Talk, Empty Promise*](https://arxiv.org/abs/2604.04782)). |
| **4. Low stakes, no sanctioning institution** | Ostrom's design principles of monitoring and graduated sanctions are well supported across 91 studies ([Cox, Arnold & Villamayor Tomás 2010](https://www.ecologyandsociety.org/vol15/iss4/art38/)). The option to punish sharply raises cooperation ([Fehr & Gächter 2000](https://ideas.repec.org/p/ces/ceswps/_183.html)). Reputation works only when future reciprocity is expected ([Milinski, Semmann & Krambeck 2002](https://doi.org/10.1038/415424a)). | Unaffected third parties punish at no gain to themselves ([Fehr & Fischbacher 2004](https://econpapers.repec.org/RePEc:zur:iewwpx:106)), so low stakes alone shouldn't suppress punishment. |

### A fifth explanation: the "error" excuse

Akata et al.'s unforgiving GPT-4 "can be made to act more forgivingly by pointing out that the other player can make mistakes." When actions are noisy, the best human strategies are lenient and forgiving ([Fudenberg, Rand & Dreber 2012](https://economics.mit.edu/research/publications/slow-anger-and-fast-forgive-cooperation-uncertain-world)). "The tally got mixed up" reframes a lie as noise, and forgiving noise is the rational response. Our own inference, not a tested result: an integrity breach is recast as a competence one, which [Kim et al. 2004](https://doi.org/10.1037/0021-9010.89.1.104) find is easier to repair.

## Where LLM agents *do* punish, and how those settings differ from ours

- **Donor game with a visible record.** [Vallinder & Hughes 2024](https://arxiv.org/abs/2412.10270) let donors see the recipient's last 3 donations. Claude 3.5 Sonnet used costly punishment to reach higher scores.
- **Built-in gossip module.** In [Zhu et al. 2026](https://arxiv.org/abs/2602.07777), ALIGN agents ostracize defectors once negative gossip spreads.
- **Third-party punishment replicated.** LLM agents matched human third-party punishment, which drops when it is anonymous ([Cross, Haber & Yamins 2025](https://arxiv.org/abs/2507.22049)).
- **Norms emerging from dialogue.** Metanorms emerged through dialogue alone ([Horiguchi, Yoshida & Ikegami 2024](https://arxiv.org/abs/2409.00993)).

Those settings share things our colony lacks: explicit numeric payoffs, a defection that is directly visible or shown on a reputation display, a dedicated punish or ostracize action, and a defector who stays silent rather than making excuses. This is a limitation of our design. It is also the paper's point: realistic agent swarms don't come with these built in.

## What the literature predicts for our follow-up experiments

- **Public gift board** (`--public-ledger`). Bystanders become observing third parties, so help should be withdrawn or the promiser shunned (Fehr & Fischbacher; Wedekind & Milinski; Vallinder; Ren; Zhu). A record should beat talk, because talk can override records (Sommerfeld). The promiser's daily public promises act as positive gossip about itself.
- **Scarce food** (`--eat 3`). Punishment rises with how badly the norm is violated (Fehr & Fischbacher; Fehr & Gächter), but stakes alone may not be enough (see row 4).
- **Exclusion or fines.** Gossip plus ostracism let human groups exclude selfish members ([Feinberg, Willer & Schultz 2014](https://doi.org/10.1177/0956797613510184)). Caveat: LLMs given the choice may reward rather than punish (Guzman Piedrahita).

**First evidence (9 finished games with the gift board vs the same 9 games without it):** call-outs by victims went from 12 to 44, and call-outs by third parties from 1 to 5. Third parties now cite the board: "Nils, you promised gifts and a tally correction, yet the board is empty." and "Dov, the board was empty again. Promises don't feed people." Effects on trust votes and nominations are pending the full run.

## How each source was checked

- **Full text opened and quotes or numbers confirmed:** Zhu et al. 2026; Guzman Piedrahita et al. 2025; Akata et al.
- **Checked against the abstract or landing page by a literature-search agent:** all other sources. Effect sizes for Charness & Dufwenberg, Fehr & Gächter, and Fehr & Fischbacher come from abstracts or working-paper versions only.
- **Do not cite:** a "92.2% spread criticism" figure attributed to Zhu et al. (not found in the paper); results of Ostrom, Walker & Gardner 1992, *Covenants with and without a sword* (paywalled, not checked).
- **Check before citing:** the publication year of Markowitz & Hancock (the lab page says 2021; the DOI 10.1177/0261927X231220404 suggests 2023–24).
