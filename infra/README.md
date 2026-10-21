# infra

Hạ tầng phát triển: `docker-compose.yml` khởi động PostgreSQL 16 và Redis 7 (healthy, chỉ mở cổng trên localhost) cùng file env mẫu. Cấu hình production, Caddy, backup và runbook thuộc WP-22. Xem [Blueprint_SDD.md](../docs/design/Blueprint_SDD.md) mục 3.10 (tài nguyên container) và mục 7.3 (cấu trúc repo).

## Chuẩn bị

Từ thư mục gốc repo, tạo file env cục bộ rồi đổi mật khẩu trong đó (file `infra/.env` bị git bỏ qua):

```powershell
Copy-Item infra/.env.example infra/.env
```

Trên Linux/macOS, dùng `cp infra/.env.example infra/.env`.

## Lệnh

Chạy từ thư mục gốc repo:

```powershell
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --wait
docker compose -f infra/docker-compose.yml --env-file infra/.env ps
docker compose -f infra/docker-compose.yml --env-file infra/.env down
```

Thêm `-v` vào lệnh `down` để xóa luôn volume dữ liệu dev.

## Biến môi trường

`infra/.env.example` là mẫu đầy đủ. Ngoài `POSTGRES_*` và `REDIS_*`, file env còn có:

- `CORE_DB_PASSWORD`: mật khẩu của login role `core_svc` (Core chỉ ghi schema `core`, `paper`, `strategy`).
- `ANALYTICS_DB_PASSWORD`: mật khẩu của login role `analytics_svc` (Analytics chỉ ghi schema `market`, `ai`, `research`).

Hai biến này được `infra/postgres/initdb/10-service-roles.sh` dùng một lần khi volume Postgres được tạo lần đầu.
Script tạo các group role `core_rw`, `analytics_rw` (NOLOGIN) và các login role `core_svc`, `analytics_svc`.
Đổi mật khẩu trong `.env` sau khi volume đã tồn tại **không** tự cập nhật role; phải xóa volume (`down -v`) hoặc
`ALTER ROLE` thủ công.

## Migration

Service `migrator` dùng Flyway Community và chỉ chạy khi được gọi qua profile `tools`:

```powershell
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm migrator
```

Migration nằm trong `db/migrations`; xem [db/migrations/README.md](../db/migrations/README.md) để biết quy tắc đặt tên.

## Kết nối

Dùng cổng localhost và mật khẩu trong `infra/.env`:

```powershell
$env:PGPASSWORD = "change-me-postgres"
psql -h 127.0.0.1 -p 5432 -U vnstockai -d vnstockai

$env:REDISCLI_AUTH = "change-me-redis"
redis-cli -h 127.0.0.1 -p 6379 ping
```

Hoặc chạy công cụ trong container:

```powershell
docker compose -f infra/docker-compose.yml --env-file infra/.env exec postgres pg_isready -U vnstockai -d vnstockai
docker compose -f infra/docker-compose.yml --env-file infra/.env exec redis redis-cli ping
```

Ảnh `postgres:16-alpine` và `redis:7-alpine` hỗ trợ đa kiến trúc ARM64/AMD64 (NFR-D01).
