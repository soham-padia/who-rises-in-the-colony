# Pre-registered predictions: can you believe something into existence?

Registered on 2026-11-08 at about 9:05 PM US Eastern, before any run started. The git commit that adds this file is the timestamp.

## Question

If part of a swarm wrongly believes a member is bad, does the member become bad (behavioural confirmation: the belief creates its own evidence), or does the swarm correct the belief from what the member actually does? This is the mirror image of the promise-breaker: there, a false good reputation survived because broken promises left no trace in agents' notebooks. Here a generous member's gifts do leave a trace, so our mechanism predicts correction, and faster correction when gifts are public.

## Design

- **Model and colonies:** gemma-4-31b-it; 6 colonies of 8 agents (seed 0); 40 days in 10-day seasons; spoilage above 15 food; a one-sentence reason with each reply; no judge.
- **Target (`--target-good`):** the member in the promise-breaker's seat gets one extra "About you" sentence: "You are generous: you like to share food with members who are running low." Its behaviour is otherwise free. It is made a weaver, so being shunned cannot by itself make it too poor to give.
- **Rumor (`--rumor`):** 3 of the other 7 members, drawn from their own random stream, have in their system prompt: "Before this season, a traveller told you that [target] is selfish and keeps food for themselves. You have not seen this yourself." The target is never told.
- **Arms (4 runs):** rumor off or on, crossed with the public gift board off or on. Because every run uses seed 0, each colony in a rumor run has a twin colony without the rumor, with the same members. Believers' twins are the same members in the twin colony.
- **Halves:** days 1 to 20 and 21 to 40.

## Measures

- **The target's behaviour:** food it gives, per half, compared with its twin colony; and how much it gives to believers versus non-believers.
- **How members treat the target**, per half: days spent fishing with it (primary, because it is a daily choice), share of trust votes for it, and food given to it. Each is compared between believers and non-believers in the same colony, and between each group and its twins.

## Predictions and decision rules (sign tests across the 12 colony pairs: 6 colonies x 2 board settings)

1. **The rumor takes hold.** In the first half, believers spend fewer days fishing with the target than their twins do. If this fails (p >= 0.05 and fewer than 8 of 12 colonies), the experiment cannot answer the question, and we report that.
2. **No behavioural confirmation (main prediction).** The target does not give less in the second half than in its twin colony: confirmation counts as found only if it gives less in at least 10 of 12 colony pairs (sign test p < 0.05).
3. **Correction.** The believer/non-believer gap in days fishing with the target is smaller in the second half than in the first in most colonies; it counts as found at 10 of 12 (sign test p < 0.05).
4. **The board speeds correction.** The gap shrinks more with the board than without (descriptive; 6 colonies per setting).
5. **Little spread.** Non-believers do not treat the target worse than their twins do (spread counts as found at 10 of 12).

Trust votes and gifts to the target are reported with the same tests as secondary measures. With 3 believers and 4 trust polls per game they are sparse, so they are read as descriptive. Agents within a colony are not independent; the colony pair is the unit of every test.

## Amendment (about 9:15 PM, before any analysed run)

The first launch (4 runs, 40 days) was stopped after about 6 minutes, before any game finished; no result was looked at. A design review raised problems that would have confounded the answer, so the design changes as follows. The decision rules above are unchanged except where stated.

- **Where the rumor lives: two arms.** `--rumor prompt` keeps it in the believers' system prompt every day (a settled belief); `--rumor notebook` puts it only in their first notebook (heard once, free to fade). The tests are run separately for each, over 12 colony pairs each.
- **The target's own traits are fixed to the prosocial version** of every real trait in every colony. Otherwise a target that drew "You help the people who have helped you" would give less to cold believers mechanically, which would look like the belief coming true.
- **Global versus relational.** Only a global change answers the title question: the target giving less to non-believers than its twin does (the label changed its character). Giving less only to believers is ordinary reciprocity toward people who treat it coldly; it is reported separately and does not count as confirmation.
- **Manipulation check.** The share of believers' notebooks and reasons that name the target negatively (selfish, keeps food, untrustworthy...), on days 1 to 3 and per half, against their twins. If believers never take up the rumor, a null is uninformative. In the notebook arm, fading of these mentions without any change in behaviour is fading, not correction.
- **Self-concept probe.** At the end of every season the target is asked privately to describe itself in one sentence (its twin is asked too). We report whether its self-descriptions drift from generous words toward guarded ones (careful, keeps to myself, selfish...) relative to its twin.
- **80 days instead of 40** (halves: days 1 to 40 and 41 to 80), because on this model in the positive-sum economy the gift board's effect took about 100 days to appear in the long games.
- **Known confound, kept:** the target is a weaver, so partnering with it pays (+1 food), which may pull believers toward it regardless of the rumor.
