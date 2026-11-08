# Pre-registered prediction: who gets punished, with and without the gift board

Registered on 2026-11-08 at about 6:30 PM US Eastern, before either run started. The git commit that adds this file is the timestamp.

## Question

Our results so far say the colony fails to sanction the promise-breaker because the breach is not on record: victims remember the promise and not the missing gift, and one explicit sentence about the missing food cuts their support. If information is the bottleneck, then giving agents a direct way to punish should not help on its own. They should aim punishment at the promise-breaker only when the breach is visible.

## Design

- **Model and colonies:** gemma-4-26b-a4b-it; the same 3 colonies of 8 agents as the other 40-day runs (seed 0); 40 days in 10-day seasons; spoilage above 15 food; a one-sentence reason with each reply; judge gemma-4-31b-it.
- **Punish action (`--punish`):** once a day each member may name one member to punish. The punisher loses 1 food and the target loses 2 (never below 0). Only the two members involved are told.
- **Arms (2 runs):** promise-breaker with `--punish`, without the gift board and with it (`--public-ledger`).

## Primary outcome

The share of punishments aimed at the promise-breaker, counting only punishments by the other 7 members. Chance is 1/7 (14.3%).

## Prediction and decision rule

- **Supports the mechanism** if, with the board, at least 2/7 (28.6%) of punishments hit the promise-breaker, and that share is at least 15 points higher than without the board.
- **Contradicts it** if, without the board, at least 2/7 of punishments hit the promise-breaker. That would mean agents target the cheat without a record, so information is not the whole bottleneck.
- **Inconclusive** if members other than the promise-breaker punish fewer than 10 times in either arm, or if neither rule above applies.

## Also reported, whatever the result

- Punishments of innocent members per arm, and how many distinct members ever punish.
- Whether victims (members the promise-breaker promised food to) punish it more than bystanders do.
- The promise-breaker's share of trust votes in each arm, next to the earlier gemma-4-26b runs without the punish action.
- Statistics: a binomial test against 1/7 within each arm and Fisher's exact test between arms. Punishments by the same member are not independent and there are only 3 colonies, so the counts are reported in full and the tests read as descriptive.
