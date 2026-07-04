# Daily Jira Report — 4 July 2026
**Reporter:** Parth Shah (parth@tagmango.com)
**Generated:** Daily standup / team call prep

---

> **Today's new tickets:** None created in the last 24 hours.
> The 3 tickets below are open carry-overs that need team attention.

---

## ACTION REQUIRED — Discuss in Call

### 1. CS-2035 · Freedom Creator | Anisha | Unable to create service & access dashboard
| Field | Detail |
|---|---|
| **Priority** | 🔴 Highest |
| **Status** | Require Details from CS |
| **Due Date** | Not set |
| **Link** | [CS-2035](https://tagmango-cs.atlassian.net/browse/CS-2035) |

**Context:** Creator cannot create a service; dashboard flagged as "unsecured network."
**Last action (Jun 3):** Tech team asked Parth to have creator update CNAME to `wlserver.tagmango.com`.
**Blocker:** No follow-up after the CNAME fix suggestion — status stuck at "Require Details from CS."
**Action needed:** Confirm whether creator updated CNAME. If yes, re-test and close or escalate.

---

### 2. CS-2472 · Freedom Creator | Satyam | Inaccurate data via Webhooks
| Field | Detail |
|---|---|
| **Priority** | 🔴 High |
| **Status** | In Development |
| **Due Date** | ~~14 Jul 2025~~ **OVERDUE** |
| **Link** | [CS-2472](https://tagmango-cs.atlassian.net/browse/CS-2472) |

**Context:** Webhook data transfer works, but volume is wrong — 7 entries on TM dashboard vs. 2 on creator's admin panel.
**Last action (Jul 22, 2025):** Status noted as "To Do" in comments despite being marked "In Development."
**Risk:** Due date has passed by nearly 1 year. Status inconsistency suggests this may have been deprioritised/forgotten.
**Action needed:** Get a dev update on root cause; update due date or close if resolved out-of-band.

---

### 3. CS-2346 · Email Broadcast Issue
| Field | Detail |
|---|---|
| **Priority** | 🔴 High |
| **Status** | Require Details from CS |
| **Due Date** | Not set |
| **Link** | [CS-2346](https://tagmango-cs.atlassian.net/browse/CS-2346) |

**Context:** Creator's email broadcast shows "Delivered" in report but emails not received. Test emails work fine; issue only with TM Network broadcasts.
**Last action (Jul 2, 2025):** Parth shared the dump report link after it was made public.
**Blocker:** No resolution update since July 2025 — stale for ~12 months.
**Action needed:** Check if this was resolved and close, or reassign for investigation.

---

## FOR VISIBILITY — No Immediate Action

_No low/medium priority open tickets at this time. All 3 open tickets are high/highest priority and listed above._

---

## Summary Snapshot

| Ticket | Priority | Due Date | Status | Risk |
|---|---|---|---|---|
| CS-2035 | Highest | — | Require Details from CS | Blocked — pending CNAME follow-up |
| CS-2472 | High | ~~2025-07-14~~ | In Development | Overdue by ~12 months |
| CS-2346 | High | — | Require Details from CS | Stale ~12 months, no resolution |

**Key themes:**
- All 3 tickets are stale (last activity 12+ months ago) — likely need triage to close or re-activate.
- CS-2035 is highest priority with an actionable next step (CNAME confirmation).
- CS-2472 has a hard overdue date and a status mismatch that needs a dev sync.
