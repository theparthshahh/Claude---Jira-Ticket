#!/usr/bin/env python3
"""
Daily Jira Report Generator for Parth Shah (parth@tagmango.com)
Fetches open tickets from Tagmango CS Jira and generates a discussion-ready report.

Usage:
    python scripts/generate_daily_report.py
    python scripts/generate_daily_report.py --date 2026-04-25
    python scripts/generate_daily_report.py --stdout   # print to console only

Requirements:
    pip install requests python-dotenv
"""

import os
import sys
import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]
REPORTER_ACCOUNT_ID = os.environ["REPORTER_ACCOUNT_ID"]

AUTH = (JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json"}

PRIORITY_MAP = {
    "Highest": ("🔴", "Highest"),
    "High":    ("🔴", "High"),
    "Medium":  ("🟡", "Medium"),
    "Low":     ("🟢", "Low"),
    "Lowest":  ("🟢", "Lowest"),
}

ACTION_PRIORITIES = {"Highest", "High"}


def jira_get(path: str, params: dict = None) -> dict:
    url = f"{JIRA_BASE_URL}/rest/api/3/{path}"
    resp = requests.get(url, auth=AUTH, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_open_tickets(report_date: date) -> list[dict]:
    """Fetch tickets created today + all open tickets by reporter."""
    jql_parts = [
        f'reporter = "{REPORTER_ACCOUNT_ID}"',
        'statusCategory != Done',
    ]
    jql = " AND ".join(jql_parts) + " ORDER BY priority ASC, created ASC"

    fields = ",".join([
        "summary", "status", "priority", "duedate",
        "issuetype", "assignee", "created", "issuelinks", "labels",
    ])

    start = 0
    issues = []
    while True:
        data = jira_get("search", {
            "jql": jql,
            "fields": fields,
            "startAt": start,
            "maxResults": 50,
        })
        issues.extend(data["issues"])
        start += len(data["issues"])
        if start >= data["total"]:
            break

    return issues


def classify_ticket(issue: dict, today: date) -> dict:
    fields = issue["fields"]
    priority_name = fields.get("priority", {}).get("name", "Medium")
    icon, label = PRIORITY_MAP.get(priority_name, ("🟡", priority_name))

    due_raw = fields.get("duedate")
    due_date = datetime.strptime(due_raw, "%Y-%m-%d").date() if due_raw else None
    days_until_due = (due_date - today).days if due_date else None

    created_raw = fields.get("created", "")
    created_date = datetime.fromisoformat(created_raw[:10]).date() if created_raw else None
    age_days = (today - created_date).days if created_date else 0

    is_overdue = due_date and due_date < today
    is_due_soon = due_date and 0 <= days_until_due <= 3
    is_aged = age_days >= 30

    status = fields.get("status", {}).get("name", "Unknown")
    assignee = (fields.get("assignee") or {}).get("displayName", "Unassigned")

    action_required = (
        priority_name in ACTION_PRIORITIES
        or is_overdue
        or is_due_soon
        or "Blocked" in status
    )

    return {
        "key": issue["key"],
        "summary": fields.get("summary", "(no title)"),
        "priority_name": priority_name,
        "priority_icon": icon,
        "priority_label": label,
        "status": status,
        "due_date": due_date,
        "due_raw": due_raw,
        "days_until_due": days_until_due,
        "is_overdue": is_overdue,
        "is_due_soon": is_due_soon,
        "created_date": created_date,
        "age_days": age_days,
        "is_aged": is_aged,
        "assignee": assignee,
        "action_required": action_required,
        "url": f"{JIRA_BASE_URL}/browse/{issue['key']}",
    }


def format_due_date(t: dict) -> str:
    if not t["due_date"]:
        return "Not set"
    label = t["due_raw"]
    if t["is_overdue"]:
        overdue_days = abs(t["days_until_due"])
        return f"~~{label}~~ ⚠️ OVERDUE by {overdue_days} day{'s' if overdue_days != 1 else ''}"
    if t["is_due_soon"]:
        return f"{label} 🔔 Due in {t['days_until_due']} day{'s' if t['days_until_due'] != 1 else ''}"
    return label


def format_age(t: dict) -> str:
    d = t["age_days"]
    if d == 0:
        return "Today"
    if d < 7:
        return f"{d} day{'s' if d != 1 else ''} ago"
    weeks = d // 7
    if weeks < 4:
        return f"~{weeks} week{'s' if weeks != 1 else ''} ago"
    months = d // 30
    return f"~{months} month{'s' if months != 1 else ''} ago"


def render_ticket_block(t: dict, index: int) -> str:
    lines = [
        f"### {index}. {t['key']} — {t['summary']}",
        f"| Field | Detail |",
        f"|-------|--------|",
        f"| **Priority** | {t['priority_icon']} {t['priority_label']} |",
        f"| **Status** | {t['status']} |",
        f"| **Due Date** | {format_due_date(t)} |",
        f"| **Created** | {t['created_date']} ({format_age(t)}) |",
        f"| **Assignee** | {t['assignee']} |",
        f"| **Link** | [{t['key']}]({t['url']}) |",
        "",
    ]

    flags = []
    if t["is_overdue"]:
        flags.append(f"⚠️ Overdue by {abs(t['days_until_due'])} days — needs immediate resolution or closure")
    if t["is_aged"] and not t["is_overdue"]:
        flags.append(f"🕐 Ticket has been open for {format_age(t)} with no resolution")
    if t["assignee"] == "Unassigned":
        flags.append("👤 No assignee — ownership gap")
    if "Blocked" in t["status"]:
        flags.append("🚫 Ticket is blocked — dependency needs to be resolved")
    if "Require Details" in t["status"]:
        flags.append("📋 Awaiting details from CS — follow-up required")

    if flags:
        lines.append("**Flags:**")
        for f in flags:
            lines.append(f"- {f}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def generate_report(report_date: date, issues: list[dict]) -> str:
    today = report_date
    tickets = [classify_ticket(i, today) for i in issues]

    new_today = [t for t in tickets if t["created_date"] == today]
    action = [t for t in tickets if t["action_required"]]
    visibility = [t for t in tickets if not t["action_required"]]

    date_str = today.strftime("%B %d, %Y").replace(" 0", " ")
    lines = [
        f"# Daily Jira Report — {date_str}",
        "",
        f"**Reporter:** Parth Shah (parth@tagmango.com)  ",
        f"**Project:** Tagmango CS  ",
        f"**Generated:** {today.isoformat()}  ",
        f"**Scope:** All open/in-progress tickets created by Parth  ",
        "",
    ]

    if new_today:
        lines += [
            f"> **{len(new_today)} new ticket{'s' if len(new_today) != 1 else ''} created today.**",
            "",
        ]
    else:
        lines += [
            "> **Note:** No new tickets were created today. Active open tickets are listed below.",
            "",
        ]

    lines += ["---", ""]

    lines += ["## 🔴 Action Required (Discuss in Call)", ""]
    lines += ["> High priority, overdue, or blocked tickets that need immediate team decision or action.", ""]
    lines += ["---", ""]

    if action:
        for i, t in enumerate(action, 1):
            lines.append(render_ticket_block(t, i))
    else:
        lines += ["_No action-required tickets today._", "", "---", ""]

    lines += ["## 🟡 For Visibility (No Immediate Action)", ""]
    lines += ["> Medium/low priority open tickets — no urgent action needed.", ""]
    lines += ["---", ""]

    if visibility:
        for i, t in enumerate(visibility, 1):
            lines.append(render_ticket_block(t, i))
    else:
        lines += ["_No tickets in this category today._", "", "---", ""]

    lines += ["## Summary Table", ""]
    lines += ["| Ticket | Priority | Status | Due Date | Risk |"]
    lines += ["|--------|----------|--------|----------|------|"]

    for t in tickets:
        risks = []
        if t["is_overdue"]:
            risks.append(f"🔴 Overdue {abs(t['days_until_due'])}d")
        if t["is_due_soon"]:
            risks.append(f"🔔 Due in {t['days_until_due']}d")
        if t["assignee"] == "Unassigned":
            risks.append("👤 Unassigned")
        if t["is_aged"]:
            risks.append(f"🕐 Aged {format_age(t)}")
        if "Require Details" in t["status"]:
            risks.append("📋 Awaiting CS details")
        risk_str = " · ".join(risks) if risks else "—"
        due_str = t["due_raw"] or "—"
        lines.append(
            f"| [{t['key']}]({t['url']}) | {t['priority_icon']} {t['priority_label']} "
            f"| {t['status']} | {due_str} | {risk_str} |"
        )

    lines += [""]

    blockers = [t for t in tickets if "Blocked" in t["status"] or "Require Details" in t["status"]]
    overdue = [t for t in tickets if t["is_overdue"]]

    if blockers or overdue:
        lines += ["### Key Flags", ""]
        if overdue:
            keys = ", ".join(t["key"] for t in overdue)
            lines.append(f"- **Overdue tickets:** {keys} — need resolution or formal closure")
        if blockers:
            keys = ", ".join(t["key"] for t in blockers)
            lines.append(f"- **Blocked/awaiting details:** {keys} — CS team must follow up")
        unassigned = [t for t in tickets if t["assignee"] == "Unassigned"]
        if unassigned:
            keys = ", ".join(t["key"] for t in unassigned)
            lines.append(f"- **Unassigned tickets:** {keys} — ownership needs to be assigned")
        lines += [""]

    lines += ["---", ""]
    lines += [f"*Report generated by Claude (Jira Daily Summary Automation) | Tagmango CS*", ""]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate daily Jira report for Parth")
    parser.add_argument("--date", default=date.today().isoformat(), help="Report date (YYYY-MM-DD)")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout only, do not save file")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date)

    print(f"Fetching open Jira tickets for {report_date.isoformat()}...", file=sys.stderr)
    issues = fetch_open_tickets(report_date)
    print(f"Found {len(issues)} open ticket(s).", file=sys.stderr)

    report = generate_report(report_date, issues)

    if args.stdout:
        print(report)
        return

    repo_root = Path(__file__).parent.parent
    output_path = repo_root / "reports" / f"{report_date.isoformat()}.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(report)
    print(f"Report saved to {output_path}", file=sys.stderr)
    print(report)


if __name__ == "__main__":
    main()
