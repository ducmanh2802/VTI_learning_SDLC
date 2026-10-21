# WP-20b: Web market screens (overview + treemap, symbol search, symbol detail with chart, indicators, order book, AI summary)

| Field | Value |
|---|---|
| Size | L |
| Audit level | Standard + compliance-copy review |
| Branch | `wp-20b-web-market` |
| Depends on | WP-20a; API from WP-13b, WP-16b (mock in tests) |
| References | SRS FR-021 to FR-030, FR-040 to FR-054, FR-060, FR-063, FR-069, UI-004 to UI-007, NFR-P04, NFR-P07; SDD ALG-05 (squarified treemap on the client); PRD US-011 to US-027, 4.2, 4.4, 4.5 |

## Goal

Build the Tổng quan, Mã and chi tiết mã screens with:

- live polling during sessions;
- provenance on every block;
- fail-closed rendering;
- the squarified treemap;
- the candlestick chart with indicators;
- the AI summary with clickable citations.

## In scope

- `apps/web/src/features/{market,symbol}/**` and the shared components they need
- Tests
- `docs/workpackages/reports/WP-20b.md`

## New dependencies

- `lightweight-charts` (Apache-2.0)
- `d3-hierarchy` (treemap with `treemapSquarify`)

## Screens

### Tổng quan (`/`, US-017 to US-020)

- **Header:** session state from `/market/state` (Vietnamese labels: "Phiên mở cửa (ATO)", "Khớp lệnh liên tục", "Nghỉ trưa", "ATC", "Đóng cửa").
- **Blocks:**
  - 4 index cards;
  - breadth bars per exchange (advancers, decliners, unchanged, ceiling, floor);
  - % above MA20/50/200;
  - top movers tabs (Tăng mạnh / Giảm mạnh / Thanh khoản đột biến);
  - the market card lines;
  - the treemap.
- **`unavailable`:** each section listed in the response's `unavailable` renders an explicit notice, for example "Dữ liệu thanh khoản trong phiên chưa có ở cấp nguồn dữ liệu hiện tại". It never renders an empty chart.
- **Treemap:**
  - weight selector (only the weights the API offers) and direction selector;
  - squarified layout computed client-side with `d3-hierarchy`;
  - cell colour from pct, using the price tokens;
  - each cell shows the group name and its leader;
  - click a group → drill down to its symbols; click a symbol → the symbol page;
  - keyboard accessible, with `role="grid"`-like navigation, or at least focusable cells with `aria-label`.

### Mã (`/ma`, US-011)

- Search-as-you-type, debounced 250 ms, at most 20 results.
- Recently viewed list (last 10 codes in `sessionStorage`).

### Chi tiết mã (`/ma/:code`, US-012 to US-016, US-022 to US-027)

**Price block:** price, change, pct, reference, ceiling, floor, volume, `<Provenance>`.

**Chart (`lightweight-charts`):**

- Candlesticks plus a volume histogram; intervals D, W, M; ranges 3M, 1Y, 5Y.
- Overlay toggles: SMA20/50/200, Bollinger.
- Sub-panes: RSI14 with 30/70 guide lines, and MACD.
- **Charts are lazy-loaded**, so the chart code is not in the initial bundle (NFR-P07).

**Tabs:**

- **Phân tích:**
  - neutral rule descriptions (from `/indicators`);
  - the AI summary block: label "Nội dung do AI tạo" + "Không phải khuyến nghị đầu tư", always visible (UI-007);
  - in the text, `[F3]` markers become citation chips; clicking one opens a popover with label, value, source and time;
  - FALLBACK → the facts table plus "Tóm tắt AI tạm thời không khả dụng";
  - skeleton while loading, with a 15 s cap.
- **Cơ bản:** fundamentals, or the unavailable notice.
- **Sổ lệnh:** 3 levels.

**Actions:** "☆ Theo dõi" and "🔔 Cảnh báo" (wired in WP-20c; placeholders here), "Giả lập lệnh" (WP-20d), "Hỏi AI về mã này" (links to `/tro-ly-ai?symbol=`).

**Derivatives:** on a 403 `DERIVATIVE_RISK_NOT_ACKED`, show the risk-disclosure modal:

- the checkbox is unchecked by default;
- the button is enabled only after it is checked;
- confirming calls `POST /me/derivative-risk/ack` and retries the request.

### Polling (CI-004, FR-022)

- During ATO, CONTINUOUS and ATC, use TanStack Query `refetchInterval: 60_000` for quote, overview and state.
- Otherwise do not poll.
- Pause polling when the tab is hidden.

## Tests

**Vitest:**

- the treemap layout helper: total area preserved; deterministic output for fixed data;
- citation parsing (`[F1]` → chips, unknown ids left as text);
- polling decision by session state.

**Playwright** (mocked API):

- overview renders every block;
- `unavailable` notices;
- treemap drill-down and navigation;
- search → symbol page;
- chart lazy chunk loaded;
- AI summary PUBLISHED with a citation popover;
- FALLBACK table;
- stale quote shows the stale label and **no number in place of missing data**;
- derivative modal flow;
- axe on the overview and symbol pages.

**Budget:** the initial JS still ≤ 300 KB gzip.

## Acceptance

| # | Command | Expected |
|---|---|---|
| 1 | `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e` | pass |
| 2 | `pnpm build && node scripts/check-bundle.mjs` | ≤ 300 KB gzip initial |
| 3 | Live (optional, full stack running) | Overview and FPT page render real data with provenance; screenshots in the report |
