# WP-13b: Core `quotes` and `marketgw` (Redis reader, `s:quotes` consumer, BFF to Analytics, caching, derivative gate)

| Field | Value |
|---|---|
| Size | M |
| Audit level | Standard |
| Branch | `wp-13b-core-market-gateway` |
| Depends on | WP-03 (and WP-05 for `DerivativeRiskGate`; if WP-05 is not merged yet, put a temporary interface in `consent.api` that always returns false, and report it) |
| References | SRS FR-015, FR-021 to FR-023, FR-030, FR-040 to FR-054, FR-181, NFR-P01, NFR-P04, NFR-A03; SDD 3.4.1 (`marketgw → consent.api`), 3.5.3, 3.6.1 (market rows), SD-03, 3.11 (circuit breaker); `contracts/openapi/dist/public.yaml`, `dist/internal.yaml`, `contracts/events/*` |

## Goal

1. **`quotes` module:**
   - reads quotes and session state from Redis, with staleness computed;
   - consumes the `s:quotes` stream with a consumer group;
   - publishes `quotes.api.QuotesUpdated(symbols, cycleTs)` as a Spring application event for alerting (WP-18) and paper trading (WP-19).
2. **`marketgw` module:**
   - serves every public **market** endpoint by calling the Analytics internal API;
   - uses short caches, a circuit breaker and fail-closed errors;
   - applies the derivative-risk gate to futures symbols.

## In scope

- `services/core/src/main/java/vn/stockai/core/quotes/**`, `.../marketgw/**`
- `package-info`: `marketgw` already allows `consent::api` (WP-03); add it if missing
- Tests
- `docs/workpackages/reports/WP-13b.md`

## Out of scope

- AI endpoints (WP-16).
- Watchlists and alerts (WP-17, WP-18).

## Design

### `quotes.api`

**`QuoteReader`:**

- `Optional<Quote> latest(String symbol)` and `Map<String, Quote> latest(Collection<String>)`, using pipelined `HGETALL q:{SYMBOL}`.
- `SessionState session(Exchange)` reads `mkt:session`.
- `Quote` record fields follow `contracts/events/redis-keys.md`. Prices are `BigDecimal` scale 2, volumes `long`.
- `stale` = true when the session is ATO, CONTINUOUS or ATC and `now − ts > 120 s` (injected `Clock`).
- A quote that cannot be parsed → empty, and a WARN log.

**Stream consumer:**

- At startup: `XGROUP CREATE s:quotes core $ MKSTREAM`; ignore `BUSYGROUP`.
- A virtual thread loop runs `XREADGROUP GROUP core core-1 COUNT 10 BLOCK 5000 STREAMS s:quotes >`.
- For each entry: parse it per `s-quotes.schema.json`, publish `QuotesUpdated` **synchronously**, then `XACK`.
- At startup, also claim and process pending entries older than 30 s (`XAUTOCLAIM`).
- A listener exception is logged with the entry id and **still acked**. A poison message must not block the stream.
- Graceful shutdown.

### `marketgw`

**`AnalyticsClient`** (Spring `RestClient`):

- Base URL `ANALYTICS_BASE_URL` (compose: `http://analytics:8090/internal/v1`).
- Header `X-Service-Token` from `SERVICE_TOKEN`; propagate `X-Correlation-Id` from MDC.
- Timeouts: connect 2 s; read 5 s.
- Resilience4j circuit breaker `analytics`: 50% failure rate over 20 calls; open for 30 s.

**Public endpoints** (`dist/public.yaml`, tag `market`):

- `/symbols?q=`, `/symbols/{code}`, `.../quote`, `.../orderbook`, `.../bars`, `.../indicators`, `.../fundamentals`
- `/market/overview`, `/market/treemap`, `/market/state`

Map the Analytics DTOs to the public DTOs (same shapes unless the contract differs).

**Caching** (Caffeine, per key):

| Data | TTL |
|---|---|
| quote, orderbook | 5 s |
| overview, treemap, state | 5 s |
| bars, indicators | 60 s |
| symbol, search | 1 h |
| fundamentals | 6 h |

- Never cache errors.

**Fail-closed:**

- Analytics unreachable, timing out or with the breaker open → 503 `DATA_STALE`, detail "Dịch vụ dữ liệu tạm thời không khả dụng".
- An Analytics 503 is passed through as 503 `DATA_STALE`.
- An Analytics 404 → 404.

**Derivative gate (FR-015):** for symbols whose Analytics `kind` is `FUTURE`, require `consent.api.DerivativeRiskGate.isAcknowledged(userId)`, otherwise 403 `DERIVATIVE_RISK_NOT_ACKED`. Apply it to every per-symbol endpoint.

**Plan entitlement (FR-181):** in R1 every authenticated user is `FREE` and allowed. Implement the `Entitlements.check(plan, feature)` hook with an allow-all policy for `FREE`, and a unit test.

## Tests

| Area | Cases |
|---|---|
| `QuoteReader` (Redis testcontainer) | Parse; stale in session; not stale outside session; malformed → empty |
| Stream consumer | `XADD` an entry → a `QuotesUpdated` listener receives it with the right symbols → the entry is acked; a listener that throws → the entry is still acked and logged; pending entries are claimed at startup |
| `marketgw` (WireMock or `MockRestServiceServer` for Analytics) | Happy path for each endpoint (DTO mapping); cache hit (only one upstream call within the TTL); upstream timeout → 503 `DATA_STALE`; breaker open → 503 without an upstream call; 404 passthrough |
| Derivative gate | FUTURE symbol without acknowledgement → 403 `DERIVATIVE_RISK_NOT_ACKED`; with it → 200; STOCK → no check |
| Auth | Unauthenticated → 401 (from WP-03); terms gate still applied (WP-05) when present |
| Guards | `ContractPathsTest` and `ModularityTests` pass |
| Coverage | `quotes` and `marketgw` ≥ 80% |

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | `cd services/core && ./gradlew build` | BUILD SUCCESSFUL; coverage met |
| 2 | Live (when WP-13a is merged): compose `app` profile with core, analytics and the scheduler running a quote cycle → `GET /api/v1/symbols/FPT/quote` with a user token | 200 with provenance; paste it |
