#!/usr/bin/env python3
"""
Daily Jira Ticket Report Generator — Parth Shah (parth@tagmango.com)
Fetches all open tickets reported by Parth and outputs a discussion-ready
report for daily team calls.
"""

import os
import sys
import json
import argparse
from datetime import date, datetime, timedelta
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]
REPORTER_ACCOUNT_ID = os.environ["JIRA_REPORTER_ACCOUNT_ID"]

AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json"}

CLOSED_STATUSES = {"Done", "Closed", "Resolved"}

PRIORITY_ORDER = {"Highest": 0, "High": 1, "Medium": 2, "Low": 3, "Lowest": 4}


def jql_search(jql: str, fields: list[str], max_results: int = 100) -> list[dict]:
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/search"
    params = {
        "jql": jql,
        "fields": ",".join(fields),
        "maxResults": max_results,
    }
    resp = requests.get(url, headers=HEADERS, auth=AUTH, params=params)
    resp.raise_for_status()
    return resp.json().get("issues", [])


def fetch_todays_tickets(report_date: date) -> list[dict]:
    date_str = report_date.strftime("%Y-%m-%d")
    jql = (
        f'reporter = "{REPORTER_ACCOUNT_ID}" '
        f'AND created >= "{date_str}" AND created <= "{date_str} 23:59"'
    )
    return jql_search(jql, ["summary", "status", "priority", "duedate", "issuetype", "assignee"])


def fetch_open_tickets() -> list[dict]:
    closed = ", ".join(f'"{s}"' for s in CLOSED_STATUSES)
    jql = (
        f'reporter = "{REPORTER_ACCOUNT_ID}" '
        f"AND status NOT IN ({closed}) "
        f"ORDER BY priority ASC, duedate ASC"
    )
    return jql_search(
        jql,
        ["summary", "status", "priority", "duedate", "issuetype", "assignee", "created"],
    )


def parse_ticket(issue: dict) -> dict:
    f = issue["fields"]
    priority_name = (f.get("priority") or {}).get("name", "None")
    status_name   = (f.get("status") or {}).get("name", "Unknown")
    status_cat    = ((f.get("status") or {}).get("statusCategory") or {}).get("key", "")
    assignee      = (f.get("assignee") or {}).get("displayName", "Unassigned")
    due_raw       = f.get("duedate")
    due_date      = datetime.strptime(due_raw, "%Y-%m-%d").date() if due_raw else None
    created_raw   = f.get("created", "")
    created_date  = datetime.fromisoformat(created_raw[:10]).date() if created_raw else None

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
        "created_date": created_date,
    }


def is_overdue(ticket: dict, today: date) -> bool:
    return ticket["due_date"] is not None and ticket["due_date"] < today


def is_nearing_due(ticket: dict, today: date, days: int = 3) -> bool:
    if ticket["due_date"] is None:
        return False
    return today <= ticket["due_date"] <= today + timedelta(days=days)


def age_days(ticket: dict, today: date) -> Optional[int]:
    if ticket["created_date"]:
        return (today - ticket["created_date"]).days
    return None


def format_date(d: Optional[date]) -> str:
    return d.strftime("%b %d, %Y") if d else "Not set"


def classify_tickets(tickets: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    action, visibility = [], []
    for t in tickets:
        if (
            t["priority"] in ("Highest", "High")
            or is_overdue(t, today)
            or is_nearing_due(t, today)
            or t["status_cat"] not in ("done",) and age_days(t, today) is not None and age_days(t, today) > 180
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
    a = age_days(ticket, today)
    if a is not None and a > 90:
        flags.append(f"Open {a} days")
    if ticket["status_cat"] == "done":
        flags.append("In done-category — confirm closure")
    return flags


def render_report(
    report_date: date,
    todays_count: int,
    action: list[dict],
    visibility: list[dict],
) -> str:
    today = report_date
    lines = []
    sep = "-" * 68

    lines += [
        sep,
        f"  DAILY JIRA REPORT — Parth Shah | {report_date.strftime('%B %d, %Y')}",
        sep,
        f"  Tickets created today : {todays_count}",
        f"  Total open tickets    : {len(action) + len(visibility)}",
        sep,
        "",
    ]

    # --- ACTION REQUIRED ---
    lines += [
        "  [ACTION REQUIRED — Discuss in Call]",
        "",
    ]
    if not action:
        lines.append("  No high-priority or urgent tickets today.")
    else:
        for t in sorted(action, key=lambda x: x["priority_ord"]):
            flags = build_flags(t, today)
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
    lines += [
        "  [FOR VISIBILITY — No Immediate Action]",
        "",
    ]
    if not visibility:
        lines.append("  All open tickets require attention (see above).")
    else:
        for t in sorted(visibility, key=lambda x: x["priority_ord"]):
            flags = build_flags(t, today)
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

    # --- SUMMARY TABLE ---
    lines += ["  QUICK REFERENCE TABLE", ""]
    col = "{:<12} {:<10} {:<30} {:<14} {}"
    lines.append(col.format("TICKET", "PRIORITY", "STATUS", "DUE DATE", "FLAGS"))
    lines.append("  " + "-" * 90)
    all_tickets = sorted(action + visibility, key=lambda x: x["priority_ord"])
    for t in all_tickets:
        flags = build_flags(t, today)
        flag_str = " | ".join(flags) if flags else "-"
        status_short = t["status"][:28]
        lines.append(
            col.format(t["key"], t["priority"], status_short, format_date(t["due_date"]), flag_str)
        )

    lines += ["", sep, "  Generated by jira_daily_report.py", sep]
    return "\n".join("" if l == "" else ("" if l.startswith("  ") else "  ") + l for l in lines)


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
        help="Report date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save report to reports/<date>.txt in addition to printing",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output raw ticket data as JSON instead of formatted report",
    )
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date)

    todays_raw  = fetch_todays_tickets(report_date)
    open_raw    = fetch_open_tickets()

    if args.as_json:
        data = {
            "report_date":   report_date.isoformat(),
            "created_today": [parse_ticket(i) for i in todays_raw],
            "open_tickets":  [parse_ticket(i) for i in open_raw],
        }
        print(json.dumps(data, indent=2, default=str))
        return

    open_tickets = [parse_ticket(i) for i in open_raw]
    action, visibility = classify_tickets(open_tickets, report_date)
    report = render_report(report_date, len(todays_raw), action, visibility)

    print(report)

    if args.save:
        path = save_report(report, report_date)
        print(f"\nReport saved to: {path}")


if __name__ == "__main__":
    main()
