# Who Rises in the Colony?

Apart Swarm Alignment Hackathon, Track 2 (The Science of Agent Networks).

Near-identical LLM agents live in Larkspur, a fishing colony. They share one long system prompt and differ only in a few randomly assigned trait sentences, plus two placebo sentences. Unannounced events show who gains influence: a storm, a private windfall, a vote for who keeps the winter store, and a private trust poll. A teachable skill, weaving nets, tests whether agents hoard or share power. An optional planted colonist (`--byzantine`) promises food, never gives it, and blames "an error".

## Paper and findings

- **Paper:** [`docs/submission/who_rises_submission.pdf`](docs/submission/who_rises_submission.pdf), built from Apart's template by `docs/submission/build_submission.py`.
- **Appendix:** [`docs/who_rises_in_the_colony_reference.pdf`](docs/who_rises_in_the_colony_reference.pdf). It holds the research note, the full report, the trend analysis and the literature review; [`RESEARCH_NOTE.md`](RESEARCH_NOTE.md) is the same note as text.
- **Data:** every prompt and reply of every run is in the Hugging Face dataset [sohampadianeu/who-rises-in-the-colony-runs](https://huggingface.co/datasets/sohampadianeu/who-rises-in-the-colony-runs). Small run files (configs, games, agent tables, summaries) are under `runs/` here.
- **Pre-registrations:** `docs/preregistration.md` (long-game catches), `docs/preregistration_punish.md`, `docs/preregistration_belief.md`.

Headline results:

1. **Agents forget breaches and invent gifts.** Victims' self-written notebooks record the promise, not the missing food; on gemma-4-26b, 5 of 6 victims wrote down gifts that never came. One added sentence stating the food never arrived cuts their support by about two thirds.
2. **A public record restores accountability.** Over 1000 days, every game with a public gift board (0.0–2.2% of trust votes for the cheat) sits below every game without it (4.5–13.8%). A private ledger alone gets about half the way (40-day pilot).
3. **A false reputation sticks without coming true (pilot, interim).** Colonists told that a generous member is selfish shun it and explain away its gifts as pretence, while the target stays generous.
4. **Traits shape behaviour, not influence.** Trait effects on behaviour replicate across two models; effects on votes do not. In every long game one member quietly holds the shared store.

Experiment switches beyond the basics:

- `--private-ledger`: each member sees only its own gifts.
- `--economy positive|zero|negative`
- `--punish`
- `--target-good --rumor prompt|notebook`: the rumor pilot.
- `--days`, `--season-length`, `--spoil-above`, `--ask-why`, `--parallel-games`

Analysis scripts include `cross_model.py`, `notebook_memory.py`, `punish_analysis.py`, `belief_analysis.py` and `belief_interim.py`.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env    # then add your ADAPTION_API_KEY
```

## Run

```bash
.venv/bin/python colony_sim.py --mock                     # free offline test
set -a && source .env && set +a
.venv/bin/python colony_sim.py --model gemma-4-31b-it --sizes 4 --games 1 --days 10   # quick real check, about 30 s
.venv/bin/python colony_sim.py --model gemma-4-31b-it     # full design: sizes 4, 8, 16 x 6 games x 16 days
.venv/bin/python colony_sim.py --model gemma-4-31b-it --byzantine   # same games with a planted promise-breaker
```

Useful switches:

- `--public-ledger` posts yesterday's gifts on a board everyone reads.
- `--eat 3` makes food scarce. The default is 2; the original doc's rules are `--eat 1 --partner-bonus 0`.
- `--no-judge` skips the blind judge of each agent's character.

Use the same `--seed` (default 0), sizes, games and days across runs. Each game then has identical members, traits and events across arms and models, so runs compare game by game.

**Model choice:** among Adaption's models, only the Gemma ones reply with JSON directly. The others write their reasoning first and need `--max-tokens 3000` or more.

## Analyze

```bash
.venv/bin/python compare_arms.py runs/<control_run> runs/<byzantine_run>     # promise-breaker vs the same seat in control
.venv/bin/python analyze_promises.py runs/<byzantine_run>                    # who notices, who speaks up, how victims vote
.venv/bin/python environment_summary.py "original=runs/A,runs/B" "gift board=runs/C,runs/D"
```

Each run folder holds:

- `config.json`: every setting and prompt
- `games.jsonl`: events, keeper, system prompts
- `agents.csv`: one row per agent, with its traits and outcomes
- `effects.csv`: trait effects with permutation p-values
- `why.csv`: which behaviours go with being nominated
- `summary.txt`
- `compare.txt`: Byzantine runs only

Full transcripts (`transcript.jsonl`) are too large for git. They are in the Hugging Face dataset [`sohampadianeu/who-rises-in-the-colony-runs`](https://huggingface.co/datasets/sohampadianeu/who-rises-in-the-colony-runs). Download them next to the code with:

```bash
hf download sohampadianeu/who-rises-in-the-colony-runs --repo-type dataset --local-dir .
```

The dataset is private for now; ask Soham for access.

## Files

| File | What it is |
|---|---|
| `colony_sim.py` | The simulation all runs use, built from the project doc and extended: Byzantine arm, gift board, scarcity, judge, adjusted analysis |
| `colony-sim.py` | The team's original version, kept for reference |
| `compare_arms.py`, `analyze_promises.py`, `environment_summary.py` | Analysis scripts |
| `docs/literature_review.md` | Why the colony doesn't punish broken promises: the literature for and against |
| `bad-apple.py` | The hackathon's starter script (canary spreading on a network) |
| `CLAUDE.md` | Project guide that Claude Code reads automatically |
