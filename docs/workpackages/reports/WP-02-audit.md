# WP-02 audit (Claude)

- **Verdict:** PASS after audit fixes (F1–F3, applied by Claude in a separate commit)
- **Date:** 2026-10-21
- **Branch:** `wp-02-contracts`, merged into `integration/r1`
- **Agent:** OpenCode, revision 2 run with model `opencode/deepseek-v4.1-flash-free`, 0 fix rounds. Revision 1 (`glm-5.3-flash-free`, single 3,000-line file) was stopped at 151 lint errors.

## Checklist

| # | Item | Result |
|---|---|---|
| A1 | Scope | Pass: only `contracts/**`, `.github/workflows/contracts.yml` and the report (checked against the merge base) |
| A2 | Contracts | Pass: 78 public and 19 internal operations; every SDD 3.6.1/3.6.2 row is mapped; `/health` is the only extra path (required by the brief) |
| A3 | Tests | The contract CI encodes lint, the stale-bundle diff and ajv |
| A4 | CI | Pending: `contracts.yml` runs on the first push of `integration/r1` after this merge |
| A5 | Architecture rules | Pass: the public and internal specs have no cross references; dist bundles are generated, never hand-edited |
| A6 | Security | Pass: `security: []` exactly on the 11 SDD "—" endpoints and `/health`; `/auth/refresh` accepts the `refreshCookie` or no scheme (mobile body); `bearerAuth` everywhere else; every `/admin` operation says ADMIN in its description; internal API uses `serviceToken` except the two health probes |
| A7 | Fail-closed / errors | Pass after F1: every 4xx/5xx is `application/problem+json`; `Problem.code` has exactly the 23 codes of the SDD error table (`INVITE_INVALID` included) |
| A8 | Money/time types | Pass after F3: VND as `int64`, prices `multipleOf: 0.01`, uuid ids, `date-time` / `date` |
| A9 | Migrations | n/a |
| A10 | No paid dependency; docs updated | Pass: Redocly CLI and ajv-cli via `npx`; `contracts/openapi/README.md` added |

## Independent re-run

| # | Check | Result |
|---|---|---|
| 1 | Redocly lint | 0 errors, 0 warnings for both APIs |
| 2 | Fresh bundles vs `dist/` | identical (diff exit 0 for both), before and after the audit fixes |
| 3 | ajv on the `s:quotes` example | valid |
| 4 | Path-by-path script over the bundles (method, path, operationId, tag, security) | matches SDD 3.6.1/3.6.2 |
| 5 | `Problem.code` | 23 values, equal to the SDD error table |
| 6 | Largest source file | 80 lines (`MarketOverview.yaml`) |
| 7 | Enums | `SessionState` = SRS FR-024; paper order status = `paper.orders` CHECK in `schema.sql` |

## Findings (fixed by Claude)

| # | Severity | Finding | Fix |
|---|---|---|---|
| F1 | Major | `Quote.price`, `Quote.volume`, `Quote.value` and `Mover.volume` were required non-null. On the vnstock Guest tier there is no matched volume/value (WP-08 probe), and there is no price before the first match. Producers would have had to send `0`, which breaks fail-closed (FR-030: never show zeros) | Made them nullable (still required keys) with descriptions, in both specs |
| F2 | Minor | `GET /symbols/{code}/bars` used cursor pagination with `limit` ≤ 100, so a one-year chart (~250 bars) needed 3 calls | Removed `limit`/`cursor` and `nextCursor`; the range `[from, to]` bounds the response (max 5 years, otherwise 400). Bars are a time series, not a list |
| F3 | Minor | `Bar.value` was required non-null, but `market.daily_bars.value` is nullable and vnstock `ohlcv` has no value column. The `PaperOrder` example fee was 186,000 VND instead of 18,600 (100 × 124,000 × 0.15%) | `Bar.value` nullable; example fee corrected |

## Accepted deviations

- `Fact.value` is a decimal **string** (exact precision, matches the SDD 3.6.2 example).
- Extra reusable response `Locked` (423 for `ACCOUNT_LOCKED`) and extra shared parameters (`Id`, `SymbolPath`, `FlagKey`, `Purpose`, internal `CorrelationId`).
- Nested `contracts/openapi/.gitignore` re-includes the two bundles despite the root `dist/` rule.
- Admin `GET / POST` rows: `POST` maps to the action sub-paths (`/lock`, `/unlock`, `/revoke`, `/verdict`). There is no FR for creating users or reviews, so the agent's reading is correct.

## Notes for later WPs

- WP-03 / WP-13b: map a null `price` / `volume` / `value` to "—" in the UI, never to 0.
- WP-12: `topMovers.volumeSpike` is an empty array and `unavailable` contains `volume_spike` on the Guest tier.
- `ProductEvent.platform` excludes `server`; server-side events are written directly by Core (WP-23).
