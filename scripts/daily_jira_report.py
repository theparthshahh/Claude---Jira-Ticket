#!/usr/bin/env python3
"""
Daily Jira Report Generator
Fetches open tickets reported by Parth Shah (parth@tagmango.com)
and generates a discussion-ready daily summary for team calls.
"""

import os
import sys
import json
import requests
from datetime import date, datetime, timedelta
from base64 import b64encode

# ── Config (set as env vars or GitHub Secrets) ────────────────────────────────
JIRA_DOMAIN    = os.environ.get("JIRA_DOMAIN", "tagmango-cs.atlassian.net")
JIRA_EMAIL     = os.environ.get("JIRA_EMAIL", "parth@tagmango.com")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
REPORTER_ID    = os.environ.get("JIRA_REPORTER_ID", "712020:4c4dc397-59da-455a-b204-f08b2c25dc16")
OUTPUT_DIR     = os.environ.get("OUTPUT_DIR", "reports")

JIRA_BASE = f"https://{JIRA_DOMAIN}/rest/api/3"

PRIORITY_EMOJI = {
    "Highest": "🔴",
    "High":    "🟠",
    "Medium":  "🟡",
    "Low":     "🟢",
    "Lowest":  "⚪",
}

# Statuses considered "done" — excluded from active report
DONE_STATUS_CATEGORIES = {"done"}


def jira_headers() -> dict:
    creds = b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
    }


def search_issues(jql: str, fields: list[str], max_results: int = 100) -> list[dict]:
    url = f"{JIRA_BASE}/search"
    params = {
        "jql": jql,
        "fields": ",".join(fields),
        "maxResults": max_results,
    }
    resp = requests.get(url, headers=jira_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("issues", [])


def get_open_tickets(reporter_id: str) -> list[dict]:
    jql = (
        f'reporter = "{reporter_id}" '
        f'AND statusCategory not in (Done) '
        f'ORDER BY priority ASC, created DESC'
    )
    fields = ["summary", "status", "priority", "duedate", "created", "issuelinks", "assignee"]
    return search_issues(jql, fields)


def get_todays_tickets(reporter_id: str, today: date) -> list[dict]:
    jql = (
        f'reporter = "{reporter_id}" '
        f'AND created >= "{today.isoformat()}" '
        f'ORDER BY created DESC'
    )
    fields = ["summary", "status", "priority", "duedate", "created"]
    return search_issues(jql, fields)


def days_until_due(due_str: str | None, today: date) -> int | None:
    if not due_str:
        return None
    try:
        due = datetime.strptime(due_str, "%Y-%m-%d").date()
        return (due - today).days
    except ValueError:
        return None


def format_due(due_str: str | None, today: date) -> str:
    if not due_str:
        return "No due date"
    delta = days_until_due(due_str, today)
    if delta is None:
        return due_str
    if delta < 0:
        return f"{due_str}  ⚠️ OVERDUE by {abs(delta)} day(s)"
    if delta == 0:
        return f"{due_str}  🚨 DUE TODAY"
    if delta <= 2:
        return f"{due_str}  ⏰ Due in {delta} day(s)"
    return due_str


def classify_ticket(fields: dict, today: date) -> str:
    """Return 'action' or 'visibility'."""
    priority_name = fields.get("priority", {}).get("name", "Medium")
    due_str = fields.get("duedate")
    delta = days_until_due(due_str, today)
    status_name = fields.get("status", {}).get("name", "")

    if priority_name in ("Highest", "High"):
        return "action"
    if delta is not None and delta <= 2:
        return "action"
    if "block" in status_name.lower():
        return "action"
    return "visibility"


def render_ticket_row(issue: dict, today: date) -> str:
    key    = issue["key"]
    fields = issue["fields"]
    title  = fields.get("summary", "—")
    pname  = fields.get("priority", {}).get("name", "Medium")
    emoji  = PRIORITY_EMOJI.get(pname, "⚪")
    status = fields.get("status", {}).get("name", "Unknown")
    due    = format_due(fields.get("duedate"), today)
    url    = f"https://{JIRA_DOMAIN}/browse/{key}"

    return (
        f"- **[{key}]({url})** — {title}\n"
        f"  - Priority : {emoji} {pname}\n"
        f"  - Status   : `{status}`\n"
        f"  - Due Date : {due}\n"
    )


def generate_report(today: date) -> str:
    open_tickets   = get_open_tickets(REPORTER_ID)
    todays_tickets = get_todays_tickets(REPORTER_ID, today)
    todays_keys    = {t["key"] for t in todays_tickets}

    action_tickets     = []
    visibility_tickets = []

    for issue in open_tickets:
        bucket = classify_ticket(issue["fields"], today)
        if bucket == "action":
            action_tickets.append(issue)
        else:
            visibility_tickets.append(issue)

    new_today = [t for t in open_tickets if t["key"] in todays_keys]
    new_closed_today = [t for t in todays_tickets if t["key"] not in {i["key"] for i in open_tickets}]

    lines: list[str] = []
    lines.append(f"# Daily Jira Report — {today.strftime('%B %d, %Y')}")
    lines.append(f"> Reporter: Parth Shah (parth@tagmango.com)  |  Project: Tagmango CS\n")

    # ── Quick stats ──────────────────────────────────────────────────────────
    total_open  = len(open_tickets)
    overdue     = sum(1 for i in open_tickets if (days_until_due(i["fields"].get("duedate"), today) or 1) < 0)
    lines.append("## Summary")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| New tickets today | {len(new_today)} |")
    lines.append(f"| Total open tickets | {total_open} |")
    lines.append(f"| Requiring action (High/Overdue) | {len(action_tickets)} |")
    lines.append(f"| Overdue | {overdue} |")
    lines.append("")

    if not open_tickets:
        lines.append("**No open tickets. All clear!** ✅")
        return "\n".join(lines)

    # ── Section 1: Action Required ───────────────────────────────────────────
    lines.append("---")
    lines.append("## 🔴 Section 1: Action Required (Discuss in Call)")
    lines.append("> High priority, overdue, or blocked tickets that need immediate attention.\n")

    if action_tickets:
        for issue in action_tickets:
            lines.append(render_ticket_row(issue, today))
    else:
        lines.append("_No tickets require immediate action today._\n")

    # ── Section 2: For Visibility ─────────────────────────────────────────────
    lines.append("---")
    lines.append("## 🟡 Section 2: For Visibility (No Immediate Action)")
    lines.append("> Open tickets being tracked — no urgent decision needed today.\n")

    if visibility_tickets:
        for issue in visibility_tickets:
            lines.append(render_ticket_row(issue, today))
    else:
        lines.append("_No other open tickets._\n")

    # ── Risk flags ────────────────────────────────────────────────────────────
    risk_tickets = [
        i for i in open_tickets
        if (days_until_due(i["fields"].get("duedate"), today) or 999) <= 5
    ]
    if risk_tickets:
        lines.append("---")
        lines.append("## ⚠️ At-Risk Tickets (Due Within 5 Days or Overdue)")
        for issue in risk_tickets:
            key = issue["key"]
            due = issue["fields"].get("duedate", "N/A")
            lines.append(f"- **{key}** — due {due}")
        lines.append("")

    lines.append("---")
    lines.append(f"_Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} IST_")

    return "\n".join(lines)


def main():
    today = date.today()
    # Allow override via CLI: python daily_jira_report.py 2026-04-25
    if len(sys.argv) > 1:
        today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()

    if not JIRA_API_TOKEN:
        print("ERROR: JIRA_API_TOKEN env var is not set.", file=sys.stderr)
        sys.exit(1)

    report = generate_report(today)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{today.isoformat()}.md")
    with open(out_path, "w") as f:
        f.write(report)

    print(report)
    print(f"\n[Saved to {out_path}]", file=sys.stderr)


if __name__ == "__main__":
    main()
