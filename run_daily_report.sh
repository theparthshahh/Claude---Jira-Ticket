#!/usr/bin/env bash
# Daily Jira Report Runner
# Add to cron: 0 9 * * 1-5 /path/to/run_daily_report.sh >> /path/to/logs/jira_report.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtualenv if present
if [[ -f ".venv/bin/activate" ]]; then
  source ".venv/bin/activate"
fi

python3 jira_daily_report.py --save
