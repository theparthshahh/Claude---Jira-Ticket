# Claude Code — Daily Jira Report Routine

## Purpose
Generate a daily discussion-ready Jira ticket summary for Parth Shah (parth@tagmango.com)
to use in team standups/calls.

## Daily Routine (run each morning)

### What Claude does
1. Fetches tickets created today using JQL: `reporter = "<accountId>" AND created >= "<today>"`
2. Fetches all open/in-progress tickets using JQL: `reporter = "<accountId>" AND statusCategory != Done`
3. Categorises tickets into **Action Required** vs **For Visibility**
4. Writes the report to `reports/YYYY-MM-DD.md`
5. Commits and pushes to the working branch

### Config
| Key | Value |
|---|---|
| Atlassian Cloud ID | `238027ff-b658-4140-a820-b368ccc0b5b1` |
| Jira Site | `https://tagmango-cs.atlassian.net` |
| Reporter Account ID | `712020:4c4dc397-59da-455a-b204-f08b2c25dc16` |
| Project | `CS` (Tagmango CS) |

### Report structure
- `reports/YYYY-MM-DD.md` — one file per day
- Section 1: **New Tickets Today**
- Section 2: **🔴 Action Required** — high priority / overdue / blocked with no owner
- Section 3: **🟡 For Visibility** — remaining open tickets
- Section 4: **Summary Table** + talking points

### Risk classification
| Condition | Flag |
|---|---|
| Due date in the past | 🔴 Critically Overdue |
| High/Highest priority + no assignee | 🔴 Blocked, No Owner |
| Status contains "Require Details" or "Blocked" | 🟡 Blocked on CS |
| Due within 2 days | 🟡 At Risk |
| Otherwise | 🟢 On Track |

## Repository layout
```
reports/          ← daily report files (YYYY-MM-DD.md)
scripts/          ← report generation logic
  generate_daily_report.py
CLAUDE.md         ← this file
```
