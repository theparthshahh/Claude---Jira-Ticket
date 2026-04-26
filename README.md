# Claude — Jira Ticket Daily Report

Automated daily Jira report for **Parth Shah (parth@tagmango.com)** — fetches all open tickets and produces a discussion-ready summary for team calls.

## What it does

- Fetches all open Jira tickets (not Done / Closed / Resolved) reported by Parth
- Classifies them into **Action Required** (high priority / overdue / nearing due date) and **For Visibility**
- Prints a scannable, decision-focused report to stdout
- Optionally saves the report to `reports/YYYY-MM-DD.txt`

## Setup

```bash
# 1. Clone the repo and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env — set JIRA_API_TOKEN (get from https://id.atlassian.com/manage-profile/security/api-tokens)
```

## Usage

```bash
# Run for today
python3 jira_daily_report.py

# Run for a specific date
python3 jira_daily_report.py --date 2026-04-25

# Save report to reports/ directory
python3 jira_daily_report.py --save

# Output raw JSON
python3 jira_daily_report.py --json
```

## Scheduling (cron — runs Mon–Fri at 9 AM)

```bash
chmod +x run_daily_report.sh
crontab -e
# Add:
0 9 * * 1-5 /absolute/path/to/run_daily_report.sh >> /absolute/path/to/logs/jira_report.log 2>&1
```

## Report Sections

| Section | Criteria |
|---------|----------|
| **Action Required** | Priority = Highest / High, or overdue, or due within 3 days, or open 180+ days |
| **For Visibility** | All other open tickets |

## Files

```
jira_daily_report.py   # Main script
run_daily_report.sh    # Shell wrapper for cron
requirements.txt       # Python dependencies
.env.example           # Credential template
reports/               # Saved reports (git-ignored)
```
