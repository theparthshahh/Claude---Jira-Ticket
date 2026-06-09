#!/usr/bin/env python3
"""
Daily Jira Report Generator for Parth Shah (parth@tagmango.com)
Run via Claude Code with Atlassian Rovo MCP tools.

Usage:
    Invoke through Claude Code — the script documents the JQL queries
    and report structure used to generate daily standups.

Config (edit below):
    CLOUD_ID     — Atlassian Cloud ID for tagmango-cs
    ACCOUNT_ID   — Parth's Jira account ID
    PROJECT_KEY  — Jira project key
"""

import json
from datetime import date, timedelta

CLOUD_ID = "238027ff-b658-4140-a820-b368ccc0b5b1"
ACCOUNT_ID = "712020:4c4dc397-59da-455a-b204-f08b2c25dc16"
PROJECT_KEY = "CS"
JIRA_BASE_URL = "https://tagmango-cs.atlassian.net"

TODAY = date.today().isoformat()

# JQL queries used by the daily report
QUERIES = {
    "new_today": (
        f'reporter = "{ACCOUNT_ID}" '
        f'AND created >= "{TODAY}" '
        f'ORDER BY created DESC'
    ),
    "open_not_closed": (
        f'reporter = "{ACCOUNT_ID}" '
        f'AND statusCategory != Done '
        f'ORDER BY priority ASC, duedate ASC'
    ),
}

FIELDS = [
    "summary", "status", "priority", "duedate",
    "created", "assignee", "labels", "issuetype", "issuelinks",
]

PRIORITY_EMOJI = {
    "Highest": "🔴",
    "High": "🔴",
    "Medium": "🟡",
    "Low": "🟢",
    "Lowest": "🟢",
}

RISK_FLAGS = {
    "overdue": "🔴 Critically Overdue",
    "no_owner_high": "🔴 Blocked, No Owner",
    "blocked": "🟡 Blocked on CS",
    "at_risk": "🟡 At Risk",
    "ok": "🟢 On Track",
}


def risk_level(issue: dict) -> str:
    fields = issue["fields"]
    due = fields.get("duedate")
    priority = fields.get("priority", {}).get("name", "Medium")
    assignee = fields.get("assignee")
    status_name = fields.get("status", {}).get("name", "")

    if due and due < TODAY:
        return RISK_FLAGS["overdue"]
    if not assignee and priority in ("Highest", "High"):
        return RISK_FLAGS["no_owner_high"]
    if "Require Details" in status_name or "Blocked" in status_name:
        return RISK_FLAGS["blocked"]
    if due:
        due_dt = date.fromisoformat(due)
        if due_dt <= date.today() + timedelta(days=2):
            return RISK_FLAGS["at_risk"]
    return RISK_FLAGS["ok"]


def action_required(issue: dict) -> bool:
    fields = issue["fields"]
    priority = fields.get("priority", {}).get("name", "Medium")
    due = fields.get("duedate")
    r = risk_level(issue)
    return (
        priority in ("Highest", "High")
        or (due and due <= TODAY)
        or "Critically Overdue" in r
        or "Blocked, No Owner" in r
    )


def format_report(today_issues: list, open_issues: list) -> str:
    today_keys = {i["key"] for i in today_issues}

    action = [i for i in open_issues if action_required(i)]
    visibility = [i for i in open_issues if not action_required(i)]

    lines = [
        f"# Daily Jira Report — {date.today().strftime('%d %B %Y')}",
        f"**Reporter:** Parth Shah (parth@tagmango.com)",
        f"**Project:** Tagmango CS",
        f"**Generated:** {TODAY}",
        "",
        "---",
        "",
    ]

    # New today
    lines.append("## New Tickets Created Today")
    if today_issues:
        for i in today_issues:
            f = i["fields"]
            p = f.get("priority", {}).get("name", "—")
            lines.append(
                f"- **[{i['key']}]({JIRA_BASE_URL}/browse/{i['key']})** "
                f"{f['summary']}  _(Priority: {p})_"
            )
    else:
        lines.append("> No new tickets were created today.")
    lines += ["", "---", ""]

    def issue_block(issue: dict) -> list[str]:
        f = issue["fields"]
        key = issue["key"]
        summary = f["summary"]
        priority = f.get("priority", {}).get("name", "—")
        status = f.get("status", {}).get("name", "—")
        due = f.get("duedate") or "Not set"
        assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")
        emoji = PRIORITY_EMOJI.get(priority, "⚪")
        risk = risk_level(issue)
        url = f"{JIRA_BASE_URL}/browse/{key}"

        block = [
            f"### {key} — {summary}",
            f"| Field | Detail |",
            f"|---|---|",
            f"| **Priority** | {emoji} {priority} |",
            f"| **Status** | {status} |",
            f"| **Due Date** | {due} |",
            f"| **Assignee** | {assignee} |",
            f"| **Risk** | {risk} |",
            f"| **Link** | [{key}]({url}) |",
            "",
        ]
        return block

    # Action Required
    lines.append("## 🔴 Action Required (Discuss in Call)")
    lines.append("")
    if action:
        for i in action:
            lines.extend(issue_block(i))
    else:
        lines.append("> No high-priority or urgent items today.")
    lines += ["---", ""]

    # For Visibility
    lines.append("## 🟡 For Visibility (No Immediate Action)")
    lines.append("")
    if visibility:
        for i in visibility:
            lines.extend(issue_block(i))
    else:
        lines.append("> No other open tickets.")
    lines += ["---", ""]

    # Summary table
    all_open = action + visibility
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| Key | Title (Short) | Priority | Status | Due Date | Risk |")
    lines.append("|---|---|---|---|---|---|")
    for i in all_open:
        f = i["fields"]
        key = i["key"]
        title = f["summary"][:55] + ("…" if len(f["summary"]) > 55 else "")
        priority = f.get("priority", {}).get("name", "—")
        status = f.get("status", {}).get("name", "—")
        due = f.get("duedate") or "—"
        risk = risk_level(i)
        lines.append(f"| {key} | {title} | {priority} | {status} | {due} | {risk} |")

    return "\n".join(lines)


if __name__ == "__main__":
    print("This script documents the report logic.")
    print("Run via Claude Code with Atlassian MCP tools enabled.")
    print(f"\nJQL (today's tickets): {QUERIES['new_today']}")
    print(f"\nJQL (open tickets):    {QUERIES['open_not_closed']}")
