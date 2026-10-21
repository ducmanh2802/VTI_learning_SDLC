# WP-16b: AI in Core (quota, userRef, proxy endpoints, admin review proxy, feature flags)

| Field | Value |
|---|---|
| Size | M |
| Audit level | **Deep** (privacy) |
| Branch | `wp-16b-core-ai` |
| Depends on | WP-13b, WP-06 (feature flags, admin auth); runs against WP-16a's contract (mock it in tests) |
| References | SRS FR-060 to FR-062, FR-069 to FR-073, FR-212, NFR-S05, SC-008; SDD SD-05, 3.6.1 (`/ai/*`, `/symbols/{code}/ai-summary`, `/admin/ai/reviews*`); `contracts/openapi/dist/*.yaml` |

## Goal

Core exposes the AI endpoints to users:

- daily question quota with refunds;
- pseudonymous `userRef` (the user id never reaches Analytics);
- feature flags.

Core also proxies the admin review queue.

## In scope

- `services/core/src/main/java/vn/stockai/core/marketgw/ai/**`, `.../admin/**` (review proxy)
- `.../identity/api` (`UserRefs`)
- Tests
- `docs/workpackages/reports/WP-16b.md`

## Out of scope

- Analytics changes.

## Design

### `identity.api.UserRefs.of(UUID userId) -> String`

- `base64url(HMAC-SHA256(users.user_secret, userId as 16 bytes))`.
- Cache it in memory for 10 min.
- Throws if `user_secret` is NULL (deleted user).

### `GET /symbols/{code}/ai-summary`

- Requires the flag `ai_summary` (else 503 `DATA_STALE`, detail "Tóm tắt AI đang tạm tắt").
- Derivative gate as in WP-13b.
- Calls Analytics `POST /ai/summary` with a 20 s read timeout and maps the response. Upstream failure → 503 `DATA_STALE`.
- Never cache FALLBACK; cache PUBLISHED for 10 min (Caffeine).

### `POST /ai/chat {question, contextSymbol?}`

1. Requires the flag `ai_chat`.
2. Validate: `question` 1–500 characters after trim.
3. **Quota (FR-062):**
   - `INCR ai:quota:{userId}:{yyyyMMdd VN}` with a 48 h TTL.
   - If the value > `app.ai.daily-limit` (default 10): `DECR`, then 429 `AI_QUOTA_EXCEEDED` with header `Retry-After` = seconds until 00:00 VN. The problem detail is "Bạn đã dùng hết 10 lượt hôm nay, lượt được làm mới lúc 00:00".
4. Call Analytics `POST /ai/chat {userRef, question, contextSymbol}` with a 25 s timeout.
5. **Refund:** on a timeout, a 5xx, or `refunded = true` → `DECR` the quota.
6. Upsert `core.ai_usage_daily` (+1 when not refunded), after the response is decided.
7. **Never log the question text.**

### Other user endpoints

- **`GET /ai/quota`:** `{limit, used, remaining, resetsAt}`.
- **`POST /ai/interactions/{id}/feedback {rating}` and `/report {reason}`:** forward with `userRef`; the response is 204.

### Admin review proxy

- `GET /admin/ai/reviews?status=&cursor=` and `POST /admin/ai/reviews/{id}/verdict {verdict, note}` → Analytics, with `reviewerId` = the admin's user id.
- `hasRole('ADMIN')`.
- The verdict is audited (`AiReviewVerdict implements AuditableEvent`).

## Tests (WireMock for Analytics; Redis testcontainer)

| Area | Cases |
|---|---|
| `userRef` | Stable for the same user; different across users; contains neither the user id nor the email; a deleted user → exception |
| Quota | 10 questions OK, the 11th → 429 with `Retry-After`; a refunded answer does not consume (11 calls with 1 refund → the 11th OK); upstream timeout → refunded; the counter key has a TTL; rollover at 00:00 VN (fake clock) |
| Flags | `ai_chat` off → 503 without an upstream call; `ai_summary` off → 503 |
| Privacy | Captured logs contain no question text (`ListAppender`); the request sent upstream contains `userRef`, not `userId` |
| Summary caching | PUBLISHED cached; FALLBACK not cached |
| Admin proxy | USER → 403; ADMIN OK; verdict audited |
| Coverage | ≥ 85% for the new code |

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | `cd services/core && ./gradlew build` | BUILD SUCCESSFUL; coverage met |
| 2 | Live with WP-16a merged: ask a question and call `/ai/quota` | `used` increments; an advice question returns REFUSED; paste the statuses |
