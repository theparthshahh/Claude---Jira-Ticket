# Claude Daily Jira Report — Setup & Instructions

## Purpose
This repo is used to track and generate daily Jira ticket summaries for Parth Shah (parth@tagmango.com) from the Tagmango CS Jira project. Reports are structured for use in daily team calls.

---

## Daily Routine (Run Every Day)

### Step 1 — Fetch Open Tickets
Use the Atlassian Rovo MCP tool to query all non-closed tickets reported by Parth:

- **Cloud ID:** `238027ff-b658-4140-a820-b368ccc0b5b1`
- **Site:** `tagmango-cs.atlassian.net`
- **Parth's Account ID:** `712020:4c4dc397-59da-455a-b204-f08b2c25dc16`
- **Reporter Email:** `parth@tagmango.com`

**JQL Query:**
```
reporter = "712020:4c4dc397-59da-455a-b204-f08b2c25dc16"
AND status NOT IN (Done, Closed, Resolved)
ORDER BY created DESC
```

**Fields to fetch:** `summary`, `status`, `priority`, `duedate`, `created`, `issuetype`, `assignee`, `labels`, `description`, `comment`

### Step 2 — Categorise Tickets

**Action Required (Discuss in Call):**
- Priority = High or Highest
- OR due date is today or past (overdue)
- OR status = Blocked

**For Visibility (No Immediate Action):**
- Priority = Medium or Low
- No due date pressure
- No blockers

### Step 3 — Generate Report
For each ticket include:
- Ticket key + title
- Priority (Highest / High / Medium / Low)
- Due date (flag as OVERDUE if past today's date)
- Current status
- Last comment / last activity date
- Any blockers or dependencies noted in comments

### Step 4 — Save Report
Save as: `reports/YYYY-MM-DD-daily-report.md`

### Step 5 — Commit & Push
Branch: `claude/relaxed-brahmagupta-33Dlc`

---

## Report Structure

```
# Daily Jira Report — [DATE]

## 🔴 ACTION REQUIRED (Discuss in Call)
[High priority / overdue / blocked tickets]

## 🟡 FOR VISIBILITY (No Immediate Action)
[Remaining open tickets]

## Summary & Key Flags
[Table of critical flags]
```

---

## Reports Archive
Reports are saved in the `/reports` directory, named `YYYY-MM-DD-daily-report.md`.

| Date | File |
|------|------|
| 2026-04-25 | [reports/2026-04-25-daily-report.md](reports/2026-04-25-daily-report.md) |
