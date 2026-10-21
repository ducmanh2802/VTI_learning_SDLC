# WP-13a: Analytics internal market API

| Field | Value |
|---|---|
| Size | M |
| Audit level | Standard |
| Branch | `wp-13a-analytics-market-api` |
| Depends on | WP-10, WP-11, WP-12 (WP-12 is only needed for overview/treemap; the other endpoints can be done first) |
| References | SDD 3.6.2, 3.5.3, ALG-04, ALG-05; SRS FR-020 to FR-030, FR-040 to FR-054, FR-213; `contracts/openapi/dist/internal.yaml` |

## Goal

Implement every market and ops endpoint of the internal contract. Data comes from `market.*`, Redis (`q:*`, `ob:*`, `idx:*`, `ov:*`, `mkt:session`) and the WP-11 functions. Each endpoint:

- validates against the contract;
- carries provenance;
- is **fail-closed**: it never returns placeholder numbers.

## In scope

- `services/analytics/src/analytics/api/routes/{symbols,market,ops}.py` (and helpers)
- `src/analytics/marketdata/queries.py`
- Tests
- `docs/workpackages/reports/WP-13a.md`

## Out of scope

- AI endpoints (WP-16).
- Any change to contracts. If a needed field is missing, report it; do not edit `contracts/`.

## Endpoint rules

| Endpoint | Rule |
|---|---|
| `GET /symbols?q=` | Normalize `q` (lowercase, no diacritics, `đ→d`). Exact code match first, then code prefix, then `name_search ILIKE %q%` (trigram index). Active symbols only, ≤ 20 results |
| `GET /symbols/{code}` | 404 if the code is unknown |
| `GET /symbols/{code}/quote` | From `q:{CODE}`. See the provenance rules below |
| `GET /symbols/{code}/orderbook` | From `ob:{CODE}`, or else the bid/ask levels of `q:{CODE}`. Same staleness rules |
| `GET /symbols/{code}/bars?interval=D\|W\|M&from&to` | D from `market.daily_bars`. W/M are aggregated: open = first, close = last, high = max, low = min, volume = sum, value = sum (or null if any is null); ISO weeks and calendar months, in VN time. Max range 5 years; default 1 year |
| `GET /symbols/{code}/indicators?from&to` | Load 260 bars of warm-up before `from`, compute with `compute_series`, return only `[from, to]`. Add `describe()` for the last bar and `rulesVersion` |
| `GET /symbols/{code}/fundamentals` | If `market.ratios` has rows, return the latest. Otherwise, if the source tier lacks `FINANCIALS`, return the contract's "unavailable" form; if the contract has none, return 503 `DATA_STALE` with detail "Nguồn dữ liệu hiện tại chưa cung cấp chỉ số tài chính" and **report the contract gap** |
| `GET /market/overview` | From `ov:latest`. Missing → 503 `DATA_STALE` |
| `GET /market/treemap?weight&dir` | From `ov:treemap:{weight}:{dir}`. A weight not available on the tier → the contract's unavailable form, or else 503 `DATA_STALE` plus a report |
| `GET /market/state` | From `mkt:session`. If `updated_at` is older than 60 s → 503 |
| `GET /ops/ingestion` | Latest run per job from `market.ingestion_runs`; quarantine counts (last 24 h); provider health snapshot (WP-09) |

**Provenance for quotes and order books:**

| Condition | `provenance.kind` | `stale` |
|---|---|---|
| Session is ATO, CONTINUOUS or ATC, and `ts` ≤ 120 s old | `DELAYED` | false |
| Session is ATO, CONTINUOUS or ATC, and `ts` is older | `DELAYED` | true |
| Outside those sessions | `CLOSE` | false |

- A missing key → 503 `DATA_STALE`.
- Prices: `Decimal` → JSON number, exactly 2 decimals. Volumes: integers.

Every route:

- requires the service token (WP-07 dependency);
- returns RFC 9457 errors;
- validates the response against the generated pydantic models where available (WP-07 `models_generated.py`).

## Tests (Postgres + Redis testcontainers, seeded with fixtures)

- **Search:** "vinamilk", "VNM", "vin", "sua" (diacritics-free match on a seeded name), an empty `q` → 400.
- **Quote:** fresh in session; stale in session; outside session; missing → 503.
- **Bars:** D, W and M aggregation checked against hand-computed values; `from > to` → 400; range > 5 years → 400.
- **Indicators:** the warm-up makes SMA200 non-null at `from` when enough history exists; the output range is exact.
- **Fundamentals:** unavailable behaviour.
- **Overview and treemap:** present / missing; unavailable weight.
- **Market state:** stale → 503.
- **Ops:** latest runs and health shape.
- **Auth:** no token → 401 on every route (parametrized).
- **Coverage:** new code ≥ 80%.

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | lint, format, mypy, import-linter | pass |
| 2 | `uv run pytest --cov=analytics.api --cov=analytics.marketdata --cov-report=term` | pass, ≥ 80% |
| 3 | Live: run ingestion `symbols_sync`, `quotes_cycle` (`--force`) and `backfill` for FPT, then `curl -H "X-Service-Token: ..." http://127.0.0.1:8090/internal/v1/symbols/FPT/quote` and `.../bars?interval=W` | Valid JSON per the contract; paste excerpts |
