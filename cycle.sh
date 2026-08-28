#!/bin/zsh
set -euo pipefail

LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$LAB_DIR"
trend_output="$(python3 simulator.py)"
short_output="$(python3 short_term_simulator.py)"
printf '%s\n%s\n' "$trend_output" "$short_output"

# Public dashboard deployments only occur when the simulator actually changes a position.
# Market prices still refresh every three minutes in the browser, without wasting Pages builds.
if printf '%s\n%s' "$trend_output" "$short_output" | rg -q 'Operações: (BUY|SELL)'; then
  git add data/dashboard.json data/short-term-dashboard.json data/short-term-state.json logs/short-term-ledger.jsonl
  git commit -m "Record paper-trading operation" || true
  git push origin main
fi
