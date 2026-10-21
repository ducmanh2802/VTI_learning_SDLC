# WP-00 audit (Claude)

- **Verdict:** PASS
- **Date:** 2026-10-21
- **Branch:** `wp-00-repo-skeleton` (5 commits, `dc79d28..382256a`), merged into `integration/r1`
- **Agent:** OpenCode, model `opencode/deepseek-v4.1-flash-free`, 1 run, 0 fix rounds

## Checklist

| # | Item | Result |
|---|---|---|
| A1 | Scope | Pass: 17 files, all listed as in scope |
| A2 | Contracts | n/a |
| A3 | Tests | n/a (infra only); acceptance commands cover the behaviour |
| A4 | CI | Pending: the workflow file is valid, but CI has not run yet (the branch has no PR) |
| A5 | Architecture rules | n/a |
| A6 | Security | Pass: placeholder secrets only; `infra/.env` ignored; ports bound to 127.0.0.1; `permissions: contents: read`; actions pinned to `@v4`; gitleaks image pinned to `v8.24.3` |
| A7 | Fail-closed / errors | n/a |
| A8 | Money/time types | n/a |
| A9 | Migrations | n/a |
| A10 | No paid dependency; docs updated | Pass |

## Independent re-run of acceptance

Items 1–10 and 13 pass on the auditor's machine: both services healthy, `shared_buffers=768MB`, Redis `PONG` with auth and `NOAUTH` without it, `volatile-lru`, both ports on `127.0.0.1`, `infra/.env` ignored and not tracked.

## Findings (non-blocking; moved into WP-01 as F1–F3)

- **F1:** Redis is started via `sh -c` without `exec`, so SIGTERM does not reach redis-server and the container waits for the stop timeout.
- **F2:** in GitHub Actions, the gitleaks container may fail on git "dubious ownership". Run it with `--user "$(id -u):$(id -g)"`.
- **F3:** CI only triggers on PRs and on `main`, so pushed WP branches get no CI signal.
