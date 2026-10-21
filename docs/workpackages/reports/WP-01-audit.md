# WP-01 audit (Claude)

- **Verdict:** PASS
- **Date:** 2026-10-21
- **Branch:** `wp-01-db-baseline` (2 commits), merged into `integration/r1`
- **Agent:** OpenCode, model `opencode/deepseek-v4.1-flash-free`, 1 run, 0 fix rounds

## Checklist

| # | Item | Result |
|---|---|---|
| A1 | Scope | Pass: 8 files, all in scope |
| A2 | Contracts | n/a |
| A3 | Tests | CI job `db-migrate` encodes acceptance checks 4–8 |
| A4 | CI | Pending: the workflow is valid; it will run on the first push of a `wp-*` / `integration/**` branch |
| A5 | Architecture rules | Pass: one writer per schema is enforced by the roles (checked both ways) |
| A6 | Security | Pass: passwords only from env; initdb mounted read-only; least-privilege login roles |
| A7 | Fail-closed / errors | `ON_ERROR_STOP=1`, `${VAR:?}` guards |
| A8 | Money/time types | n/a |
| A9 | Migrations | Pass: `V1__baseline.sql` is byte-identical to `docs/design/schema.sql`; Flyway naming validation is on |
| A10 | No paid dependency; docs updated | Pass: Flyway Community `11.13.3` pinned; READMEs updated |

## Independent re-run

- Items 1–9, 11 and 12 pass.
- Migrator: first run applies v1, second run says "up to date".
- 48 tables.
- `core_svc`: reads `market.symbols`, cannot write it, and **can** write `core.users`.
- `analytics_svc`: cannot read `core`, and **can** write `market.trading_calendar`.
- `beta_invite_only = t`.
- Redis stops in 0.8 s (F1 fixed).

## WP-00 follow-ups

F1 (`exec`), F2 (gitleaks `--user`) and F3 (push triggers): all fixed.

## Notes

- Role passwords are applied only when the data volume is created (initdb). Rotating them later needs `ALTER ROLE`; this is documented in `infra/README.md`. WP-22 must cover it in the production runbook.
