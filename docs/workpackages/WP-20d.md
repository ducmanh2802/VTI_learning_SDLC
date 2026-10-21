# WP-20d: Web paper trading (account, two-step order ticket, positions, orders, ledger, limits, rules)

| Field | Value |
|---|---|
| Size | M |
| Audit level | Standard + money-display review |
| Branch | `wp-20d-web-paper` |
| Depends on | WP-20a, WP-20b; API from WP-19 (mock in tests) |
| References | SRS FR-100 to FR-115, NFR-U03; PRD US-039 to US-047, 4.2 (Giả lập, phiếu lệnh), 4.3 (item 3), 4.4 (no gamification), 4.5; UC-011, UC-012 |

## Screens

### Giả lập (`/gia-lap`)

- **Permanent strip:** "Kết quả giả lập không phản ánh kết quả giao dịch thực" + a link to "Quy tắc giả lập" (`/gia-lap/quy-tac`, from `/content/fill-rules`).
- **Account summary:** NAV, cash, available cash, unrealized and realized P&L, status.
  - `HALTED` → a red banner with the reason and a "Mở lại" button with a confirmation step.
  - `navPriceBasis = CLOSE` → a note "theo giá đóng cửa gần nhất".
- **Tabs:**
  - **Vị thế:** quantity total/available (with "chờ về T+2"), average cost, last price, market value, P&L.
  - **Lệnh:** đang chờ / đã khớp / hết hạn / đã hủy / bị từ chối with the reason; cancel for OPEN orders.
  - **Sổ cái:** paginated entries with type, asset, amount and available date.
- **Settings:** max order value, max daily value, max drawdown %; clearable.
- **Reset account:** confirmation dialog explaining that history is archived.

### Order ticket (modal / bottom sheet, US-040, US-041; PRD 4.3 item 3: **two steps**)

**Step 1, Nhập:**

- Symbol, Mua/Bán, LO/MP, quantity stepper (step 100), limit price stepper (tick by exchange and price, mirroring the WP-19 tick table in `src/lib/ticks.ts`).
- Shows ceiling and floor.
- Estimate: value, fee (0.15%), tax for sells (0.1%), total.
- **Inline pre-checks** mirror RiskGuard: lot, band, tick, cash, shares, session. They show the same Vietnamese messages as the server, but the **server stays the authority**.

**Step 2, Xem lại:** a summary, then "Xác nhận lệnh giả lập".

**Submit:**

- The `Idempotency-Key` is generated once per ticket (`crypto.randomUUID()`) and reused on retry.
- Result: FILLED with fill details, or OPEN, or a 422 rejection with the code's Vietnamese message. The user can go back to step 1 without losing input.

**Money display:** amounts come from the API as integers (VND). Client estimates are labelled "ước tính", and their arithmetic uses integers only.

**No gamification** (PRD 4.4): no confetti, badges or leaderboards.

## Tests

**Vitest:** the tick table (boundaries 9,990 / 10,000 / 49,950 / 50,000); fee and tax estimates (integer maths); pre-check messages.

**Playwright** (mocked API):

- MP buy → FILLED;
- LO → OPEN → cancel;
- each RiskGuard 422 code shows the right message;
- `DATA_STALE` disables submit;
- halted banner and resume;
- settings save;
- reset confirmation;
- **idempotent retry** (the same key is sent twice after a simulated network error);
- axe.

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` | pass |
| 2 | `pnpm build && node scripts/check-bundle.mjs` | budget kept |
