# WP-20a: Web app shell (Vite/React/TS, typed API client, auth flows, terms/consent gates, design tokens)

| Field | Value |
|---|---|
| Size | M |
| Audit level | Standard + accessibility review |
| Branch | `wp-20a-web-shell` |
| Depends on | WP-04, WP-05 (API behaviour; use mocks in tests) |
| References | SRS UI-001 to UI-007, NFR-U01 to NFR-U03, NFR-P07, NFR-S09, UC-001 to UC-004; SDD 2.4, 2.5, 3.6.1 (auth/me rows); PRD 4.1, 4.2, 4.3 (items 1, 2, 7), 4.4, 4.5; `contracts/openapi/dist/public.yaml` |

## Goal

A production-grade web shell that the next web WPs plug screens into. It has:

- registration with an invite code, email verification, login, logout, and forgot/reset password;
- a session that refreshes itself;
- a blocking terms gate;
- consent selection;
- the navigation frame;
- design tokens, formatting helpers and the "provenance" / "stale" UI primitives;
- the Vietnamese error-code → message table.

## In scope

- `apps/web/**` (new)
- `.github/workflows/web.yml` (new)
- `docs/workpackages/reports/WP-20a.md`

## Out of scope

- Market, AI, watchlist, alert, paper and admin screens (WP-20b to WP-20e). Add their **routes as placeholders** ("Đang phát triển").

## Tooling

- Package manager **pnpm**. If `pnpm -v` fails, run `npm install -g pnpm` (user-level).
- Scaffold with `pnpm create vite@latest apps/web -- --template react-ts`.
- Dependencies (latest stable): `react-router-dom`, `@tanstack/react-query`, `openapi-fetch`, `zod`, `tailwindcss` with `@tailwindcss/vite` (Tailwind v4, CSS-first `@theme` tokens), `@fontsource/jetbrains-mono`.
- Dev dependencies: `openapi-typescript`, `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `@playwright/test`, `@axe-core/playwright`, `eslint` with the TS + react-hooks presets, `prettier`.

## Design

### API client

- `pnpm gen:api` runs `openapi-typescript ../../contracts/openapi/dist/public.yaml -o src/api/schema.d.ts`. Commit the output; CI fails if regenerating it changes anything.
- `src/api/client.ts` uses `openapi-fetch`:
  - `baseUrl: "/api/v1"`, `credentials: "include"`;
  - an `Authorization: Bearer <access>` header from the in-memory store (**never** `localStorage`).
- **Interceptor:**
  - On 401, call `POST /auth/refresh` once (client WEB, cookie), then retry the original request.
  - If the refresh fails: clear the session and navigate to `/dang-nhap?next=<path>`.
  - Concurrent 401s share **one** refresh call.
- **Errors:** every response that is not OK is parsed as RFC 9457 `Problem` and thrown as `ApiError{status, code, detail, correlationId, errors}`.
- **Dev proxy:** Vite proxies `/api` → `http://127.0.0.1:8080`, so cookies are same-origin.

### Session

- `AuthProvider` keeps `{accessToken, user}` in memory.
- On app start, call `POST /auth/refresh` silently. Success → logged in. Failure → logged out. No flash of protected content.
- Log out calls `/auth/logout` and clears state.

### Routes (Vietnamese slugs)

| Group | Routes |
|---|---|
| Public | `/dang-ky`, `/xac-minh-email?token=`, `/dang-nhap`, `/quen-mat-khau`, `/dat-lai-mat-khau?token=`, `/gioi-han-goi` (reads `GET /content/limits`), `/dieu-khoan` |
| Protected (inside `AppShell`) | `/` (Tổng quan), `/ma` (search), `/ma/:code`, `/theo-doi`, `/canh-bao`, `/gia-lap`, `/tro-ly-ai`, `/hop-thu`, `/tai-khoan`, `/quan-tri/*` (shown only to ADMIN) |

### Screens in this WP

**Register (US-001, US-002, US-058):**

- Fields: email, password, confirm, invite code.
- Terms text links; checkbox "Tôi đồng ý Điều khoản và Chính sách dữ liệu", required.
- Consents P2, P3, P4, **unchecked by default**, each with a one-line explanation. P1 is shown as required and cannot be changed.
- Client validation: password 10–128 chars, matching confirm.
- On 202, show "Kiểm tra email".
- `INVITE_INVALID` → the message from the table below.

**Verify email:** reads the token, calls the API, shows success with a link to log in, or an expired-link message with "Gửi lại".

**Login:**

- Email and password.
- 423 `ACCOUNT_LOCKED` shows the retry time from the detail.
- 403 `EMAIL_NOT_VERIFIED` offers a resend.
- Success → `next` or `/`.

**Forgot / reset password:** always says "Nếu email tồn tại...". Reset applies the password rules.

**Terms gate (US-006, PRD 4.3 item 1):**

- After login, and on any `TERMS_NOT_ACCEPTED` error, show a **blocking modal**: it cannot be dismissed with Esc or a click outside. Focus is trapped.
- It lists the current TERMS and PRIVACY titles with links. Actions: "Chấp thuận", "Đăng xuất", "Xóa tài khoản" (link to account deletion in WP-20e; placeholder for now).

**Account page:** placeholder in this WP.

### App shell (PRD 4.1, SDD 2.4)

- **Navigation:** Tổng quan · Mã · Theo dõi · Giả lập · Trợ lý AI. Left sidebar at ≥ 1024 px; bottom tab bar below that.
- **Top bar:** global search box (placeholder that navigates to `/ma`), inbox icon, account menu, theme toggle.
- A status banner area that reads `GET /content/status` every 60 s.

### Design system (UI-003 to UI-005, SDD 2.5)

**Tokens** in `src/styles/theme.css` (`@theme`):

- dark default plus a light theme;
- price colours: `--up` green, `--ref` yellow, `--down` red, `--ceil` purple, `--floor` cyan;
- surface, text and border tokens;
- every text/background pair meets contrast **≥ 4.5:1**; add a unit test that checks the token pairs with a contrast function.

**`<Price value change ref ceil floor>`:** coloured text plus a symbol (`▲`, `▼`, `■`, `⇡`/`⇣` for ceiling/floor) and `aria-label` in Vietnamese. Numbers use the mono font.

**Formatting** (`src/lib/format.ts`, `Intl`, `vi-VN`):

| Helper | Example |
|---|---|
| `formatVnd(57400000)` | `57.400.000 ₫` |
| `formatPrice(57400)` | `57.400` |
| `formatPct(1.21)` | `+1,21%` |
| `formatDateTime(iso)` | `21/10/2026 10:15` (Asia/Ho_Chi_Minh) |

**`<Provenance p>`:** "Trễ ≤ 60 giây · KBS · 10:15:30" / "Tính toán · …" / "Đóng cửa 20/10/2026". If `stale`, render "Dữ liệu đã cũ · cập nhật lần cuối hh:mm" in a warning style.

**`<DataState>`:** renders loading (skeleton within 300 ms), error (Vietnamese message + correlation id), stale, or unavailable. It **never** renders a number in place of missing data.

**Error messages** (`src/lib/errors.ts`): a map from **every** `Problem.code` in the contract to a Vietnamese message. A unit test asserts the map covers the contract enum, by reading it from the generated schema types.

**UI copy:** no advice wording. A unit test scans `src/**/*.tsx` string literals for the forbidden list from AGENTS.md.

### Security headers and CSP (NFR-S09)

- Production CSP is set by Caddy (WP-22).
- Add `index.html` meta tags only where safe.
- **No** inline scripts.
- **No** third-party scripts or fonts from CDNs: all assets are bundled.

### Tests

**Vitest:**

- format helpers;
- the error map covers every contract code;
- token contrast;
- forbidden-copy scan;
- the client interceptor: a single shared refresh on concurrent 401s; redirect when the refresh fails.

**Playwright** (API mocked with `page.route` on `/api/v1/**`):

- register happy path and `INVITE_INVALID`;
- login → app shell;
- 423 lock message;
- terms gate blocks navigation until accepted;
- logout;
- reset password;
- axe: no `serious`/`critical` violations on register, login and the terms gate;
- keyboard-only navigation through the register form.

**Bundle budget:** after `pnpm build`, the initial JS is ≤ 300 KB gzip. A script `scripts/check-bundle.mjs` fails above that.

### CI: `.github/workflows/web.yml`

- Triggers: like the other workflows, with path filters `apps/web/**` and `contracts/**`.
- Steps:
  1. pnpm install with `--frozen-lockfile`.
  2. `gen:api` + `git diff --exit-code`.
  3. lint, typecheck, vitest.
  4. Install Playwright chromium and run the tests.
  5. build + bundle check.

## Acceptance

Run from `apps/web`.

| # | Command | Expected |
|---|---|---|
| 1 | `pnpm install && pnpm gen:api && git diff --exit-code src/api/schema.d.ts` | no diff |
| 2 | `pnpm lint && pnpm typecheck && pnpm test` | pass |
| 3 | `pnpm exec playwright install chromium && pnpm e2e` | pass, including axe |
| 4 | `pnpm build && node scripts/check-bundle.mjs` | pass; paste the gzip size |
| 5 | Live (optional, needs the core stack): `pnpm dev`, register with `DEV-INVITE-001` from the dev seed, verify via the link in `DC logs core`, log in | Works; paste the steps |
