#!/bin/zsh
set -euo pipefail

LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$LAB_DIR"
trend_output="$(python3 simulator.py)"
printf '%s\n' "$trend_output"

# Public dashboard deployments only occur when the simulator actually changes a position.
# Market prices still refresh every three minutes in the browser, without wasting Pages builds.
if printf '%s' "$trend_output" | rg -q 'Operações: (BUY|SELL)'; then
  git add data/dashboard.json
  git commit -m "Record paper-trading operation" || true
  git push origin main
fi
