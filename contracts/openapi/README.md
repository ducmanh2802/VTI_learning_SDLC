# contracts/openapi

Hợp đồng OpenAPI 3.1 cho API công khai (`public.yaml`) và nội bộ (`internal.yaml`).
Được tạo ở WP-02. Xem [Blueprint_SDD.md](../../docs/design/Blueprint_SDD.md) mục 3.6.

## Cấu trúc

- `public.yaml` / `internal.yaml`: root, chỉ chứa `openapi`, `info`, `servers`, `tags`,
  `securitySchemes`, `security` và `paths` (mỗi path là một `$ref`).
- `public/paths/`, `internal/paths/`: một Path Item mỗi file.
- `public/schemas/`, `internal/schemas/`: một schema mỗi file.
- `public/responses/`, `internal/responses/`: response lỗi dùng chung.
- `public/parameters/`, `internal/parameters/`: tham số dùng chung.
- `dist/`: bản bundle một file dùng cho sinh mã ở WP-03 và WP-07. **Không sửa tay.**

## Lệnh

```bash
npx --yes @redocly/cli@1 lint --config contracts/openapi/redocly.yaml
npx --yes @redocly/cli@1 bundle public --config contracts/openapi/redocly.yaml -o contracts/openapi/dist/public.yaml
npx --yes @redocly/cli@1 bundle internal --config contracts/openapi/redocly.yaml -o contracts/openapi/dist/internal.yaml
```

Sau mọi thay đổi hợp đồng, chạy lint, bundle lại `dist/` và commit cả hai file.
