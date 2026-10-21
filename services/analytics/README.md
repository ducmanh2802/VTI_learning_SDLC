# services/analytics

Dịch vụ Analytics (Python 3.12 + FastAPI, quản lý bằng `uv`): dữ liệu thị trường, định lượng và AI; chỉ nhận gọi nội bộ.
Xem [Blueprint_SDD.md](../../docs/design/Blueprint_SDD.md) mục 3.2 (DE-05), 3.4.2 (luật phụ thuộc tầng) và 7.3.

## Bố cục

```text
src/analytics/
  api/          router nội bộ /internal/v1, xác thực token dịch vụ, lỗi RFC 9457
  ingestion/    tiến trình scheduler (APScheduler)
  ai/           gói dữ kiện, cổng LLM, guardrails (R2+)
  research/     backtest, chiến lược trực tiếp (R2)
  quant/        hàm thuần: chỉ báo, mô tả theo quy tắc, độ rộng, top movers
  fundamentals/ chỉ số tài chính từ báo cáo
  marketdata/   mô hình chuẩn hóa, repository, kiểm tra chất lượng
  providers/    port và adapter nguồn dữ liệu (SC-010)
  common/       settings, log JSON, thời gian, tiền, mã lỗi, probe sẵn sàng
```

Quy tắc phụ thuộc được kiểm tra bằng import-linter (`uv run lint-imports`):

```text
api → ingestion | ai | research → quant | fundamentals → marketdata | providers → common
```

`analytics.quant` và `analytics.ai.guardrails` là mã thuần: không mạng, không CSDL, không Redis.

## Lệnh

Chạy từ `services/analytics`:

| Lệnh | Mục đích |
|---|---|
| `uv sync` | cài dependency theo `uv.lock` |
| `uv run ruff check .` | lint |
| `uv run ruff format --check .` | kiểm tra định dạng |
| `uv run mypy --strict src` | kiểm tra kiểu |
| `uv run lint-imports` | kiểm tra luật phụ thuộc tầng |
| `uv run pytest --cov=analytics --cov-report=term` | chạy test |
| `uv run uvicorn analytics.api.main:app --reload` | chạy API nội bộ ở chế độ dev |
| `uv run python -m analytics.ingestion.scheduler` | chạy tiến trình scheduler |

## Biến môi trường

| Biến | Bắt buộc | Mặc định | Ý nghĩa |
|---|---|---|---|
| `ANALYTICS_DB_URL` | không | `postgresql+asyncpg://analytics_svc:...@postgres:5432/vnstockai` | URL Postgres (schema `market`, `ai`, `research`) |
| `REDIS_URL` | không | `redis://:...@redis:6379/0` | URL Redis |
| `SERVICE_TOKEN` | **có** | – | bí mật dùng chung, tối thiểu 32 ký tự |
| `LOG_LEVEL` | không | `INFO` | mức log của tiến trình |
| `ENV` | không | `dev` | `dev`, `test` hoặc `prod`; chỉ `test` mới bật route thử nghiệm |

## Endpoint nội bộ

| Method | Đường dẫn | Xác thực | Mô tả |
|---|---|---|---|
| GET | `/internal/v1/health/live` | không | tiến trình còn sống |
| GET | `/internal/v1/health/ready` | không | Postgres và Redis còn trả lời trong 2 giây |
| GET | `/internal/v1/_auth-probe` | `X-Service-Token` | route thử nghiệm, chỉ tồn tại khi `ENV=test` |

Mọi lỗi trả về `application/problem+json` theo RFC 9457 với mã ổn định (`code`), ví dụ
`UNAUTHENTICATED`, `VALIDATION_ERROR`, `DATA_STALE`, `INTERNAL_ERROR`.

## Sinh model từ hợp đồng

Model pydantic được sinh từ `contracts/openapi/dist/internal.yaml` (file đã bundle của WP-02) vào
`src/analytics/api/models_generated.py`. File sinh ra được commit; CI sinh lại và so sánh.

```powershell
# PowerShell
pwsh ./scripts/gen_models.ps1
```

```bash
# bash
./scripts/gen_models.sh
```

Lệnh `datamodel-codegen` tương đương:

```bash
uv run datamodel-codegen \
  --input ../../contracts/openapi/dist/internal.yaml \
  --input-file-type openapi \
  --output src/analytics/api/models_generated.py \
  --output-model-type pydantic_v2.BaseModel \
  --target-python-version 3.12 \
  --snake-case-field \
  --allow-population-by-field-name \
  --use-annotated \
  --use-standard-collections \
  --use-union-operator \
  --use-double-quotes \
  --keep-model-order \
  --disable-timestamp \
  --formatters ruff-format ruff-check
```

## Chạy bằng Docker

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env --profile app up -d --build analytics analytics-scheduler
```

API lắng nghe ở `127.0.0.1:8090` (chỉ trong dev), scheduler chạy tiến trình riêng để không chạy trùng job.
