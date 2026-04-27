#!/usr/bin/env python3
"""
Daily Jira Ticket Report Generator — Parth Shah (parth@tagmango.com)

Per-run scope:
  1. Tickets created TODAY (report date) that are not closed
  2. Tickets created YESTERDAY (report date - 1) that are not closed
  3. Unclosed tickets created on the ANCHOR DATE (default: 2026-04-22)

Outputs a discussion-ready report for daily team calls.
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

# Anchor date — unclosed tickets from this date are always included in every report
ANCHOR_DATE = date(2026, 4, 22)

FIELDS = ["summary", "status", "priority", "duedate", "issuetype", "assignee", "created"]


# ---------------------------------------------------------------------------
# Jira helpers
# ---------------------------------------------------------------------------

def jql_search(jql: str, max_results: int = 100) -> list[dict]:
    url    = f"{JIRA_BASE_URL}/rest/api/3/issue/search"
    params = {"jql": jql, "fields": ",".join(FIELDS), "maxResults": max_results}
    resp   = requests.get(url, headers=HEADERS, auth=AUTH, params=params)
    resp.raise_for_status()
    return resp.json().get("issues", [])


def _date_window(d: date) -> str:
    return f'created >= "{d}" AND created <= "{d} 23:59"'


def _closed_clause() -> str:
    return "status NOT IN (" + ", ".join(f'"{s}"' for s in CLOSED_STATUSES) + ")"


def fetch_for_day(target: date, open_only: bool = False) -> list[dict]:
    reporter = f'reporter = "{REPORTER_ACCOUNT_ID}"'
    window   = _date_window(target)
    parts    = [reporter, window]
    if open_only:
        parts.append(_closed_clause())
    return jql_search(" AND ".join(parts) + " ORDER BY priority ASC")


# ---------------------------------------------------------------------------
# Ticket parsing
# ---------------------------------------------------------------------------

def parse_ticket(issue: dict) -> dict:
    f             = issue["fields"]
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


# ---------------------------------------------------------------------------
# Classification & flags
# ---------------------------------------------------------------------------

def is_overdue(t: dict, today: date) -> bool:
    return t["due_date"] is not None and t["due_date"] < today


def is_nearing_due(t: dict, today: date, days: int = 3) -> bool:
    return t["due_date"] is not None and today <= t["due_date"] <= today + timedelta(days=days)


def classify(tickets: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    action, visibility = [], []
    for t in tickets:
        if t["priority"] in ("Highest", "High") or is_overdue(t, today) or is_nearing_due(t, today):
            action.append(t)
        else:
            visibility.append(t)
    return action, visibility


def build_flags(t: dict, today: date) -> list[str]:
    flags = []
    if is_overdue(t, today):
        flags.append(f"OVERDUE by {(today - t['due_date']).days} days")
    elif is_nearing_due(t, today):
        flags.append("Due soon")
    if t["assignee"] == "Unassigned":
        flags.append("No assignee")
    if t["status_cat"] == "done":
        flags.append("In done-category — confirm closure")
    return flags


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def fmt_date(d: Optional[date]) -> str:
    return d.strftime("%b %d, %Y") if d else "Not set"


def _ticket_block(t: dict, today: date, marker: str = "  !!") -> list[str]:
    flags    = build_flags(t, today)
    flag_str = f"{marker} " + " | ".join(flags) if flags else ""
    block    = [
        f"  {t['key']}  [{t['priority']}]  {t['status']}",
        f"  {t['summary']}",
        f"  Due: {fmt_date(t['due_date'])}  |  Assignee: {t['assignee']}",
    ]
    if flag_str:
        block.append(flag_str)
    block += [f"  {t['url']}", ""]
    return block


def _section(title: str, tickets: list[dict], today: date, marker: str, empty_msg: str) -> list[str]:
    lines = [f"  [{title}]", ""]
    if not tickets:
        lines += [f"  {empty_msg}", ""]
    else:
        for t in sorted(tickets, key=lambda x: x["priority_ord"]):
            lines += _ticket_block(t, today, marker)
    return lines


def _table(tickets: list[dict], today: date) -> list[str]:
    if not tickets:
        return []
    col   = "  {:<12} {:<10} {:<30} {:<14} {}"
    lines = [
        "  QUICK REFERENCE",
        "",
        col.format("TICKET", "PRIORITY", "STATUS", "DUE DATE", "FLAGS"),
        "  " + "-" * 86,
    ]
    for t in sorted(tickets, key=lambda x: x["priority_ord"]):
        flags = build_flags(t, today)
        lines.append(col.format(
            t["key"], t["priority"], t["status"][:28],
            fmt_date(t["due_date"]), " | ".join(flags) if flags else "-",
        ))
    lines.append("")
    return lines


def render_report(
    report_date:    date,
    prev_day:       date,
    anchor_date:    date,
    today_all:      int,
    prev_all:       int,
    today_open:     list[dict],
    prev_open:      list[dict],
    anchor_open:    list[dict],
) -> str:
    today  = report_date
    sep    = "-" * 68
    lines  = [
        sep,
        f"  DAILY JIRA REPORT — Parth Shah | {report_date.strftime('%B %d, %Y')}",
        sep,
        f"  Today ({report_date.strftime('%b %d')})     — Created: {today_all}  |  Open: {len(today_open)}",
        f"  Yesterday ({prev_day.strftime('%b %d')})  — Created: {prev_all}  |  Open: {len(prev_open)}",
        f"  Anchor ({anchor_date.strftime('%b %d')})     — Still unclosed: {len(anchor_open)}",
        sep,
        "",
    ]

    # ---- Section 1: Today's open tickets ----
    lines.append(f"  === TODAY ({report_date.strftime('%B %d, %Y')}) ===")
    lines.append("")
    today_action, today_vis = classify(today_open, today)
    lines += _section("ACTION REQUIRED — Discuss in Call",  today_action, today, "  !!", "No high-priority or urgent tickets created today.")
    lines += _section("FOR VISIBILITY — No Immediate Action", today_vis,  today, "  --", "No other open tickets created today.")
    lines += [sep, ""]

    # ---- Section 2: Yesterday's open tickets ----
    lines.append(f"  === YESTERDAY ({prev_day.strftime('%B %d, %Y')}) ===")
    lines.append("")
    prev_action, prev_vis = classify(prev_open, today)
    lines += _section("ACTION REQUIRED — Discuss in Call",  prev_action, today, "  !!", "No high-priority or urgent tickets from yesterday.")
    lines += _section("FOR VISIBILITY — No Immediate Action", prev_vis,  today, "  --", "No other open tickets from yesterday.")
    lines += [sep, ""]

    # ---- Section 3: Anchor date unclosed tickets ----
    lines.append(f"  === PENDING FROM {anchor_date.strftime('%B %d, %Y').upper()} (ANCHOR) ===")
    lines.append("")
    anch_action, anch_vis = classify(anchor_open, today)
    lines += _section("ACTION REQUIRED — Discuss in Call",  anch_action, today, "  !!", f"No high-priority tickets still open from {anchor_date.strftime('%b %d')}.")
    lines += _section("FOR VISIBILITY — No Immediate Action", anch_vis,  today, "  --", f"No other tickets still open from {anchor_date.strftime('%b %d')}.")
    lines += [sep, ""]

    # ---- Quick reference table (all open across all three scopes) ----
    all_open = {t["key"]: t for t in today_open + prev_open + anchor_open}.values()
    lines += _table(list(all_open), today)

    lines += [sep, "  Generated by jira_daily_report.py", sep]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_report(report: str, report_date: date, output_dir: str = "reports") -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"report_{report_date.strftime('%Y-%m-%d')}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report)
    return path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily Jira report for Parth Shah")
    parser.add_argument(
        "--date", default=date.today().isoformat(),
        help="Report date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--anchor", default=ANCHOR_DATE.isoformat(),
        help=f"Anchor date to always check for unclosed tickets (default: {ANCHOR_DATE})",
    )
    parser.add_argument("--save",  action="store_true", help="Save report to reports/<date>.txt")
    parser.add_argument("--json",  action="store_true", dest="as_json", help="Output raw JSON")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date)
    prev_day    = report_date - timedelta(days=1)
    anchor_date = date.fromisoformat(args.anchor)

    # Fetch all three scopes in parallel (sequential here for simplicity)
    today_all_raw  = fetch_for_day(report_date, open_only=False)
    today_open_raw = fetch_for_day(report_date, open_only=True)
    prev_all_raw   = fetch_for_day(prev_day,    open_only=False)
    prev_open_raw  = fetch_for_day(prev_day,    open_only=True)
    anchor_open_raw = fetch_for_day(anchor_date, open_only=True)

    if args.as_json:
        print(json.dumps({
            "report_date":  report_date.isoformat(),
            "prev_day":     prev_day.isoformat(),
            "anchor_date":  anchor_date.isoformat(),
            "today_all":    [parse_ticket(i) for i in today_all_raw],
            "today_open":   [parse_ticket(i) for i in today_open_raw],
            "prev_all":     [parse_ticket(i) for i in prev_all_raw],
            "prev_open":    [parse_ticket(i) for i in prev_open_raw],
            "anchor_open":  [parse_ticket(i) for i in anchor_open_raw],
        }, indent=2, default=str))
        return

    report = render_report(
        report_date  = report_date,
        prev_day     = prev_day,
        anchor_date  = anchor_date,
        today_all    = len(today_all_raw),
        prev_all     = len(prev_all_raw),
        today_open   = [parse_ticket(i) for i in today_open_raw],
        prev_open    = [parse_ticket(i) for i in prev_open_raw],
        anchor_open  = [parse_ticket(i) for i in anchor_open_raw],
    )

    print(report)

    if args.save:
        path = save_report(report, report_date)
        print(f"\nReport saved to: {path}")


if __name__ == "__main__":
    main()
