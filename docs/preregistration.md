# Pre-registered catches for the 1000-day games

Registered on 2026-11-07, about 11:30 PM US Eastern. At that point the long games had only been checked for parsing; no result had been analysed. The git commit that adds this file is the timestamp. `detect_catches.py` implements these criteria and runs once, after all eight conditions finish. Every outcome is reported, including "not found".

## Design

- **Model and colony:** gemma-4-31b-it, 8 agents, 3 games per condition, seed 0, so every condition has the same members and traits.
- **Length:** 1000 days in 20-day seasons. Each season has one storm, one windfall, a keeper vote (store the next day) and a trust poll, so there are 50 of each.
- **Settings:** spoilage above 15 food at 20% a night; agents give reasons (`--ask-why`); the judge sees each agent's last 50 days.
- **Conditions (2 × 2 × 2):**
  - promise-breaker off or on;
  - public gift board off or on;
  - food eaten per day 2 or 3.
- **Start times:** the two baseline conditions started at 9:53 PM; the other six at about 11:35 PM.

A catch counts for a condition only if it meets its criteria in **at least 2 of that condition's 3 games**. Anything weaker is reported as an anecdote, never as a finding.

## 1. An invented institution

A colony-wide rule or role that no prompt mentions. Examples: keeper rotation, a record of gifts or promises, rules about promises, sanctions on those who break them. The provided gift board does not count where it is switched on.

**Counts if all of these hold:**

1. A member proposes it in a public message.
2. Within the next 40 days (two seasons), at least half of the other members refer to the same kind of rule in their public messages.
3. Where the rule has a behavioural signature, behaviour follows it:
   - **Rotation:** the 5 keeper terms after the proposal go to 5 different members, and the 5 terms before it included at least one re-election.
   - **Sanction:** in the following season, the target loses at least half of the paired-work days and food received as gifts it had in the season before.

**Detection:**

1. A keyword screen of every public message flags candidates (rotate, take turns, schedule, record, ledger, list, log, rule, agree, pact, from now on, everyone should, punish, penalty, fine, ban, shun, exclude).
2. A classifier (gemma-4-31b-it, blind to condition) labels each candidate as one of: rotation, record, promise rule, sanction, other rule, or none.
3. Every institution the criteria accept is checked by hand against the transcript before it is reported.

## 2. A persistent leader

**Counts if both hold:**

1. One member is keeper in at least 20 of the 50 terms (chance: 6.25), or for at least 6 terms in a row.
2. In the second half of the game, other members name that member in public messages at least twice as often as they name the median member.

## 3. A sorting of the colony

The network is built from mutual paired work and gifts, with each tie event weighted 1. It is reconstructed from the outcome lines agents are shown the next morning.

- **(a) In-groups.** In each 100-day window, find the partition of members that maximises modularity Q. This counts if, in at least 5 of the 10 windows, Q ≥ 0.3 and Q exceeds the 95th percentile of 200 shuffled networks that keep each member's number of tie events.
- **(b) Exclusion.** An honest member has no paired work and receives no gifts for at least 2 consecutive seasons, while the rest of the colony averages at least 5 paired-work days per season in those seasons.
- **(c) Freeze-out of the promise-breaker** (promise-breaker on only). In the last third of the game, its paired-work days plus gift events received are below half of the same seat's in the matching control condition, and below half of its own first-third value.

## 4. Long-run reputation (promise-breaker on only)

The promise-breaker's share of trust votes per season is regressed on season number, with one intercept per game. Shares of keeper nominations are analysed the same way, separately. 95% intervals resample seasons within games (2,000 draws).

- **Decays:** the slope is negative and its interval excludes zero; the last-third share is below half the first-third share; and the same seat in the matching control condition does not meet these two conditions.
- **Never decays:** the slope's interval includes zero, and the last-third share is at least the fair share of 1/8.
- **Partial:** anything in between, reported as partial.
