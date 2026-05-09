#!/usr/bin/env python3
"""
Daily Jira Report Generator
Reporter: Parth Shah (parth@tagmango.com)
Project: Tagmango CS (tagmango-cs.atlassian.net)
"""

import os
import sys
from datetime import date, datetime
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://tagmango-cs.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "parth@tagmango.com")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
REPORTER_ACCOUNT_ID = os.environ.get(
    "JIRA_REPORTER_ACCOUNT_ID", "712020:4c4dc397-59da-455a-b204-f08b2c25dc16"
)

PRIORITY_RANK = {"Highest": 0, "High": 1, "Medium": 2, "Low": 3, "Lowest": 4}

PRIORITY_BADGE = {
    "Highest": "🔴 HIGHEST",
    "High":    "🟠 HIGH",
    "Medium":  "🟡 MEDIUM",
    "Low":     "🟢 LOW",
    "Lowest":  "⚪ LOWEST",
}

ACTION_PRIORITIES = {"Highest", "High"}


def get_auth() -> HTTPBasicAuth:
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def search_issues(jql: str, max_results: int = 100) -> list:
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/search"
    fields = "summary,status,priority,duedate,assignee,issuelinks"
    params = {"jql": jql, "fields": fields, "maxResults": max_results}
    resp = requests.get(url, auth=get_auth(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("issues", [])


def format_due_date(due: Optional[str], today: date) -> str:
    if not due:
        return "No Due Date"
    try:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        days_diff = (d - today).days
        if days_diff < 0:
            return f"{d.strftime('%b %d, %Y')}  ⚠️ OVERDUE by {abs(days_diff)} days"
        elif days_diff <= 3:
            return f"{d.strftime('%b %d, %Y')}  ⏰ DUE IN {days_diff} day{'s' if days_diff != 1 else ''}"
        return d.strftime("%b %d, %Y")
    except ValueError:
        return due


def is_overdue(due: Optional[str], today: date) -> bool:
    if not due:
        return False
    try:
        return datetime.strptime(due, "%Y-%m-%d").date() < today
    except ValueError:
        return False


def is_due_soon(due: Optional[str], today: date) -> bool:
    if not due:
        return False
    try:
        days_diff = (datetime.strptime(due, "%Y-%m-%d").date() - today).days
        return 0 <= days_diff <= 3
    except ValueError:
        return False


def has_blocker(issue: dict) -> bool:
    links = issue.get("fields", {}).get("issuelinks", [])
    for link in links:
        if "is blocked by" in link.get("type", {}).get("inward", "").lower():
            return True
    return False


def build_ticket_block(issue: dict, today: date) -> str:
    fields = issue["fields"]
    key = issue["key"]
    summary = fields.get("summary", "—")
    priority = fields.get("priority", {}).get("name", "Unknown")
    status = fields.get("status", {}).get("name", "Unknown")
    due = fields.get("duedate")
    assignee = (fields.get("assignee") or {}).get("displayName", "Unassigned")
    url = f"{JIRA_BASE_URL}/browse/{key}"

    badge = PRIORITY_BADGE.get(priority, f"• {priority}")
    due_str = format_due_date(due, today)
    blocker_note = "  🚫 Has Blocker/Dependency" if has_blocker(issue) else ""

    lines = [
        f"  [{key}]({url}) — {summary}",
        f"  Priority   : {badge}",
        f"  Status     : {status}",
        f"  Due Date   : {due_str}",
        f"  Assignee   : {assignee}",
    ]
    if blocker_note:
        lines.append(f"  Note       :{blocker_note}")
    return "\n".join(lines)


def generate_report(today: date) -> str:
    today_str = today.strftime("%Y-%m-%d")
    display_date = today.strftime("%B %d, %Y")

    # All active (non-done) tickets by Parth
    open_jql = (
        f'reporter = "{REPORTER_ACCOUNT_ID}" '
        f'AND statusCategory NOT IN ("Done") '
        f'ORDER BY priority ASC, duedate ASC'
    )

    # Tickets created today by Parth
    today_jql = (
        f'reporter = "{REPORTER_ACCOUNT_ID}" '
        f'AND created >= "{today_str}" AND created <= "{today_str}" '
        f'ORDER BY priority ASC'
    )

    open_issues = search_issues(open_jql)
    today_issues = search_issues(today_jql)

    # Separate into Action Required vs For Visibility
    action_tickets = []
    visibility_tickets = []

    for issue in open_issues:
        fields = issue["fields"]
        priority = fields.get("priority", {}).get("name", "Medium")
        due = fields.get("duedate")
        if (
            priority in ACTION_PRIORITIES
            or is_overdue(due, today)
            or is_due_soon(due, today)
            or has_blocker(issue)
        ):
            action_tickets.append(issue)
        else:
            visibility_tickets.append(issue)

    # Build report
    lines = [
        "=" * 65,
        f"  DAILY JIRA REPORT — {display_date}",
        f"  Reporter : Parth Shah  (parth@tagmango.com)",
        f"  Project  : Tagmango CS  |  tagmango-cs.atlassian.net",
        "=" * 65,
        "",
        f"  Tickets created today : {len(today_issues)}",
        f"  Total open tickets    : {len(open_issues)}",
        f"  Needing action        : {len(action_tickets)}",
        "",
    ]

    # ── Section 1: Action Required ──────────────────────────────────
    lines.append("┌─────────────────────────────────────────────────────────────┐")
    lines.append("│  🚨  ACTION REQUIRED  (Discuss in Call)                     │")
    lines.append("└─────────────────────────────────────────────────────────────┘")

    if action_tickets:
        for i, issue in enumerate(action_tickets, 1):
            fields = issue["fields"]
            due = fields.get("duedate")
            priority = fields.get("priority", {}).get("name", "")
            reasons = []
            if priority in ("Highest", "High"):
                reasons.append("high priority")
            if is_overdue(due, today):
                reasons.append("OVERDUE")
            if is_due_soon(due, today):
                reasons.append("due soon")
            if has_blocker(issue):
                reasons.append("has blocker")
            reason_str = " | ".join(reasons)
            lines.append(f"\n  {i}. Why flagged: {reason_str}")
            lines.append(build_ticket_block(issue, today))
    else:
        lines.append("\n  ✅  No high-priority or urgent tickets today.\n")

    lines.append("")

    # ── Section 2: For Visibility ───────────────────────────────────
    lines.append("┌─────────────────────────────────────────────────────────────┐")
    lines.append("│  👁️   FOR VISIBILITY  (No Immediate Action)                 │")
    lines.append("└─────────────────────────────────────────────────────────────┘")

    if visibility_tickets:
        for i, issue in enumerate(visibility_tickets, 1):
            lines.append(f"\n  {i}.")
            lines.append(build_ticket_block(issue, today))
    else:
        lines.append("\n  ✅  No additional open tickets.\n")

    lines.append("")

    # ── Risk Summary ────────────────────────────────────────────────
    overdue = [
        i for i in open_issues if is_overdue(i["fields"].get("duedate"), today)
    ]
    blocked = [i for i in open_issues if has_blocker(i)]
    no_due  = [i for i in open_issues if not i["fields"].get("duedate")]

    if overdue or blocked or no_due:
        lines.append("┌─────────────────────────────────────────────────────────────┐")
        lines.append("│  ⚠️   RISK SUMMARY                                           │")
        lines.append("└─────────────────────────────────────────────────────────────┘")
        if overdue:
            keys = ", ".join(i["key"] for i in overdue)
            lines.append(f"\n  Overdue        : {keys}")
        if blocked:
            keys = ", ".join(i["key"] for i in blocked)
            lines.append(f"  Blocked        : {keys}")
        if no_due:
            keys = ", ".join(i["key"] for i in no_due)
            lines.append(f"  No due date    : {keys}  ← Consider setting due dates")
        lines.append("")

    lines.append("=" * 65)
    lines.append(f"  Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 65)

    return "\n".join(lines)


def save_report(report: str, today: date) -> str:
    os.makedirs("reports", exist_ok=True)
    filename = f"reports/jira_report_{today.strftime('%Y-%m-%d')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    return filename


def main():
    if not JIRA_API_TOKEN:
        print("ERROR: JIRA_API_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    today = date.today()

    # Allow override via CLI arg for backfill: python jira_daily_report.py 2026-04-25
    if len(sys.argv) > 1:
        try:
            today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            print(f"ERROR: Invalid date format '{sys.argv[1]}'. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)

    print(f"Fetching Jira tickets for {today} …")
    report = generate_report(today)
    print(report)

    saved = save_report(report, today)
    print(f"\nReport saved to: {saved}")


if __name__ == "__main__":
    main()
