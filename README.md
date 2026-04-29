# Claude — Jira Ticket Daily Report

Automated daily Jira ticket summary for **Parth Shah (parth@tagmango.com)**, structured for team standups and daily calls.

## What It Does

Every day, this system:
1. Fetches all open/in-progress Jira tickets reported by Parth from Tagmango CS
2. Identifies tickets that are overdue, high priority, or blocked
3. Generates a structured markdown report split into two sections:
   - **Action Required** — High priority, overdue, or blocked tickets to discuss in the call
   - **For Visibility** — Remaining open tickets with no immediate urgency

Reports are saved to `reports/YYYY-MM-DD.md`.

## Reports

| Date | Report |
|------|--------|
| 2026-04-25 | [reports/2026-04-25.md](reports/2026-04-25.md) |

## Setup

### 1. Install dependencies

```bash
pip install requests python-dotenv
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env and fill in your Jira API token
```

Generate your Jira API token at: https://id.atlassian.com/manage-profile/security/api-tokens

### 3. Run the report

```bash
# Generate today's report
python scripts/generate_daily_report.py

# Generate report for a specific date
python scripts/generate_daily_report.py --date 2026-04-25

# Print to stdout only (no file saved)
python scripts/generate_daily_report.py --stdout
```

## Automate with Cron

To run every weekday at 9:00 AM:

```bash
crontab -e
# Add this line:
0 9 * * 1-5 cd /path/to/Claude---Jira-Ticket && python scripts/generate_daily_report.py >> logs/cron.log 2>&1
```

## Report Structure

```
# Daily Jira Report — April 25, 2026

## 🔴 Action Required (Discuss in Call)
  - High/Highest priority tickets
  - Overdue tickets
  - Blocked tickets

## 🟡 For Visibility (No Immediate Action)
  - Medium/Low priority open tickets

## Summary Table
  - Quick-scan table of all open tickets with risk flags
```
