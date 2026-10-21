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
