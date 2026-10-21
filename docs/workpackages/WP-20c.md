# WP-20c: Web AI assistant, watchlists, alerts, inbox, Web Push

| Field | Value |
|---|---|
| Size | M |
| Audit level | Standard + compliance-copy review |
| Branch | `wp-20c-web-ai-watch-alerts` |
| Depends on | WP-20a, WP-20b; API from WP-16b, WP-17, WP-18 (mock in tests) |
| References | SRS FR-061 to FR-073, FR-080 to FR-097, UI-007; PRD US-028 to US-038, 4.3 (items 4, 5), 4.5; UC-007 to UC-010 |

## Screens

### Trợ lý AI (`/tro-ly-ai`, US-028 to US-033)

- Suggested neutral questions, for example "RSI(14) của FPT đang ở mức nào?" and "VN-Index hôm nay thế nào?".
- **Input:** 500-character counter; `?symbol=` pre-fills the context.
- **Header:** remaining quota from `/ai/quota`.
- **Answers:**
  - the label and disclaimer are always visible;
  - citation chips as in WP-20b;
  - 👍 / 👎 and "Báo cáo nội dung" (reason dialog).
- **Errors:** `AI_QUOTA_EXCEEDED` shows the reset time; REFUSED answers render as normal answers.
- The conversation is kept only in memory (not persisted).

### Theo dõi (`/theo-doi`, US-034)

- Tabs per list: create, rename, delete, reorder.
- Rows: code, price (`<Price>`), pct, provenance/stale. Tapping a row opens the symbol page.
- Add and remove symbols, including from the symbol page's "☆ Theo dõi" button, which now goes live.
- Limits (5 × 50) produce the `LIMIT_EXCEEDED` message.

### Cảnh báo (`/canh-bao`, US-035 to US-038)

- List by status: Đang hoạt động / Chờ phiên sau / Tạm dừng / Hết hạn.
- **Create dialog** (also from the symbol page "🔔 Cảnh báo"):
  - condition, threshold (pre-filled with the current price), channels, optional expiry;
  - a preview sentence, for example "Thông báo khi giá FPT ≥ 130.000".
- **Channel consent:** if EMAIL/PUSH is chosen without P2, show a link to the privacy settings (FR-097).
- History tab (90 days).

### Hộp thư (`/hop-thu`)

- Paginated notifications; mark as read; an unread badge in the top bar, polled every 60 s.

### Web Push (PRD 4.3 item 5)

- Ask for permission **only** when the user creates the first alert with the PUSH channel.
- Register a service worker `sw.js` that shows notifications and opens the deep link.
- Subscribe with `VITE_VAPID_PUBLIC_KEY` (build-time env; document it in the README). `POST /devices {platform: WEB_PUSH, token: JSON.stringify(subscription)}`.
- If permission is denied, suggest email or the inbox, and do not ask again for 30 days (`localStorage` timestamp).

## Tests

**Vitest:** quota display; preview sentence builder; 30-day re-ask logic.

**Playwright** (mocked API):

- chat happy path with a citation;
- REFUSED answer;
- quota exceeded;
- report dialog;
- watchlist CRUD and limits;
- alert creation with preview;
- P2 missing → consent link;
- inbox mark-read;
- push permission requested only on the first PUSH alert (mock `Notification.requestPermission`);
- axe on every screen.

**Forbidden-copy scan** still passes.

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` | pass |
| 2 | `pnpm build && node scripts/check-bundle.mjs` | budget kept |
