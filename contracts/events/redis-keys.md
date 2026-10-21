# Hợp đồng khóa Redis

Nguồn: Blueprint_SDD.md mục 3.5.3 (bảng gốc) bổ sung cột người đọc và TTL.
Giá trị số ghi dạng chuỗi thập phân. Mọi khóa giá có trường `ts` và `src` để Core
tự đánh giá độ cũ (FR-030).

| Khóa | Kiểu | Bên ghi | Bên đọc | Nội dung / TTL |
|---|---|---|---|---|
| `q:{SYMBOL}` | Hash | Analytics | Core | price, ref, ceil, floor, open, high, low, vol, val, chg, pct, ts (epoch ms), src, sess. TTL 1 ngày |
| `ob:{SYMBOL}` | Hash | Analytics | Core | Sổ lệnh: b1p, b1v … b3p, b3v, a1p … a3v, ts, src. TTL 60 s |
| `idx:{CODE}` | Hash | Analytics | Core | Điểm chỉ số. TTL 1 ngày |
| `mkt:session` | Hash | Analytics | Core | `HOSE`, `HNX`, `UPCOM`, `DERIV` → trạng thái phiên; `updated_at` |
| `ov:latest` | String (JSON) | Analytics | Core | Tổng quan (FR-040 đến FR-044). TTL 10 phút |
| `ov:treemap:{weight}:{dir}` | String (JSON) | Analytics | Core | Dữ liệu bản đồ nhiệt. TTL 10 phút |
| `s:quotes` | Stream | Analytics | Core (consumer group `core`) | `{cycle_id, ts, session, symbols}` (symbols nối bằng dấu phẩy), MAXLEN ~ 10.000 |
| `ai:quota:{userId}:{yyyymmdd}` | String (int) | Core | Core | Số câu hỏi đã dùng. TTL 48 giờ |
| `ai:budget:{provider}:{yyyymmdd}` | String (int) | Analytics | Analytics | Số request LLM đã dùng. TTL 48 giờ |
| `alert:st:{alertId}` | String (0/1) | Core | Core | Trạng thái điều kiện lần trước |
| `rl:{scope}:{key}` | String | Core, Analytics | Core, Analytics | Bộ đếm giới hạn tần suất |
| `sf:{hash}` | String | Analytics | Analytics | Khóa single-flight cho gộp truy vấn. TTL 10 s |

## Ghi chú vận hành

- `q:{SYMBOL}` và `ob:{SYMBOL}` là nguồn duy nhất cho giá nóng; Core không ghi đè.
- `s:quotes` dùng `XADD` với `MAXLEN ~ 10000`. Consumer group `core` được tạo bằng
  `XGROUP CREATE s:quotes core $ MKSTREAM`.
- Khóa `ai:quota:*` và `ai:budget:*` được đặt TTL 48 giờ để qua ngày theo giờ Việt Nam.
- Khi một khóa giá thiếu hoặc `ts` quá cũ, Core trả trạng thái fail-closed, không dùng 0.
