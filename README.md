# Claude — Jira Ticket Daily Report

Automated daily Jira report for **Parth Shah** (`parth@tagmango.com`) — Tagmango CS project.

Every weekday at **9:00 AM IST** a GitHub Action fetches all open tickets reported by Parth, classifies them by urgency, and commits a Markdown report to `reports/YYYY-MM-DD.md` for use in daily team calls.

## Structure

```
reports/          # Daily Markdown reports (one file per day)
scripts/
  daily_jira_report.py   # Core report generator (uses Jira REST API v3)
.github/workflows/
  daily-jira-report.yml  # Scheduled GitHub Actions workflow
```

## Report Format

Each report has two sections:

| Section | Contents |
|---------|----------|
| **🔴 Action Required** | High/Highest priority, overdue, or blocked tickets — discuss in call |
| **🟡 For Visibility** | Open tickets with no immediate urgency |

Plus a quick stats table and key discussion talking points at the top.

## Setup

Add these three secrets to the repository (`Settings → Secrets → Actions`):

| Secret | Value |
|--------|-------|
| `JIRA_EMAIL` | `parth@tagmango.com` |
| `JIRA_API_TOKEN` | Atlassian API token from id.atlassian.com |
| `JIRA_REPORTER_ID` | `712020:4c4dc397-59da-455a-b204-f08b2c25dc16` |

## Run Manually

```bash
pip install requests
export JIRA_EMAIL=parth@tagmango.com
export JIRA_API_TOKEN=<your-token>
python scripts/daily_jira_report.py           # today
python scripts/daily_jira_report.py 2026-04-25  # specific date
```
