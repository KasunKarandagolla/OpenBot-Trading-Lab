---
name: trading-lab-news-macro-operations
description: Source-grounded crypto news, official economic-calendar and exchange-incident intelligence for OpenBot Trading Lab. Use to classify event risk, verify incidents, enforce freshness, and report market context without turning headlines into trade authority.
---

# News, macro and operations intelligence

Outcome: a dated, sourced context block that can raise caution or explain a no-trade, and never silently converts an unverified report into fact.

## Approved source classes

| Class | Sources | Use |
|---|---|---|
| Official macro calendar | Federal Reserve, BLS, BEA official releases/calendars | Scheduled event time and actual/consensus where published |
| Venue notices | Gate announcements, maintenance/status pages, instrument/delisting notices | Trading halts, symbol changes, funding anomalies |
| Publisher RSS | The five publisher feeds selected in the completed news evaluation | General market context, with publication time and link |
| Internal | Trading Lab exports, runbook events, reconciliation records | Operational state |

Do not integrate World Monitor or a second aggregation platform. Do not scrape an arbitrary news site because it appeared in a search result.

## Feed registry

Every source used in a report must appear in a registry row:

```json
{
  "source_id": "string",
  "class": "OFFICIAL_CALENDAR | VENUE_NOTICE | PUBLISHER_RSS | INTERNAL",
  "url": "https://...",
  "fetched_at_utc": "ISO-8601Z",
  "http_status": 200,
  "published_at_utc": "ISO-8601Z or null",
  "updated_at_utc": "ISO-8601Z or null",
  "content_sha256": "hex",
  "verified": true
}
```

A source without a fetch time and hash is not citable. A feed that fails to fetch is `UNAVAILABLE`; it is not "no news".

## Freshness rules

- Store `published_at_utc`, `updated_at_utc`, `fetched_at_utc` separately. Do not substitute one for another.
- A headline older than the strategy's news window is context, not a catalyst.
- A calendar event is `SCHEDULED` until an official release exists; then it is `RELEASED` with the official actual value.
- Consensus/forecast numbers must be labelled as such and attributed. Never present a forecast as an outcome.
- If the publication time is missing, the item is `TIME_UNKNOWN` and cannot be used for event timing.

## Incident verification ladder

| Status | Requirement | Permitted wording |
|---|---|---|
| `VERIFIED` | Primary venue/official notice, or two independent reputable sources with matching facts and times | "Gate reported X at T" |
| `REPORTED` | One reputable source, no primary confirmation | "One report claims X; unconfirmed" |
| `UNVERIFIED` | Social post, screenshot, single anonymous claim | "Unverified claim; not used for a decision" |
| `DISPUTED` | Sources conflict | State both and the conflict |
| `RETRACTED` | Source withdrew | Record the retraction; do not reuse the original |

Rules:

- An unverified incident must never be silently promoted to `VERIFIED`.
- Do not turn "exchange wallet moved" into "insolvency", or "withdrawals delayed" into "halt", without the primary notice.
- A venue maintenance notice is operational context. It is not proof that stops will fail.
- Preserve the original link and hash; do not paraphrase a quote into a fact.

## Event-risk policy

1. Classify each event: `SCHEDULED`, `IMMINENT` (inside the proposed holding window), `RELEASED`, `PASSED`.
2. If an event lands inside the holding window and the strategy has no event rule, mark `CAUTION`; the Risk Reviewer may still pass a small, well-hedged-by-stop trade.
3. A hard `NO_TRADE` requires a written policy rule with an event class, a time buffer and a version. Do not invent one per trade.
4. Do not claim that an event veto already operates inside OpenBot Trading Lab. The prior event-clearance test used AstraBot-compatible fixtures; it is not an installed Trading Lab control.
5. An unverified incident does not create a veto. It creates an `UNKNOWN`/`CAUTION` note and a request for primary confirmation.
6. After a release, record the official actual value and the source timestamp. Do not trade the headline; the deterministic strategy decides.

## Operational context

Report only what the exported evidence supports:

- Last successful snapshot and its age.
- Stale symbols and the reason.
- Pending/unfilled orders and unresolved reconciliation.
- Engine/container state if a read-only status export exists.
- Disk/backup warnings if exported.
- Known outages and their start/end times.

Never claim 24/7 uptime. The design explicitly warns that a sleeping laptop stops paper monitoring.

## Director-facing output

```json
{
  "as_of_utc": "ISO-8601Z",
  "market_context": [{"summary": "string", "source_id": "string", "published_at_utc": "ISO-8601Z", "status": "VERIFIED | REPORTED | UNVERIFIED"}],
  "scheduled_events": [{"name": "string", "when_utc": "ISO-8601Z", "class": "MACRO | VENUE | OTHER", "status": "SCHEDULED | RELEASED", "source_id": "string"}],
  "incidents": [{"summary": "string", "status": "VERIFIED | REPORTED | UNVERIFIED | DISPUTED | RETRACTED", "source_ids": []}],
  "operational": {"last_snapshot_utc": null, "stale_symbols": [], "unresolved": []},
  "event_risk": "NONE | CAUTION | NO_TRADE_POLICY",
  "unknowns": [],
  "execution_authority": "NONE"
}
```

Keep it short. The owner needs to know what changed, what is scheduled and what is uncertain — not a news digest.

## Verification

- [ ] Every item has a registry row with fetch time and hash.
- [ ] Publication and fetch times are distinct.
- [ ] Incident status matches the evidence ladder.
- [ ] No forecast presented as actual.
- [ ] No World Monitor or unapproved aggregator.
- [ ] No claim that event vetoes are installed in Trading Lab.
- [ ] Unverified items remain visibly unverified.
