# AGENTS.md: rules for coding agents

You are implementing **VN Stock AI Pro**, a Vietnamese stock-analysis **tool** (web + mobile + backend).
Work is delivered as small **work packages (WP)**. Claude writes each WP brief and audits your result; the founder merges.
Read this file fully before every WP. If a WP brief conflicts with this file, stop and ask in your report.

## 1. Sources of truth (read the parts your WP references)

| File | What it defines |
|---|---|
| `docs/requirements/SRS.md` | Requirements: FR-xxx, NFR-xxx, UC-xxx, constraints SC-xxx |
| `docs/design/Blueprint_SDD.md` | Architecture, modules, APIs, algorithms (ALG-xx), WP list (section 7) |
| `docs/design/schema.sql` | Database schema (becomes `db/migrations/V1__baseline.sql`) |
| `docs/workpackages/WP-xx.md` | Your current task: scope, steps, acceptance commands |
| `contracts/` | OpenAPI and Redis/event contracts (from WP-02 on) |

Documents are in Vietnamese. Code, identifiers, comments and commit messages are in English. **Text shown to end users is in Vietnamese.**

## 2. Golden rules

1. Change only files inside the WP scope. Never edit `docs/requirements/`, `docs/design/` or existing migrations unless the WP says so.
2. Every behaviour change ships with tests. Run the WP acceptance commands before you report "done".
3. No paid services, paid APIs or non-free dependencies (SC-005). Free/open-source only.
4. Never commit secrets. Only `*.example` env files with placeholder values are committed.
5. Money and prices never use floating point in domain logic. Java: `long` (VND) or `BigDecimal`. Python: `int` or `Decimal`. In the API, VND amounts are JSON integers and prices are JSON numbers with at most 2 decimals. The TS clients only display these values and never compute money with them.
6. **Fail-closed:** when data is missing, stale or invalid, return an explicit "unavailable/stale" state. Never substitute 0, a fake value or an unlabeled old value (FR-030).
7. The product **never gives investment advice**. No UI text, AI prompt or code path may recommend buying/selling/holding a symbol, state a target price, or promise profit (BRU-001). Forbidden wording in UI copy includes: "nên mua", "nên bán", "khuyến nghị", "điểm mua", "cơ hội mua", "chắc chắn tăng".
8. **No real broker orders.** Do not implement any code that sends orders to a securities company before release R4 (SC-007).
9. No personal data (email, name, phone, ID numbers) leaves the system, except email/push sent to that same user. Never send personal data to an LLM (FR-070).
10. If something is unclear or missing, do not invent requirements. Make the smallest safe choice, and list it under "Questions" in your report.

## 3. Repository layout

```text
AGENTS.md                 this file
apps/web                  React 18 + Vite + TypeScript + Tailwind (WP-20a+)
apps/mobile               Expo / React Native + TypeScript (WP-21)
services/core             Java 21 + Spring Boot 4, Gradle Kotlin DSL (WP-03+)
services/analytics        Python 3.12 + FastAPI, managed with uv (WP-07+)
contracts/openapi         public.yaml, internal.yaml (WP-02)
contracts/events          redis-keys.md, s-quotes.schema.json (WP-02)
db/migrations             Flyway SQL migrations V<n>__<name>.sql (WP-01+)
infra                     docker-compose.yml, Caddyfile, scripts, runbooks
docs/requirements         BRD.md, SRS.md
docs/design               Blueprint_SDD.md, schema.sql
docs/workpackages         WP briefs; reports/ holds your WP reports
.github/workflows         CI
```

## 4. Commands

Commands become available as WPs land. Use the ones that exist. Never mark a step as passed without running it.

| Area | Command (run from repo root unless noted) | Available after |
|---|---|---|
| Dev infra up | `docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --wait` | WP-00 |
| Dev infra down | `docker compose -f infra/docker-compose.yml --env-file infra/.env down` | WP-00 |
| Migrations | `docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm migrator` | WP-01 |
| Core build + tests | `cd services/core && ./gradlew build` (Windows: `gradlew.bat build`) | WP-03 |
| Analytics tests | `cd services/analytics && uv run pytest` | WP-07 |
| Analytics lint/types/layers | `uv run ruff check . && uv run mypy . && uv run lint-imports` | WP-07 |
| Web | `cd apps/web && pnpm install && pnpm lint && pnpm test && pnpm build` | WP-20a |
| Mobile | `cd apps/mobile && pnpm install && pnpm lint && pnpm test` | WP-21 |

Local env: copy `infra/.env.example` to `infra/.env` (git-ignored) and change the passwords.

## 5. Workflow for each WP

1. Start from up-to-date `main`. Create the branch `wp-<nn>-<short-slug>`, for example `wp-00-repo-skeleton`.
2. Do the steps in the WP brief, in order. Keep commits small. Use Conventional Commits with the WP id:
   `feat(core-identity): add refresh token rotation [WP-04]`, `chore(infra): add dev compose [WP-00]`.
3. Run every acceptance command in the brief. Fix failures. Do not weaken, skip or delete tests or lint rules to make them pass.
4. Write the report to `docs/workpackages/reports/WP-<nn>.md` using the template in section 11. Commit it on the same branch.
5. Push the branch and open a pull request titled `WP-<nn>: <title>`. Never push to `main`. Never force-push. Never use `--no-verify`.

## 6. Architecture rules

- **Core (Java)** is a modular monolith (Spring Modulith). The modules are: `identity`, `consent`, `marketgw`, `quotes`, `watchlist`, `alerting`, `notification`, `paper`, `admin`, `audit`, `support`, `shared`.
  - Modules talk only through their `..api` package or Spring application events.
  - Allowed dependencies are listed in SDD 3.4.1. `ApplicationModules.verify()` must pass.
- **Analytics (Python)** has this layer order: `api` → `ingestion | ai | research` → `quant | fundamentals` → `marketdata | providers` → `common`.
  - `quant` and `ai.guardrails` are pure: no network, no DB, no Redis.
  - Rules are enforced by import-linter (SDD 3.4.2).
- **Single writer per DB schema:** Core writes `core`, `paper`, `strategy`. Analytics writes `market`, `ai`, `research`. Never write another service's schema.
- Only Core is reachable from the Internet. Analytics listens on the internal Docker network and requires `X-Service-Token`.
- External providers (market data, LLM, email, push) are used only through their port/adapter interfaces (SC-010). Domain code never imports a vendor SDK directly.
- APIs follow the OpenAPI contracts in `contracts/openapi`. Errors use RFC 9457 `application/problem+json` with a stable `code` (list: SDD 3.6.1).
- Schema changes go in a **new** Flyway migration `db/migrations/V<n>__<name>.sql`. Never edit an applied migration.

## 7. Domain rules

- **Time:** trading logic uses `Asia/Ho_Chi_Minh`; store `timestamptz`. Inject a `Clock` (Java) or a time provider (Python). Never call `now()` directly in domain code.
- **Market session** comes from Analytics (`mkt:session` in Redis). Core reads it and never recomputes it. Session times live in config, not in code.
- **Provenance:** every market value carries `source` and `asOf`. The UI shows the provenance label (FR-029).
- **RiskGuard (paper trading):** rules run in the order given in SDD ALG-10 and stop at the first violation, which returns its `RISK_*` code. Lot size, price band, tick size, T+2 availability, no short selling, user limits, halt.
- **Ledger:** `paper.ledger_entries` is append-only. Post entries and update `paper.positions` in the same DB transaction (ALG-12).
- **AI = "facts in, words out":** the LLM only rephrases a fact pack computed by our code.
  - Every number in the AI output cites `[F<n>]`.
  - Output must pass the number, recommendation and profit guardrails. Otherwise regenerate once, then fall back to the facts table (ALG-07).
  - Log every generation to `ai.interactions`.
- **Rate limits:** each market-data provider is called at most 1 request/second by default, with request coalescing (FR-033).

## 8. Coding conventions

- **Java:** Java 21, Spring Boot 4 (Spring Framework 7, Jakarta EE 11, Jackson 3), records for DTOs, constructor injection, no Lombok. Bean Validation on inputs. JUnit 5 + AssertJ + Testcontainers (Postgres, Redis) for integration tests.
- **Python:** 3.12, type hints everywhere (`mypy --strict` on new modules), Pydantic v2 models, `async` I/O with `httpx`/`asyncpg`. `ruff` for lint and format. `pytest` + `hypothesis` for pure functions.
- **TypeScript:** `strict: true`, no `any`. TanStack Query for server state. `zod` validation at API boundaries. Format numbers and dates with `Intl` in the `vi-VN` locale.
- Keep functions small. Comment only where the code cannot say it. No dead code, no commented-out code, no TODO without a WP id.

## 9. Testing and quality gates

- Coverage: ≥ 80% for domain logic (RiskGuard, ledger, indicators, AI guardrails, auth); ≥ 60% overall (NFR-M01).
- For every use case you touch, test the main flow, alternate flows and exception flows (SRS section 4).
- Indicators and other numeric algorithms use golden-data tests with known expected values.
- Integration tests use real Postgres/Redis through Testcontainers or the dev compose. Never mock the database when testing SQL.
- CI must be green before you report done.

## 10. Security

- Validate every input. Check authorization on every endpoint (a user may only read or modify their own data).
- Passwords: Argon2id. Tokens are stored hashed. Refresh tokens rotate; reuse revokes the whole family.
- Logs are JSON and include `correlationId`. Never log passwords, tokens, OTPs, full emails or AI questions linked to a user id.
- Dev ports bind to `127.0.0.1` only.

## 11. Report template (`docs/workpackages/reports/WP-<nn>.md`)

```markdown
# WP-<nn> report
- Branch / PR: <branch> / <PR url>
- Model used: <agent + model name>
## Done
- <what was implemented, mapped to the WP steps>
## Files changed
- <path>: <one-line purpose>
## Acceptance commands
| Command | Result (pass/fail + key output) |
## Deviations from the brief
- <none, or what and why>
## Questions / open issues
- <anything unclear; assumptions you made>
```
