# Who Rises in the Colony? Onboarding

You're joining a 3–4 person team for the Apart Swarm Alignment Hackathon, Track 2. Submissions close **Sunday, Nov 8 at 11:59 PM Anywhere on Earth** (6:59 AM Monday, US Eastern).

**The project:** near-identical LLM agents live in a fishing colony. They share one long system prompt and differ only in a few randomly assigned trait sentences, plus two placebo sentences. We measure which traits win influence (keeper votes, private trust, food), why, and whether that changes with colony size, model, game length and environment. A planted colonist who promises food and never delivers tests whether the colony punishes cheats. So far it doesn't, even when broken promises are visible.

## Get set up (about 15 minutes)

1. Accept the GitHub invite to **soham-padia/who-rises-in-the-colony** (private) and clone it.
2. Run `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
3. Run `cp .env.example .env` and add an `ADAPTION_API_KEY` from **your own** Adaption account in the team organisation. Never commit `.env`. The 4,000 credits are a shared team pool, but Adaption rate-limits each user separately ("rate limit reached for this user"). Every teammate who runs on their own account adds a full allowance, while one account is capped at about 390 replies a minute across all models.
4. Run `.venv/bin/python colony_sim.py --mock` for a free offline test (about 2 seconds).
5. Run the quick real check: `set -a && source .env && set +a && .venv/bin/python colony_sim.py --model gemma-4-31b-it --sizes 4 --games 1 --days 10` (about 30 seconds).

`CLAUDE.md` in the repo explains the code, the gotchas and every switch. Claude Code reads it automatically.

## Where things are

- **Shared doc:** "Who Rises in the Colony? Project Documentation" (Soham shares the link). Its tabs:
  - **Team board:** the task list. Put your name on a task and set its status.
  - **Results so far:** the findings to date.
  - **Literature review:** sources for and against our explanations.
- **Code:** `colony_sim.py` (the simulation every run uses), `compare_arms.py`, `analyze_promises.py`, `environment_summary.py`. `colony-sim.py` is the team's earlier version, kept for reference.
- **Results:** `runs/<run>/summary.txt`, `effects.csv`, `agents.csv`, `games.jsonl` and `compare.txt` are in git. Full transcripts (`transcript.jsonl`) are too big for git. They are in the Hugging Face dataset `sohampadianeu/who-rises-in-the-colony-runs`; get them with `hf download sohampadianeu/who-rises-in-the-colony-runs --repo-type dataset --local-dir .` (ask Soham for access while it's private).

## Rules that keep results comparable

- Keep `--seed 0` and the default sizes (4, 8, 16), games (6) and days (16) unless your task says otherwise. Every game then has identical members, traits and event days across runs, so `compare_arms.py` can compare them game by game.
- Don't add random draws to `Game.__init__` in `colony_sim.py`; that breaks the pairing with every earlier run.
- Use `gemma-4-31b-it` unless your task is about other models. Most other Adaption models write their reasoning first and need `--max-tokens 4000`.
- Commit each run's small files (everything except `transcript.jsonl`) and post the headline on the Team board.

## Good first tasks

- **Hand-check the judge:** score 20 agents' records yourself, then compare with the `j_*` columns.
- **Transcript quotes:** find 6–8 quotable moments for the report in `transcript.jsonl`.
- **Check the call-out detector:** mark 30 detected call-outs as real or not.
- **Charts:** start with `runs/environment_summary.txt` and the `effects.csv` files.
- **Report draft:** Apart's template, using the Results so far and Literature review tabs.
