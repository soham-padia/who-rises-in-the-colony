#!/usr/bin/env bash
# Gift-board arms of the belief study (docs/preregistration_belief.md, amendment 3), for a teammate to run on
# their OWN Adaption account. Setup once: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt,
# and a .env with your own ADAPTION_API_KEY=... (never share it). Then, on a Mac (keeps it awake):
#   caffeinate -ims bash run_belief_board.sh
# About 2.5-3 hours. When it ends, zip the two new runs/belief80/colony_*ledger_target* folders and send them.
set -euo pipefail
cd "$(dirname "$0")"
set -a; source .env; set +a
# If .env holds a teammate's key (with their permission), these runs use it instead of ADAPTION_API_KEY.
if [ -n "${ADAPTION_API_KEY_TEAMMATE:-}" ]; then export ADAPTION_API_KEY="$ADAPTION_API_KEY_TEAMMATE"; fi
mkdir -p runs/belief80
COMMON=(--model gemma-4-31b-it --max-tokens 700 --no-judge --sizes 8 --games 6 --parallel-games 3 --days 80
        --season-length 10 --spoil-above 15 --ask-why --target-good --public-ledger --out runs/belief80)
.venv/bin/python colony_sim.py "${COMMON[@]}" --rumor none > runs/belief80/board_none.log 2>&1 &
sleep 2
.venv/bin/python colony_sim.py "${COMMON[@]}" --rumor prompt > runs/belief80/board_prompt.log 2>&1 &
echo "running; progress: tail -f runs/belief80/board_*.log"
wait
grep -h "saved to" runs/belief80/board_*.log
