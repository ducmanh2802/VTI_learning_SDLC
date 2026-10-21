# db/migrations

Migration Flyway cho toàn bộ schema của hệ thống. `V1__baseline.sql` là bản sao nguyên văn của
[schema.sql](../../docs/design/schema.sql); mọi thay đổi schema sau này phải nằm trong file migration mới.

## Quy tắc

- Tên file: `V<n>__<snake_case>.sql`, ví dụ `V2__add_price_alerts.sql`. Số `<n>` tăng dần, không trùng.
- Không bao giờ sửa migration đã áp dụng (đã chạy ở bất kỳ môi trường nào); hãy tạo migration mới.
- Không đổi tên hay xóa migration đã áp dụng. Flyway kiểm tra checksum và sẽ dừng nếu file bị sửa.
- Chỉ dùng cú pháp PostgreSQL 16 và giữ tính idempotent ở mức hợp lý (ví dụ `IF NOT EXISTS` cho index).

## Chạy migration

Từ thư mục gốc repo, sau khi đã tạo `infra/.env`:

```powershell
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --wait postgres
docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm migrator
```

Service `migrator` dùng image `flyway/flyway:11.13.3` (Flyway Community, miễn phí) và mount thư mục này
vào `/flyway/sql` chỉ đọc. Chạy lại lệnh trên là an toàn: Flyway chỉ áp dụng migration còn thiếu.

Xem [Blueprint_SDD.md](../../docs/design/Blueprint_SDD.md) mục 3.5 và [schema.sql](../../docs/design/schema.sql).
