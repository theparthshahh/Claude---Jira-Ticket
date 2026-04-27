#!/usr/bin/env python3
"""
Daily Jira Ticket Report Generator — Parth Shah (parth@tagmango.com)
Fetches tickets created the previous day by Parth, filters to non-closed ones,
and outputs a discussion-ready report for daily team calls.
"""

import os
import json
import argparse
from datetime import date, datetime, timedelta
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL       = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL          = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN      = os.environ["JIRA_API_TOKEN"]
REPORTER_ACCOUNT_ID = os.environ["JIRA_REPORTER_ACCOUNT_ID"]

AUTH    = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json"}

CLOSED_STATUSES = {"Done", "Closed", "Resolved"}
PRIORITY_ORDER  = {"Highest": 0, "High": 1, "Medium": 2, "Low": 3, "Lowest": 4}


def jql_search(jql: str, fields: list[str], max_results: int = 100) -> list[dict]:
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/search"
    params = {"jql": jql, "fields": ",".join(fields), "maxResults": max_results}
    resp = requests.get(url, headers=HEADERS, auth=AUTH, params=params)
    resp.raise_for_status()
    return resp.json().get("issues", [])


def fetch_previous_day_tickets(target_date: date) -> tuple[list[dict], list[dict]]:
    """
    Fetches all tickets created on target_date by Parth.
    Returns (all_created, open_only) — open_only excludes closed/done/resolved.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    base_jql = (
        f'reporter = "{REPORTER_ACCOUNT_ID}" '
        f'AND created >= "{date_str}" AND created <= "{date_str} 23:59"'
    )
    fields = ["summary", "status", "priority", "duedate", "issuetype", "assignee", "created"]

    all_issues = jql_search(f"{base_jql} ORDER BY priority ASC", fields)

    closed = ", ".join(f'"{s}"' for s in CLOSED_STATUSES)
    open_issues = jql_search(
        f"{base_jql} AND status NOT IN ({closed}) ORDER BY priority ASC",
        fields,
    )
    return all_issues, open_issues


def parse_ticket(issue: dict, report_date: date) -> dict:
    f             = issue["fields"]
    priority_name = (f.get("priority") or {}).get("name", "None")
    status_name   = (f.get("status") or {}).get("name", "Unknown")
    status_cat    = ((f.get("status") or {}).get("statusCategory") or {}).get("key", "")
    assignee      = (f.get("assignee") or {}).get("displayName", "Unassigned")
    due_raw       = f.get("duedate")
    due_date      = datetime.strptime(due_raw, "%Y-%m-%d").date() if due_raw else None

    return {
        "key":          issue["key"],
        "url":          f"{JIRA_BASE_URL}/browse/{issue['key']}",
        "summary":      f.get("summary", "(no title)"),
        "priority":     priority_name,
        "priority_ord": PRIORITY_ORDER.get(priority_name, 99),
        "status":       status_name,
        "status_cat":   status_cat,
        "assignee":     assignee,
        "due_date":     due_date,
    }


def is_overdue(ticket: dict, today: date) -> bool:
    return ticket["due_date"] is not None and ticket["due_date"] < today


def is_nearing_due(ticket: dict, today: date, days: int = 3) -> bool:
    if ticket["due_date"] is None:
        return False
    return today <= ticket["due_date"] <= today + timedelta(days=days)


def classify_tickets(tickets: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    action, visibility = [], []
    for t in tickets:
        if (
            t["priority"] in ("Highest", "High")
            or is_overdue(t, today)
            or is_nearing_due(t, today)
        ):
            action.append(t)
        else:
            visibility.append(t)
    return action, visibility


def build_flags(ticket: dict, today: date) -> list[str]:
    flags = []
    if is_overdue(ticket, today):
        delta = (today - ticket["due_date"]).days
        flags.append(f"OVERDUE by {delta} days")
    elif is_nearing_due(ticket, today):
        flags.append("Due soon")
    if ticket["assignee"] == "Unassigned":
        flags.append("No assignee")
    if ticket["status_cat"] == "done":
        flags.append("In done-category — confirm closure")
    return flags


def format_date(d: Optional[date]) -> str:
    return d.strftime("%b %d, %Y") if d else "Not set"


def render_report(
    report_date: date,
    prev_day: date,
    total_created: int,
    action: list[dict],
    visibility: list[dict],
) -> str:
    today = report_date
    sep   = "-" * 68
    lines = [
        sep,
        f"  DAILY JIRA REPORT — Parth Shah | {report_date.strftime('%B %d, %Y')}",
        f"  Covering tickets created on: {prev_day.strftime('%B %d, %Y')}",
        sep,
        f"  Tickets created yesterday : {total_created}",
        f"  Open (not closed)         : {len(action) + len(visibility)}",
        sep,
        "",
    ]

    # --- ACTION REQUIRED ---
    lines += ["  [ACTION REQUIRED — Discuss in Call]", ""]
    if not action:
        lines.append("  No high-priority or urgent tickets from yesterday.")
    else:
        for t in sorted(action, key=lambda x: x["priority_ord"]):
            flags    = build_flags(t, today)
            flag_str = "  !! " + " | ".join(flags) if flags else ""
            lines += [
                f"  {t['key']}  [{t['priority']}]  {t['status']}",
                f"  {t['summary']}",
                f"  Due: {format_date(t['due_date'])}  |  Assignee: {t['assignee']}",
            ]
            if flag_str:
                lines.append(flag_str)
            lines += [f"  {t['url']}", ""]

    lines += [sep, ""]

    # --- FOR VISIBILITY ---
    lines += ["  [FOR VISIBILITY — No Immediate Action]", ""]
    if not visibility:
        if action:
            lines.append("  All open tickets from yesterday require attention (see above).")
        else:
            lines.append("  No open tickets from yesterday.")
    else:
        for t in sorted(visibility, key=lambda x: x["priority_ord"]):
            flags    = build_flags(t, today)
            flag_str = "  -- " + " | ".join(flags) if flags else ""
            lines += [
                f"  {t['key']}  [{t['priority']}]  {t['status']}",
                f"  {t['summary']}",
                f"  Due: {format_date(t['due_date'])}  |  Assignee: {t['assignee']}",
            ]
            if flag_str:
                lines.append(flag_str)
            lines += [f"  {t['url']}", ""]

    lines += [sep, ""]

    # --- SUMMARY TABLE (only when there are open tickets) ---
    open_tickets = action + visibility
    if open_tickets:
        lines += ["  QUICK REFERENCE TABLE", ""]
        col = "  {:<12} {:<10} {:<30} {:<14} {}"
        lines.append(col.format("TICKET", "PRIORITY", "STATUS", "DUE DATE", "FLAGS"))
        lines.append("  " + "-" * 88)
        for t in sorted(open_tickets, key=lambda x: x["priority_ord"]):
            flags      = build_flags(t, today)
            flag_str   = " | ".join(flags) if flags else "-"
            status_short = t["status"][:28]
            lines.append(col.format(t["key"], t["priority"], status_short, format_date(t["due_date"]), flag_str))
        lines += ["", sep, ""]

    lines += ["  Generated by jira_daily_report.py", sep]
    return "\n".join(lines)


def save_report(report: str, report_date: date, output_dir: str = "reports") -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"report_{report_date.strftime('%Y-%m-%d')}.txt")
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(report)
    return filename


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily Jira report for Parth Shah")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Report date in YYYY-MM-DD (default: today). Tickets from the day before this date are fetched.",
    )
    parser.add_argument("--save", action="store_true", help="Save report to reports/<date>.txt")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output raw JSON")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date)
    prev_day    = report_date - timedelta(days=1)

    all_raw, open_raw = fetch_previous_day_tickets(prev_day)

    if args.as_json:
        print(json.dumps({
            "report_date":      report_date.isoformat(),
            "previous_day":     prev_day.isoformat(),
            "all_created":      [parse_ticket(i, report_date) for i in all_raw],
            "open_tickets":     [parse_ticket(i, report_date) for i in open_raw],
        }, indent=2, default=str))
        return

    open_tickets        = [parse_ticket(i, report_date) for i in open_raw]
    action, visibility  = classify_tickets(open_tickets, report_date)
    report              = render_report(report_date, prev_day, len(all_raw), action, visibility)

    print(report)

    if args.save:
        path = save_report(report, report_date)
        print(f"\nReport saved to: {path}")


if __name__ == "__main__":
    main()
