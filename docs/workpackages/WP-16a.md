# WP-16a: AI pipeline in Analytics (fact packs, summary, chat, logging, reviews, sampling)

| Field | Value |
|---|---|
| Size | L |
| Audit level | **Deep** (AI safety) |
| Branch | `wp-16a-ai-pipeline` |
| Depends on | WP-11, WP-13a, WP-14, WP-15 |
| References | SRS FR-060 to FR-074, NFR-P02, NFR-P03, NFR-AI01 to NFR-AI04, BRU-001; SDD ALG-07, ST-05, SD-04, SD-05, 3.6.3 (prompt templates); schema `ai.*`; PRD US-027 to US-033 |

## Goal

Implement "facts in, words out" end to end inside Analytics:

1. Build fact packs.
2. Generate symbol summaries (cached once per symbol and trading day) and chat answers through the LLM gateway (WP-14).
3. Verify them with the guardrails (WP-15).
4. Regenerate once, then fall back to the facts.
5. Log every attempt.
6. Run the review queue and the weekly sampling.

## In scope

- `services/analytics/src/analytics/ai/{facts.py, pipeline.py, templates.py, reviews.py}`
- `.../api/routes/ai.py`
- `.../ingestion/jobs/ai_sampling.py`
- `db/migrations/V2__ai_prompt_templates.sql` (seeds `summary` v1 and `chat` v1)
- Tests
- `docs/workpackages/reports/WP-16a.md`

## Out of scope

- Core quota and proxy (WP-16b).
- Changes to the guardrail patterns: report needed changes; do not edit WP-15 files except to fix a bug, with a test.

## Design

### Fact pack (`facts.py`)

`build_symbol_facts(code) -> FactPack`. `trade_date` = the latest date in `market.daily_bars` for the symbol.

Facts are numbered `F1…Fn` in this order (skip any that are missing; **never** invent):

1. close
2. change vs the previous close (VND)
3. % change
4. volume
5. SMA20, SMA50, SMA200
6. RSI14
7. MACD, signal, histogram
8. Bollinger upper and lower
9. ATR14
10. fundamentals P/E, P/B, ROE (if available)

**Each fact:**

- `id`, `label` in Vietnamese (for example "Giá đóng cửa", "RSI(14)").
- `value` (`Decimal`) and `unit` (`VND`, `%`, `""`).
- `display`: vi-VN format, for example `57.400` or `72,40`.
- `source`: provider or `"Tính toán"`; `as_of` (UTC).

**Descriptions:** `describe()` from WP-11, each mapped to the fact ids of its inputs.

**Hash:** `facts_hash` = SHA-256 of canonical JSON (sorted keys, no whitespace, values as strings).

`build_market_facts()` builds the same kind of pack from `ov:latest`: indices and breadth.

### Templates

- `V2__ai_prompt_templates.sql` inserts `summary` v1 and `chat` v1 into `ai.prompt_templates`. The body is exactly SDD 3.6.3 (the system part and the user part).
- The code loads the latest version by name. The template id is stored on every interaction.

### Summary: `POST /ai/summary {symbol}` (FR-060, SD-04)

1. If `ai.summaries` has a row for `(symbol, trade_date, facts_hash)` that is not hidden → return it (status PUBLISHED, with citations).
2. Otherwise take a Redis lock `lock:ai:summary:{symbol}:{trade_date}` (TTL 60 s). Concurrent callers wait up to 15 s for the result, or else get FALLBACK.
3. **Generate (ALG-07):**
   - Messages = the template plus facts and descriptions.
   - Call the gateway. `None` → FALLBACK.
   - Check with `guardrails.run_all(text, facts)`.
   - If it fails, retry **once** with an extra user message listing the failure reasons (no facts removed).
   - A second failure → FALLBACK.
4. **Store:** every attempt writes an `ai.interactions` row: kind SUMMARY, facts, `facts_hash`, `template_id`, provider/model, output, the guard results, `final_status`, latency, tokens. PUBLISHED also inserts `ai.summaries`.
5. **Response** (per contract):
   - `{interactionId, status, text, citations, facts, labels: {aiGenerated: true, notAdvice: true}}`.
   - `citations` = the facts cited in the text, in order of first appearance.
   - FALLBACK has `text = null` and carries `facts`.

### Chat: `POST /ai/chat {userRef, question, contextSymbol?}` (FR-061 to FR-068, SD-05)

1. `pii.scrub(question)`. **Only the scrubbed text** is used and stored afterwards.
2. `intent.classify(scrubbed, known_symbols)`; `known_symbols` comes from `market.symbols`, cached 1 h.
   - **ADVICE or OUT_OF_SCOPE** → REFUSED, using the standard text (FR-068): "Nền tảng không cung cấp khuyến nghị đầu tư...". The text suggests data the user can view (for a symbol: its analysis page; otherwise the market overview). `refunded = false`.
   - **No symbol, but a market keyword** → market facts.
   - **No symbol and no keyword**, but it looks like a symbol question → REFUSED, asking "Bạn muốn hỏi về mã nào?", with `refunded = true` (UC-007 4b).
3. Build facts (symbol or market). Generate with `chat` v1 plus the scrubbed question. Use the same guard, retry and fallback logic as the summary.
4. `refunded = true` when the gateway returned `None` (system failure), otherwise false.
5. Log `ai.interactions` with kind CHAT, `user_ref`, `question_redacted`, intent.

### Feedback, reports and reviews (FR-073, FR-074, FR-212)

| Endpoint | Behaviour |
|---|---|
| `POST /ai/interactions/{id}/feedback {userRef, rating}` | Upsert into `ai.feedback` |
| `POST /ai/interactions/{id}/report {userRef, reason}` | Insert into `ai.reviews` with source `USER_REPORT` |
| `GET /ai/reviews?status=&cursor=` | Interaction text, facts and guard results. **No** `user_ref` |
| `POST /ai/reviews/{id}/verdict {verdict, note, reviewerId}` | Store the verdict. `VIOLATION` → `ai.summaries.hidden = true` for that interaction |

**Sampling job:** Mondays 06:00 VN time. Insert up to 50 random PUBLISHED interactions from the last 7 days, not already reviewed, with source `SAMPLE`.

### Performance

- Summary from cache: p95 ≤ 800 ms (DB lookup only).
- LLM timeout 15 s per attempt; the whole request is capped at 40 s.

## Tests (fake LLM provider injected into the gateway; Postgres + Redis testcontainers)

| Area | Cases |
|---|---|
| Fact pack | Numbering, missing facts skipped, vi-VN display, stable hash |
| Summary: good path | Fake LLM returns cited, correct text → PUBLISHED, cached; a second call is served from cache (no LLM call) |
| Summary: advice | Text with "nên mua" → regenerated → second attempt OK → PUBLISHED; 2 interaction rows |
| Summary: failures | Wrong number twice → FALLBACK with facts; gateway `None` → FALLBACK |
| Summary: hidden | A hidden summary is not served → regenerate |
| Summary: concurrency | Two concurrent requests → exactly one LLM call |
| Chat: advice and scope | "có nên mua FPT không" → REFUSED, `refunded=false`, no LLM call; out-of-scope → REFUSED |
| Chat: privacy | A question with an email → the fake provider receives `[EMAIL]` and `question_redacted` stores it scrubbed |
| Chat: failure | Gateway failure → `refunded=true` |
| Reviews | Report creates a review; verdict VIOLATION hides the summary; the review list contains no `user_ref` |
| Sampling | ≤ 50 entries, none duplicated |
| Coverage | `analytics.ai` (excluding llm and guardrails, tested elsewhere) ≥ 85% |

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | lint, format, mypy, import-linter | pass |
| 2 | `uv run pytest tests/ai --cov=analytics.ai --cov-report=term` | pass; thresholds met |
| 3 | `DC run --rm migrator` | applies V2; re-run says up to date |
| 4 | Live (needs at least one LLM key in `infra/.env`; otherwise run with the fake provider and say so): summary for FPT | PUBLISHED or FALLBACK, logged; paste the response without secrets |
