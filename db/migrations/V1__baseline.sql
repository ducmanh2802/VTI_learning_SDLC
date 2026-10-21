-- =============================================================================
-- VN Stock AI Pro: database baseline (PostgreSQL 16)
-- Nguồn cho db/migrations/V1__baseline.sql (WP-01). Thiết kế: Blueprint_SDD.md mục 3.5.
--
-- Quyền ghi (ADR-003):
--   core, paper, strategy  -> Core service      (role core_rw)
--   market, ai, research   -> Analytics service (role analytics_rw)
-- Quy ước: tiền = bigint (đồng); giá = numeric(14,2); thời điểm = timestamptz (UTC);
--          ngày giao dịch = date theo Asia/Ho_Chi_Minh (SRS SC-011, SC-012).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid(), gen_random_bytes()
CREATE EXTENSION IF NOT EXISTS citext;     -- email không phân biệt hoa thường
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- tìm tên mã không dấu (FR-021)

CREATE SCHEMA IF NOT EXISTS util;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS paper;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS strategy;   -- R2
CREATE SCHEMA IF NOT EXISTS research;   -- R2

-- Role nhóm (NOLOGIN). User đăng nhập của từng service được tạo bởi infra/bootstrap
-- với mật khẩu lấy từ secret, rồi GRANT role nhóm tương ứng.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'core_rw') THEN
        CREATE ROLE core_rw NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics_rw') THEN
        CREATE ROLE analytics_rw NOLOGIN;
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- util: hàm dùng chung
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION util.forbid_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Bảng % chỉ cho phép ghi thêm: thao tác % bị cấm', TG_TABLE_NAME, TG_OP;
END $$;

CREATE OR REPLACE FUNCTION util.touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

-- =============================================================================
-- core (Core service)
-- =============================================================================

-- Người dùng (FR-001 đến FR-018, ST-01). Tài khoản DELETED được giữ dạng bia mộ
-- không còn dữ liệu cá nhân để các khóa ngoại kiểm toán vẫn hợp lệ (FR-016).
CREATE TABLE core.users (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email                  citext NOT NULL CHECK (length(email) <= 254),
    password_hash          text NOT NULL,
    display_name           text CHECK (length(display_name) <= 60),
    status                 text NOT NULL DEFAULT 'PENDING_VERIFICATION'
                           CHECK (status IN ('PENDING_VERIFICATION', 'ACTIVE', 'SUSPENDED',
                                             'DELETION_REQUESTED', 'DELETED')),
    role                   text NOT NULL DEFAULT 'USER' CHECK (role IN ('USER', 'ADMIN')),
    plan                   text NOT NULL DEFAULT 'FREE' CHECK (plan IN ('FREE')),  -- R3 thêm gói trả phí
    email_verified_at      timestamptz,
    failed_login_count     integer NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until           timestamptz,
    totp_secret_enc        bytea,           -- chỉ ADMIN, mã hóa bằng khóa ứng dụng (FR-018)
    user_secret            bytea DEFAULT gen_random_bytes(32),  -- khóa HMAC cho userRef; xóa khi DELETED (SD-07)
    default_alert_channels text[] NOT NULL DEFAULT ARRAY['IN_APP']::text[],
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    deletion_requested_at  timestamptz,
    deleted_at             timestamptz,
    CONSTRAINT users_secret_present CHECK (status = 'DELETED' OR user_secret IS NOT NULL),
    CONSTRAINT users_admin_totp CHECK (role <> 'ADMIN' OR status <> 'ACTIVE' OR totp_secret_enc IS NOT NULL),
    CONSTRAINT users_default_channels CHECK (default_alert_channels <@ ARRAY['IN_APP', 'EMAIL', 'PUSH']::text[])
);
CREATE UNIQUE INDEX users_email_uq ON core.users (email) WHERE status <> 'DELETED';
CREATE INDEX users_deletion_due ON core.users (deletion_requested_at) WHERE status = 'DELETION_REQUESTED';
CREATE TRIGGER users_touch BEFORE UPDATE ON core.users
    FOR EACH ROW EXECUTE FUNCTION util.touch_updated_at();

-- Token email dùng một lần (FR-003, FR-008). Chỉ lưu SHA-256 của token.
CREATE TABLE core.email_tokens (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    purpose     text NOT NULL CHECK (purpose IN ('VERIFY_EMAIL', 'RESET_PASSWORD')),
    token_hash  bytea NOT NULL UNIQUE,
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX email_tokens_open ON core.email_tokens (user_id, purpose) WHERE used_at IS NULL;

-- Refresh token xoay vòng; phát hiện dùng lại theo family (FR-004, NFR-S04, SD-02).
CREATE TABLE core.refresh_tokens (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    family_id    uuid NOT NULL,
    token_hash   bytea NOT NULL UNIQUE,
    client       text NOT NULL CHECK (client IN ('WEB', 'MOBILE')),
    issued_at    timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    revoked_at   timestamptz,
    replaced_by  uuid REFERENCES core.refresh_tokens (id),
    user_agent   text,
    ip           inet
);
CREATE INDEX refresh_tokens_active ON core.refresh_tokens (user_id) WHERE revoked_at IS NULL;
CREATE INDEX refresh_tokens_family ON core.refresh_tokens (family_id);

-- Nhật ký bảo mật, giữ 90 ngày (SRS DR-003).
CREATE TABLE core.security_events (
    id           bigserial PRIMARY KEY,
    occurred_at  timestamptz NOT NULL DEFAULT now(),
    user_id      uuid REFERENCES core.users (id),
    event        text NOT NULL CHECK (event IN ('LOGIN_OK', 'LOGIN_FAIL', 'LOCKED', 'TOKEN_REUSED',
                                                'PASSWORD_RESET', 'PASSWORD_CHANGED', 'TOTP_FAIL')),
    ip           inet,
    user_agent   text
);
CREATE INDEX security_events_time ON core.security_events (occurred_at);

-- Phiên bản điều khoản, chính sách dữ liệu, công bố rủi ro phái sinh (FR-011, FR-012, FR-015, FR-211).
-- Phiên bản hiện hành của mỗi loại = bản có published_at lớn nhất.
CREATE TABLE core.terms_versions (
    version       text PRIMARY KEY,
    kind          text NOT NULL CHECK (kind IN ('TERMS', 'PRIVACY', 'DERIVATIVE_RISK')),
    title         text NOT NULL,
    content_md    text NOT NULL,
    published_at  timestamptz NOT NULL DEFAULT now(),
    published_by  uuid REFERENCES core.users (id)
);
CREATE INDEX terms_versions_current ON core.terms_versions (kind, published_at DESC);
CREATE TRIGGER terms_versions_immutable BEFORE UPDATE OR DELETE ON core.terms_versions
    FOR EACH ROW EXECUTE FUNCTION util.forbid_mutation();

-- Bằng chứng chấp thuận. Job xóa tài khoản đặt ip, user_agent = NULL (FR-016).
CREATE TABLE core.terms_acceptances (
    id           bigserial PRIMARY KEY,
    user_id      uuid NOT NULL REFERENCES core.users (id),
    version      text NOT NULL REFERENCES core.terms_versions (version),
    accepted_at  timestamptz NOT NULL DEFAULT now(),
    ip           inet,
    user_agent   text,
    UNIQUE (user_id, version)
);

-- Mục đích xử lý dữ liệu (FR-013). Mục đích tùy chọn mặc định KHÔNG đồng ý.
CREATE TABLE core.consent_purposes (
    code             text PRIMARY KEY,
    description      text NOT NULL,
    required         boolean NOT NULL,
    default_granted  boolean NOT NULL
);

-- Lịch sử đồng ý, chỉ ghi thêm (FR-013, FR-014). Trạng thái hiện tại xem ở view current_consents.
CREATE TABLE core.consents (
    id            bigserial PRIMARY KEY,
    user_id       uuid NOT NULL REFERENCES core.users (id),
    purpose_code  text NOT NULL REFERENCES core.consent_purposes (code),
    granted       boolean NOT NULL,
    source        text NOT NULL CHECK (source IN ('REGISTER', 'SETTINGS', 'DELETION')),
    recorded_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX consents_lookup ON core.consents (user_id, purpose_code, recorded_at DESC);
CREATE TRIGGER consents_append_only BEFORE UPDATE OR DELETE ON core.consents
    FOR EACH ROW EXECUTE FUNCTION util.forbid_mutation();

CREATE VIEW core.current_consents AS
SELECT DISTINCT ON (user_id, purpose_code) user_id, purpose_code, granted, recorded_at
FROM core.consents
ORDER BY user_id, purpose_code, recorded_at DESC;

-- Danh sách theo dõi (FR-080 đến FR-082). Giới hạn 5 × 50 áp ở tầng ứng dụng (cấu hình).
CREATE TABLE core.watchlists (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    name        text NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    sort_order  smallint NOT NULL DEFAULT 0,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE TABLE core.watchlist_items (
    watchlist_id  uuid NOT NULL REFERENCES core.watchlists (id) ON DELETE CASCADE,
    symbol        text NOT NULL,
    sort_order    smallint NOT NULL DEFAULT 0,
    added_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (watchlist_id, symbol)
);

-- Cảnh báo (FR-090 đến FR-095, ST-02, ALG-09).
CREATE TABLE core.alerts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    symbol               text NOT NULL,
    condition_type       text NOT NULL CHECK (condition_type IN ('PRICE_GTE', 'PRICE_LTE', 'PCT_CHANGE_GTE',
                                                                 'PCT_CHANGE_LTE', 'VOLUME_GTE',
                                                                 'STRATEGY_SIGNAL')),  -- STRATEGY_SIGNAL: R2
    threshold            numeric(20, 4),
    strategy_version_id  uuid,              -- R2, tham chiếu strategy.strategy_versions
    channels             text[] NOT NULL,
    status               text NOT NULL DEFAULT 'ACTIVE'
                         CHECK (status IN ('ACTIVE', 'COOLDOWN', 'PAUSED', 'EXPIRED', 'DELETED')),
    expires_at           timestamptz,
    last_triggered_at    timestamptz,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT alerts_channels CHECK (cardinality(channels) > 0
                                      AND channels <@ ARRAY['IN_APP', 'EMAIL', 'PUSH']::text[]),
    CONSTRAINT alerts_strategy CHECK ((condition_type = 'STRATEGY_SIGNAL') = (strategy_version_id IS NOT NULL)),
    CONSTRAINT alerts_threshold CHECK (condition_type = 'STRATEGY_SIGNAL' OR threshold IS NOT NULL)
);
CREATE INDEX alerts_by_symbol ON core.alerts (symbol) WHERE status IN ('ACTIVE', 'COOLDOWN');
CREATE INDEX alerts_by_user ON core.alerts (user_id) WHERE status <> 'DELETED';
CREATE TRIGGER alerts_touch BEFORE UPDATE ON core.alerts
    FOR EACH ROW EXECUTE FUNCTION util.touch_updated_at();

-- Mỗi cảnh báo kích hoạt tối đa 1 lần mỗi phiên (FR-093): UNIQUE (alert_id, session_date).
CREATE TABLE core.alert_events (
    id              bigserial PRIMARY KEY,
    alert_id        uuid NOT NULL REFERENCES core.alerts (id) ON DELETE CASCADE,
    session_date    date NOT NULL,
    triggered_at    timestamptz NOT NULL DEFAULT now(),
    quote_snapshot  jsonb NOT NULL,          -- {price, pct, volume, ts, src}
    UNIQUE (alert_id, session_date)
);

-- Thiết bị nhận push (FR-097).
CREATE TABLE core.devices (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    platform      text NOT NULL CHECK (platform IN ('EXPO', 'WEB_PUSH')),
    token         text NOT NULL,             -- Expo push token hoặc JSON subscription của Web Push
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (platform, token)
);

-- Hộp thư trong ứng dụng, giữ 90 ngày (FR-096, DR-008).
CREATE TABLE core.notifications (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    kind        text NOT NULL CHECK (kind IN ('ALERT', 'SECURITY', 'ACCOUNT', 'PAPER', 'SYSTEM')),
    title       text NOT NULL CHECK (length(title) <= 120),
    body        text NOT NULL CHECK (length(body) <= 1000),
    deep_link   text,
    payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    read_at     timestamptz
);
CREATE INDEX notifications_inbox ON core.notifications (user_id, created_at DESC);

-- Transactional outbox (mục 3.11). Worker lấy bản ghi PENDING đến hạn, gửi, thử lại 10 s / 60 s / 5 phút.
CREATE TABLE core.notification_outbox (
    id               bigserial PRIMARY KEY,
    notification_id  uuid NOT NULL REFERENCES core.notifications (id) ON DELETE CASCADE,
    channel          text NOT NULL CHECK (channel IN ('EMAIL', 'PUSH')),
    status           text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'SKIPPED')),
    attempts         smallint NOT NULL DEFAULT 0,
    next_attempt_at  timestamptz NOT NULL DEFAULT now(),
    last_error       text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    sent_at          timestamptz
);
CREATE INDEX outbox_due ON core.notification_outbox (next_attempt_at) WHERE status = 'PENDING';

-- Nhật ký kiểm toán, chỉ ghi thêm (FR-216, NFR-S08). detail KHÔNG chứa dữ liệu cá nhân.
CREATE TABLE core.audit_log (
    id              bigserial PRIMARY KEY,
    occurred_at     timestamptz NOT NULL DEFAULT now(),
    actor_type      text NOT NULL CHECK (actor_type IN ('USER', 'ADMIN', 'SYSTEM')),
    actor_id        uuid,
    action          text NOT NULL,           -- ví dụ: LOGIN, TERMS_ACCEPT, CONSENT_CHANGE, PAPER_ORDER, FLAG_SET
    target_type     text,
    target_id       text,
    detail          jsonb NOT NULL DEFAULT '{}'::jsonb,
    correlation_id  uuid
);
CREATE INDEX audit_log_time ON core.audit_log (occurred_at);
CREATE INDEX audit_log_actor ON core.audit_log (actor_id, occurred_at);
CREATE TRIGGER audit_log_append_only BEFORE UPDATE OR DELETE ON core.audit_log
    FOR EACH ROW EXECUTE FUNCTION util.forbid_mutation();

-- Đếm câu hỏi AI theo ngày, dùng cho báo cáo (bộ đếm thời gian thực nằm ở Redis).
CREATE TABLE core.ai_usage_daily (
    user_id     uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    usage_date  date NOT NULL,
    questions   integer NOT NULL DEFAULT 0 CHECK (questions >= 0),
    PRIMARY KEY (user_id, usage_date)
);

-- Phản hồi và khiếu nại (FR-220).
CREATE TABLE core.feedback_tickets (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code         text NOT NULL UNIQUE,       -- ví dụ: FB-2026-000123
    user_id      uuid REFERENCES core.users (id),
    category     text NOT NULL CHECK (category IN ('FEEDBACK', 'COMPLAINT', 'BUG', 'DATA_ISSUE')),
    message      text NOT NULL CHECK (length(message) BETWEEN 1 AND 4000),
    status       text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ANSWERED', 'CLOSED')),
    created_at   timestamptz NOT NULL DEFAULT now(),
    answered_at  timestamptz
);

-- Cờ tính năng (FR-214).
CREATE TABLE core.feature_flags (
    key          text PRIMARY KEY,
    enabled      boolean NOT NULL DEFAULT false,
    description  text NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now(),
    updated_by   uuid REFERENCES core.users (id)
);

-- Banner sự cố (FR-221).
CREATE TABLE core.status_messages (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    severity    text NOT NULL CHECK (severity IN ('INFO', 'DEGRADED', 'OUTAGE')),
    message     text NOT NULL CHECK (length(message) <= 500),
    starts_at   timestamptz NOT NULL DEFAULT now(),
    ends_at     timestamptz,
    created_by  uuid REFERENCES core.users (id)
);

-- Nội dung tĩnh do quản trị viên quản lý: giải thích chỉ báo, giới hạn gói, quy tắc giả lập
-- (FR-054, FR-109, FR-180).
CREATE TABLE core.content_pages (
    key         text PRIMARY KEY,            -- ví dụ: indicator.rsi, limits.free, paper.fill-rules
    title       text NOT NULL,
    body_md     text NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now(),
    updated_by  uuid REFERENCES core.users (id)
);

-- Mã mời cho beta kín (FR-019, FR-217; CR-02). Chỉ lưu SHA-256 của mã; mã gốc hiển thị đúng một lần khi tạo.
CREATE TABLE core.invites (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code_hash   bytea NOT NULL UNIQUE,
    label       text CHECK (length(label) <= 80),
    max_uses    integer NOT NULL CHECK (max_uses BETWEEN 1 AND 1000),
    used_count  integer NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    expires_at  timestamptz NOT NULL,
    revoked_at  timestamptz,
    created_by  uuid REFERENCES core.users (id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT invites_usage CHECK (used_count <= max_uses)
);

CREATE TABLE core.invite_redemptions (
    invite_id    uuid NOT NULL REFERENCES core.invites (id),
    user_id      uuid NOT NULL UNIQUE REFERENCES core.users (id),
    redeemed_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (invite_id, user_id)
);

-- Sự kiện sử dụng ẩn danh, chỉ khi có đồng ý P3 (FR-223, FR-224; CR-01). Giữ 13 tháng (DR-010).
CREATE TABLE core.product_events (
    id           bigserial PRIMARY KEY,
    occurred_at  timestamptz NOT NULL,
    received_at  timestamptz NOT NULL DEFAULT now(),
    user_ref     text NOT NULL,              -- HMAC(user_secret, userId), như ai.interactions
    session_id   uuid,
    event        text NOT NULL CHECK (event ~ '^[a-z]+(_[a-z]+)+$'),
    platform     text NOT NULL CHECK (platform IN ('web', 'android', 'pwa', 'server')),
    properties   jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (pg_column_size(properties) <= 2048)
);
CREATE INDEX product_events_time ON core.product_events (occurred_at);
CREATE INDEX product_events_event ON core.product_events (event, occurred_at);

-- =============================================================================
-- paper (Core service): giả lập, RiskGuard, sổ cái (FR-100 đến FR-117, ALG-10 đến ALG-13)
-- =============================================================================

CREATE TABLE paper.accounts (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    status            text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'HALTED', 'ARCHIVED')),
    initial_cash      bigint NOT NULL CHECK (initial_cash > 0),               -- mặc định 500.000.000 (OQ-049)
    fee_rate          numeric(7, 6) NOT NULL CHECK (fee_rate >= 0 AND fee_rate < 0.01),  -- OQ-044
    sell_tax_rate     numeric(7, 6) NOT NULL DEFAULT 0.001 CHECK (sell_tax_rate >= 0),   -- BRU-008
    max_order_value   bigint CHECK (max_order_value > 0),                     -- FR-107
    max_daily_value   bigint CHECK (max_daily_value > 0),                     -- FR-107
    max_drawdown_pct  numeric(5, 2) CHECK (max_drawdown_pct > 0 AND max_drawdown_pct <= 100),  -- FR-108
    peak_nav          bigint NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    halted_at         timestamptz,
    archived_at       timestamptz
);
-- Mỗi người dùng có đúng 1 tài khoản chưa lưu trữ.
CREATE UNIQUE INDEX paper_accounts_one_open ON paper.accounts (user_id) WHERE status <> 'ARCHIVED';

CREATE TABLE paper.orders (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id           uuid NOT NULL REFERENCES paper.accounts (id),
    client_order_id      uuid NOT NULL,                                       -- khóa chống trùng (FR-101)
    symbol               text NOT NULL,
    side                 text NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type           text NOT NULL CHECK (order_type IN ('LO', 'MP')),
    quantity             integer NOT NULL CHECK (quantity > 0),
    limit_price          numeric(14, 2) CHECK (limit_price > 0),
    status               text NOT NULL CHECK (status IN ('NEW', 'OPEN', 'FILLED', 'CANCELLED', 'EXPIRED', 'REJECTED')),
    reject_code          text,
    session_date         date NOT NULL,
    source               text NOT NULL DEFAULT 'MANUAL' CHECK (source IN ('MANUAL', 'STRATEGY')),  -- STRATEGY: R2
    strategy_version_id  uuid,
    reserved_cash        bigint NOT NULL DEFAULT 0 CHECK (reserved_cash >= 0),   -- LO mua đang OPEN
    reserved_qty         integer NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),   -- LO bán đang OPEN
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (account_id, client_order_id),
    CONSTRAINT orders_limit_price CHECK ((order_type = 'LO') = (limit_price IS NOT NULL)),
    CONSTRAINT orders_reject_code CHECK (status <> 'REJECTED' OR reject_code IS NOT NULL),
    CONSTRAINT orders_strategy CHECK ((source = 'STRATEGY') = (strategy_version_id IS NOT NULL))
);
CREATE INDEX paper_orders_open_by_symbol ON paper.orders (symbol) WHERE status = 'OPEN';
CREATE INDEX paper_orders_by_account ON paper.orders (account_id, created_at DESC);
CREATE TRIGGER paper_orders_touch BEFORE UPDATE ON paper.orders
    FOR EACH ROW EXECUTE FUNCTION util.touch_updated_at();

-- R1: mỗi lệnh khớp toàn bộ đúng một lần (FR-109), nên UNIQUE (order_id).
CREATE TABLE paper.fills (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     uuid NOT NULL UNIQUE REFERENCES paper.orders (id),
    quantity     integer NOT NULL CHECK (quantity > 0),
    price        numeric(14, 2) NOT NULL CHECK (price > 0),
    gross_value  bigint NOT NULL CHECK (gross_value > 0),
    fee          bigint NOT NULL CHECK (fee >= 0),
    tax          bigint NOT NULL CHECK (tax >= 0),
    trade_date   date NOT NULL,
    filled_at    timestamptz NOT NULL DEFAULT now()
);

-- Sổ cái chỉ ghi thêm (FR-110, ADR-013). amount có dấu: CASH tính bằng đồng, SECURITY tính bằng cổ phiếu.
CREATE TABLE paper.ledger_entries (
    id            bigserial PRIMARY KEY,
    account_id    uuid NOT NULL REFERENCES paper.accounts (id),
    entry_type    text NOT NULL CHECK (entry_type IN ('INITIAL_DEPOSIT', 'BUY_COST', 'SELL_PROCEEDS', 'FEE',
                                                      'TAX', 'BUY_SHARES', 'SELL_SHARES')),
    asset_type    text NOT NULL CHECK (asset_type IN ('CASH', 'SECURITY')),
    symbol        text,
    amount        bigint NOT NULL CHECK (amount <> 0),
    available_on  date NOT NULL,               -- BUY_SHARES: T+2 (FR-111); còn lại: ngày phát sinh
    fill_id       uuid REFERENCES paper.fills (id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ledger_symbol CHECK ((asset_type = 'SECURITY') = (symbol IS NOT NULL))
);
CREATE INDEX ledger_by_account_asset ON paper.ledger_entries (account_id, asset_type, symbol);
CREATE TRIGGER ledger_append_only BEFORE UPDATE OR DELETE ON paper.ledger_entries
    FOR EACH ROW EXECUTE FUNCTION util.forbid_mutation();

-- Projection vị thế, cập nhật trong cùng giao dịch với sổ cái; đối soát hằng ngày (NFR-A04).
CREATE TABLE paper.positions (
    account_id      uuid NOT NULL REFERENCES paper.accounts (id),
    symbol          text NOT NULL,
    quantity_total  bigint NOT NULL CHECK (quantity_total >= 0),
    avg_cost        numeric(18, 4) NOT NULL DEFAULT 0 CHECK (avg_cost >= 0),
    realized_pnl    bigint NOT NULL DEFAULT 0,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, symbol)
);

CREATE TABLE paper.reconciliation_runs (
    id                bigserial PRIMARY KEY,
    run_date          date NOT NULL,
    accounts_checked  integer NOT NULL,
    mismatches        integer NOT NULL,
    detail            jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- Tiền theo sổ cái (chưa trừ phần giữ chỗ của lệnh OPEN; ALG-10 trừ ở tầng ứng dụng).
CREATE VIEW paper.v_cash AS
SELECT account_id, sum(amount) AS cash
FROM paper.ledger_entries
WHERE asset_type = 'CASH'
GROUP BY account_id;

-- Chứng khoán khả dụng theo T+2 (FR-105, FR-111).
CREATE VIEW paper.v_shares AS
SELECT account_id,
       symbol,
       sum(amount) AS qty_total,
       sum(amount) FILTER (WHERE available_on <= (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) AS qty_available
FROM paper.ledger_entries
WHERE asset_type = 'SECURITY'
GROUP BY account_id, symbol;

-- =============================================================================
-- market (Analytics service)
-- =============================================================================

-- Danh mục mã (FR-020, FR-021). name_search = tên viết thường, bỏ dấu (kể cả đ → d); ứng dụng điền.
CREATE TABLE market.symbols (
    code           text PRIMARY KEY CHECK (code ~ '^[A-Z0-9]{2,20}$'),
    name           text NOT NULL,
    name_search    text NOT NULL,
    exchange       text NOT NULL CHECK (exchange IN ('HOSE', 'HNX', 'UPCOM', 'DERIV')),
    kind           text NOT NULL CHECK (kind IN ('STOCK', 'FUTURE', 'INDEX', 'ETF', 'CW')),
    industry_code  text,
    industry_name  text,
    lot_size       integer NOT NULL DEFAULT 100 CHECK (lot_size > 0),   -- BRU-004 (OQ-048)
    listed_date    date,
    delisted_date  date,
    expiry_date    date,                                               -- hợp đồng VN30F
    is_active      boolean NOT NULL DEFAULT true,
    source         text NOT NULL,
    updated_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX symbols_name_trgm ON market.symbols USING gin (name_search gin_trgm_ops);
CREATE INDEX symbols_exchange ON market.symbols (exchange) WHERE is_active;

CREATE TABLE market.index_memberships (
    index_code      text NOT NULL,             -- VN30, VN100, ...
    symbol          text NOT NULL REFERENCES market.symbols (code),
    effective_date  date NOT NULL,
    source          text NOT NULL,
    PRIMARY KEY (index_code, symbol, effective_date)
);

-- Lịch giao dịch (FR-024, ALG-01, ALG-11).
CREATE TABLE market.trading_calendar (
    trade_date      date PRIMARY KEY,
    is_trading_day  boolean NOT NULL,
    note            text
);

-- Nến ngày (FR-025, FR-028).
CREATE TABLE market.daily_bars (
    symbol         text NOT NULL REFERENCES market.symbols (code),
    trade_date     date NOT NULL,
    open           numeric(14, 2) NOT NULL,
    high           numeric(14, 2) NOT NULL,
    low            numeric(14, 2) NOT NULL,
    close          numeric(14, 2) NOT NULL,
    volume         bigint NOT NULL CHECK (volume >= 0),
    value          bigint CHECK (value >= 0),
    ref_price      numeric(14, 2),
    ceiling_price  numeric(14, 2),
    floor_price    numeric(14, 2),
    source         text NOT NULL,
    ingested_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, trade_date),
    CONSTRAINT bars_ohlc CHECK (low > 0 AND low <= open AND low <= close AND high >= open AND high >= close)
);
CREATE INDEX daily_bars_date ON market.daily_bars (trade_date);

-- Chỉ báo tính lúc đóng cửa (FR-051, FR-052) theo phiên bản bảng quy tắc.
CREATE TABLE market.indicator_snapshots (
    symbol            text NOT NULL,
    trade_date        date NOT NULL,
    rules_version     text NOT NULL,
    indicator_values  jsonb NOT NULL,          -- {"sma20": "...", "rsi14": "...", ...}; null nếu chưa đủ nến
    descriptions      jsonb NOT NULL,          -- ["RSI(14) ở vùng quá mua theo quy ước", ...]
    computed_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, trade_date),
    FOREIGN KEY (symbol, trade_date) REFERENCES market.daily_bars (symbol, trade_date)
);

-- Báo cáo tài chính (FR-026). fiscal_quarter = 0 cho kỳ năm.
CREATE TABLE market.financial_reports (
    symbol          text NOT NULL REFERENCES market.symbols (code),
    period_type     text NOT NULL CHECK (period_type IN ('Y', 'Q')),
    fiscal_year     smallint NOT NULL,
    fiscal_quarter  smallint NOT NULL CHECK (fiscal_quarter BETWEEN 0 AND 4),
    metrics         jsonb NOT NULL,
    source          text NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, period_type, fiscal_year, fiscal_quarter),
    CONSTRAINT fin_period CHECK ((period_type = 'Y') = (fiscal_quarter = 0))
);

-- Chỉ số cơ bản (FR-053).
CREATE TABLE market.ratios (
    symbol              text NOT NULL REFERENCES market.symbols (code),
    as_of               date NOT NULL,
    pe                  numeric(12, 4),
    pb                  numeric(12, 4),
    eps                 numeric(14, 2),
    roe                 numeric(8, 4),
    roa                 numeric(8, 4),
    debt_to_equity      numeric(10, 4),
    revenue_growth_yoy  numeric(10, 4),
    profit_growth_yoy   numeric(10, 4),
    source              text NOT NULL,
    computed_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, as_of)
);

-- Lần chạy job thu thập (FR-213, ST-07).
CREATE TABLE market.ingestion_runs (
    id           bigserial PRIMARY KEY,
    job          text NOT NULL,
    provider     text,
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    status       text NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'DEGRADED', 'FAILED')),
    records      integer,
    quarantined  integer,
    error        text
);
CREATE INDEX ingestion_runs_recent ON market.ingestion_runs (job, started_at DESC);

-- Bản ghi bị cách ly vì không đạt kiểm tra chất lượng (FR-031).
CREATE TABLE market.quarantine (
    id          bigserial PRIMARY KEY,
    dataset     text NOT NULL,
    provider    text NOT NULL,
    payload     jsonb NOT NULL,
    reason      text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- ai (Analytics service): FR-060 đến FR-074, ALG-07
-- =============================================================================

-- Mẫu prompt có phiên bản; không sửa được sau khi tạo (SDD 3.6.3).
CREATE TABLE ai.prompt_templates (
    id          serial PRIMARY KEY,
    name        text NOT NULL,               -- summary, chat
    version     integer NOT NULL,
    body        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);
CREATE TRIGGER prompt_templates_immutable BEFORE UPDATE OR DELETE ON ai.prompt_templates
    FOR EACH ROW EXECUTE FUNCTION util.forbid_mutation();

-- Nhật ký mỗi lần sinh nội dung (FR-071). user_ref = HMAC(user_secret, userId); không có email hay tên.
CREATE TABLE ai.interactions (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind               text NOT NULL CHECK (kind IN ('SUMMARY', 'CHAT')),
    user_ref           text,
    symbol             text,
    trade_date         date,
    question_redacted  text CHECK (length(question_redacted) <= 600),
    intent             text,
    facts              jsonb,
    facts_hash         text,
    template_id        integer REFERENCES ai.prompt_templates (id),
    provider           text,
    model              text,
    output             text,
    attempts           smallint NOT NULL DEFAULT 0,
    guard_numbers      text CHECK (guard_numbers IN ('PASS', 'FAIL', 'SKIPPED')),
    guard_reco         text CHECK (guard_reco IN ('PASS', 'FAIL', 'SKIPPED')),
    guard_profit       text CHECK (guard_profit IN ('PASS', 'FAIL', 'SKIPPED')),
    guard_reasons      jsonb,
    final_status       text NOT NULL CHECK (final_status IN ('PUBLISHED', 'FALLBACK', 'REFUSED')),
    latency_ms         integer,
    tokens_in          integer,
    tokens_out         integer,
    created_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT interactions_chat_user CHECK (kind = 'SUMMARY' OR user_ref IS NOT NULL)
);
CREATE INDEX ai_interactions_time ON ai.interactions (created_at);
CREATE INDEX ai_interactions_summary ON ai.interactions (symbol, trade_date) WHERE kind = 'SUMMARY';

-- Tóm tắt đã lưu: 1 bản mỗi (mã, ngày giao dịch, gói dữ kiện) (FR-060).
CREATE TABLE ai.summaries (
    symbol          text NOT NULL,
    trade_date      date NOT NULL,
    facts_hash      text NOT NULL,
    interaction_id  uuid NOT NULL REFERENCES ai.interactions (id),
    hidden          boolean NOT NULL DEFAULT false,   -- true khi rà soát kết luận VIOLATION (UC-015)
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, trade_date, facts_hash)
);

CREATE TABLE ai.feedback (
    id              bigserial PRIMARY KEY,
    interaction_id  uuid NOT NULL REFERENCES ai.interactions (id),
    user_ref        text NOT NULL,
    rating          smallint NOT NULL CHECK (rating IN (-1, 1)),
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (interaction_id, user_ref)
);

-- Hàng đợi rà soát (FR-073, FR-074, FR-212). reviewer_id là id quản trị viên phía Core
-- (không có khóa ngoại vì Analytics không có quyền đọc schema core).
CREATE TABLE ai.reviews (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id  uuid NOT NULL REFERENCES ai.interactions (id),
    source          text NOT NULL CHECK (source IN ('USER_REPORT', 'SAMPLE')),
    report_reason   text CHECK (length(report_reason) <= 500),
    verdict         text NOT NULL DEFAULT 'PENDING' CHECK (verdict IN ('PENDING', 'OK', 'VIOLATION')),
    reviewer_id     uuid,
    note            text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    reviewed_at     timestamptz
);
CREATE INDEX ai_reviews_queue ON ai.reviews (verdict, created_at);

-- =============================================================================
-- strategy (Core service, R2): FR-130 đến FR-133
-- =============================================================================

CREATE TABLE strategy.strategies (
    id                         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                    uuid NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    name                       text NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
    status                     text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE_PAPER', 'INACTIVE')),
    responsibility_accepted_at timestamptz NOT NULL,           -- FR-133, BRU-009
    created_at                 timestamptz NOT NULL DEFAULT now(),
    updated_at                 timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

-- Mỗi lần sửa tạo phiên bản mới; phiên bản không sửa được (FR-132).
CREATE TABLE strategy.strategy_versions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id     uuid NOT NULL REFERENCES strategy.strategies (id) ON DELETE CASCADE,
    version         integer NOT NULL CHECK (version > 0),
    schema_version  smallint NOT NULL,
    definition      jsonb NOT NULL,          -- lược đồ JSON có phiên bản (FR-131)
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (strategy_id, version)
);
CREATE TRIGGER strategy_versions_immutable BEFORE UPDATE ON strategy.strategy_versions
    FOR EACH ROW EXECUTE FUNCTION util.forbid_mutation();

-- =============================================================================
-- research (Analytics service, R2): FR-140 đến FR-145, ALG-14
-- =============================================================================

CREATE TABLE research.backtest_runs (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version_id  uuid NOT NULL,       -- tham chiếu strategy.strategy_versions (khác bên sở hữu, không FK)
    user_ref             text NOT NULL,
    symbols              text[] NOT NULL CHECK (cardinality(symbols) BETWEEN 1 AND 20),
    start_date           date NOT NULL,
    end_date             date NOT NULL,
    fee_rate             numeric(7, 6) NOT NULL,
    status               text NOT NULL DEFAULT 'QUEUED'
                         CHECK (status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')),
    metrics              jsonb,               -- total_return, max_drawdown, trades, win_rate, cagr
    nav_series           jsonb,
    error                text,
    created_at           timestamptz NOT NULL DEFAULT now(),
    started_at           timestamptz,
    finished_at          timestamptz,
    CONSTRAINT backtest_range CHECK (start_date < end_date)
);

CREATE TABLE research.backtest_trades (
    id           bigserial PRIMARY KEY,
    run_id       uuid NOT NULL REFERENCES research.backtest_runs (id) ON DELETE CASCADE,
    symbol       text NOT NULL,
    entry_date   date NOT NULL,
    entry_price  numeric(14, 2) NOT NULL,
    exit_date    date,
    exit_price   numeric(14, 2),
    quantity     integer NOT NULL CHECK (quantity > 0),
    net_pnl      bigint
);

-- =============================================================================
-- Phân quyền theo bên sở hữu (ADR-003)
-- =============================================================================

GRANT USAGE ON SCHEMA util TO core_rw, analytics_rw;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA util TO core_rw, analytics_rw;

GRANT USAGE ON SCHEMA core, paper, strategy TO core_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core, paper, strategy TO core_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core, paper, strategy TO core_rw;
GRANT USAGE ON SCHEMA market TO core_rw;
GRANT SELECT ON market.symbols, market.trading_calendar TO core_rw;

GRANT USAGE ON SCHEMA market, ai, research TO analytics_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA market, ai, research TO analytics_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA market, ai, research TO analytics_rw;
GRANT USAGE ON SCHEMA strategy TO analytics_rw;
GRANT SELECT ON strategy.strategy_versions TO analytics_rw;   -- R2: Analytics đọc định nghĩa chiến lược

-- Bảng tạo bởi migration sau này (migrator là owner) cũng được cấp quyền tự động.
ALTER DEFAULT PRIVILEGES IN SCHEMA core, paper, strategy
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO core_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA core, paper, strategy
    GRANT USAGE, SELECT ON SEQUENCES TO core_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA market, ai, research
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO analytics_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA market, ai, research
    GRANT USAGE, SELECT ON SEQUENCES TO analytics_rw;

-- =============================================================================
-- Dữ liệu khởi tạo
-- =============================================================================

-- FR-013: mục đích tùy chọn mặc định không đồng ý (không dùng ô đánh dấu sẵn).
INSERT INTO core.consent_purposes (code, description, required, default_granted) VALUES
    ('P1', 'Cung cấp dịch vụ cốt lõi (tài khoản, dữ liệu, phân tích, giả lập)', true,  true),
    ('P2', 'Gửi cảnh báo qua email và thông báo đẩy',                           false, false),
    ('P3', 'Phân tích dữ liệu sử dụng để cải tiến sản phẩm',                     false, false),
    ('P4', 'Gửi email tiếp thị',                                                false, false);

-- FR-214: tính năng nhạy cảm pháp lý mặc định tắt (BRD OQ-031).
INSERT INTO core.feature_flags (key, enabled, description) VALUES
    ('beta_invite_only', true, 'FR-019 (CR-02): đăng ký bắt buộc có mã mời trong beta kín'),
    ('market_regime', false, 'FR-045: trạng thái thị trường và hỗ trợ/kháng cự'),
    ('market_scores', false, 'FR-045: điểm rủi ro gãy xu hướng và sức mạnh hồi phục; chờ BRD OQ-031'),
    ('ai_summary',    true,  'FR-060: tóm tắt AI theo mã'),
    ('ai_chat',       true,  'FR-061: hỏi đáp AI');
