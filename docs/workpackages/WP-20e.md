# WP-20e: Web account and privacy, admin console

| Field | Value |
|---|---|
| Size | M |
| Audit level | **Deep** for privacy flows; standard for admin |
| Branch | `wp-20e-web-account-admin` |
| Depends on | WP-20a; API from WP-05, WP-06, WP-16b, WP-23 (mock in tests) |
| References | SRS FR-009, FR-010, FR-013 to FR-017, FR-210 to FR-217, FR-220, FR-221; PRD US-007 to US-010, US-048 to US-057, US-074, US-075; UC-013, UC-015 |

## Screens

### Tài khoản (`/tai-khoan`)

- **Hồ sơ:** display name; default alert channels.
- **Bảo mật:** change password; "Đăng xuất khỏi mọi thiết bị" with confirmation.
- **Quyền riêng tư:**
  - P1 is shown as required and cannot be toggled.
  - P2, P3, P4 are toggles that save immediately, with the explanation text. Turning P2 off shows "Cảnh báo email/push sẽ dừng trong vòng 5 phút".
  - "Tải dữ liệu cá nhân" downloads `POST /me/export` as a JSON file. Handle 429.
  - "Xóa tài khoản" (UC-013) opens a dialog listing the consequences (lists, alerts, paper data deleted; legal records kept anonymized) and asks for the password. Then 202 → logged out → a confirmation page.
- **Điều khoản:** current versions and acceptance state.
- **Phản hồi:** category and message → shows the ticket code.

### Quản trị (`/quan-tri/*`, visible only to role ADMIN; the server enforces it too)

| Page | Content |
|---|---|
| Người dùng | Search/filter list, cursor pagination; lock (with a required reason) / unlock |
| Mã mời | Create (label, max uses, expiry). Show the code **once** with a copy button and a warning that it will not be shown again. List: used/max, expiry, revoke |
| Điều khoản | Publish a new version (kind, version, title, markdown content). The preview renders markdown **safely**: sanitize, no raw HTML |
| Cờ tính năng | Toggles with descriptions; confirmation for `market_scores` and `beta_invite_only` |
| Rà soát AI | Queue filtered by source; each item shows text, facts and guard results (no user identity); verdict OK/VIOLATION with a note |
| Dữ liệu | `/admin/ops/ingestion`: last runs per job, failures, quarantine counts, provider health; refresh every 30 s |
| Chỉ số | Month picker → MET table with definitions and sources; manual metrics marked "nhập ngoài hệ thống" |
| Thông báo sự cố | Create and end status messages, if the endpoint exists (WP-23) |

## Tests

**Playwright** (mocked API):

- consent toggle;
- export download;
- deletion flow, including a wrong password;
- logout everywhere;
- change password;
- feedback;
- an admin route as USER → redirect plus no admin links;
- admin user lock (with reason) and unlock;
- invite code shown once;
- publish terms (markdown sanitized: a test with a `<script>` in the content proves it is not executed);
- flags confirmation;
- review verdict;
- ingestion page;
- metrics page;
- axe on every page.

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` | pass |
| 2 | `pnpm build && node scripts/check-bundle.mjs` | budget kept (admin pages lazy-loaded) |
