# WP-07 audit (Claude)

- **Verdict:** PASS after audit fixes (F1–F5, applied by Claude in a separate commit)
- **Date:** 2026-10-21
- **Branch:** `wp-07-analytics-skeleton` (3 agent commits, a merge of `integration/r1` and 1 audit commit), merged into `integration/r1`
- **Agent:** OpenCode, model `opencode/minimax-m3.1-flash-free`, 1 run, 0 fix rounds

## Checklist

| # | Item | Result |
|---|---|---|
| A1 | Scope | Pass: 53 files, all in scope (`services/analytics/**`, compose, `.env.example`, `analytics.yml`, report) |
| A2 | Contracts | Pass after F1/F2: health payloads now match the internal contract; generated models committed |
| A3 | Tests | Pass: 59 tests (58 + 1 audit test), testcontainers for Postgres/Redis, hypothesis for money/time |
| A4 | CI | Pending: `analytics.yml` runs on the push of `integration/r1` |
| A5 | Architecture rules | Pass: 3 import-linter contracts kept; the agent proved `quant-pure` breaks on a forbidden import |
| A6 | Security | Pass: `hmac.compare_digest`; every non-health route sits behind the protected router; the probe route exists only with `ENV=test`; credentials are redacted from probe errors; `SERVICE_TOKEN` < 32 chars refuses to start |
| A7 | Fail-closed / errors | Pass: probes never raise and report DOWN; every error is RFC 9457; no traceback in bodies |
| A8 | Money/time types | Pass after F3/F4: floats refused by the helpers; prices in generated models are `Decimal`; naive datetimes refused |
| A9 | Migrations | n/a (tests apply `db/migrations` in order) |
| A10 | No paid dependency; docs updated | Pass: all dependencies open source; README updated |

## Independent re-run (after the fixes)

| # | Check | Result |
|---|---|---|
| 1 | `ruff check .`, `ruff format --check .` | All checks passed; 42 files formatted |
| 2 | `mypy --strict src` | Success, 31 files (generated models included) |
| 3 | `lint-imports` | 3 kept, 0 broken |
| 4 | `pytest --cov` | 59 passed, total 92.9% (generated file omitted from coverage) |
| 5 | `gen_models.ps1` twice | identical output; 0 `float` fields with `multiple_of` |
| 6–9 | Compose smoke | Accepted from the agent's run (analytics healthy, ready 200, heartbeat, `down -v`); the code change since then is limited to the ready payload, which the tests cover |

## Findings (fixed by Claude)

| # | Severity | Finding | Fix |
|---|---|---|---|
| F1 | Major | `/health/ready` returned `components.postgres: {status, detail}`, while the internal contract (`Health`) has `components: {db: UP\|DOWN, redis: UP\|DOWN}` | Payload aligned with the contract; probe name `db`; tests updated |
| F2 | Minor | The contract required `components` on `/health/live`, but the brief (and the code) return `{status}` only | Contract fix: new `internal/schemas/HealthLive.yaml` |
| F3 | Major | Acceptance 5 was deferred because WP-02 was not merged yet. Once generated, the models had (a) `float` for every price, because `--use-decimal-for-multiple-of` is ignored together with `--use-annotated` (datamodel-codegen 0.86), and (b) lowercase enum members (`index`, `count`) that clash with `str` methods and fail `mypy --strict` | Contract fix: `format: decimal` on all 35 price fields of both specs; generator flag `--capitalise-enum-members`; models generated and committed; coverage omits the generated file |
| F4 | Minor | `to_trading_tz()` accepted naive datetimes and read them in the host timezone (UTC in a container, UTC+7 on the dev machine) | Raises `ValueError`; test added |
| F5 | Minor | `Problem.type` is the relative reference `/errors/<code>`, but the contract said `format: uri` (absolute only). RFC 9457 allows a relative reference | Contract: `format: uri-reference` in both specs; examples use `/errors/risk-lot-size`. CI now calls `scripts/gen_models.sh` instead of a copied command |

## Answers to the agent's questions

- `Problem.type`: relative `/errors/<kebab-code>` is the product convention (F5). Core (WP-03) uses the same form.
- 503 code: `DATA_STALE` is correct for "a dependency does not answer".
- `errors[]` naming the failing component in the 503 problem: accepted.
- `ENV` variable name: accepted; compose feeds it from `APP_ENV`.
- Service-token rotation: out of R1 scope; WP-22 `rotate-secrets.md` covers the procedure (restart both services with the new value).
- SQLAlchemy stays: WP-08/WP-10 repositories use it.

## Notes for later WPs

- **Pydantic serializes `Decimal` as a JSON string.** Every Analytics endpoint that returns prices (WP-13a) must write them as JSON numbers, with a test that checks the raw JSON.
- The hand-written health models in `api/schemas.py` are kept; new endpoints use `models_generated.py`.
