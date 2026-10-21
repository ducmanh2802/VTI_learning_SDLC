# Gói công việc (Work Packages)

Mỗi gói công việc (WP) là một việc nhỏ giao cho AI coding agent (OpenCode, Antigravity, Cline). Phân công theo phase và prompt giao việc nằm ở [ASSIGNMENTS.md](ASSIGNMENTS.md). Quy trình (Blueprint_SDD.md mục 7):

1. Claude viết brief `WP-xx.md`.
2. Agent thực hiện trên nhánh `wp-xx-...`, ghi báo cáo vào `reports/WP-xx.md`, mở pull request.
3. Claude audit theo checklist A1–A10 và trả về `PASS` hoặc `FIX`.
4. Founder merge.

Quy tắc chung cho agent nằm ở [AGENTS.md](../../AGENTS.md). Danh sách đầy đủ 25 WP của R1 nằm ở [Blueprint_SDD.md mục 7.7](../design/Blueprint_SDD.md).

## Trạng thái

| WP | Tên | Brief | Trạng thái |
|---|---|---|---|
| WP-00 | Khung repo, hạ tầng dev, CI cơ bản | [WP-00.md](WP-00.md) | **PASS**, đã merge vào `integration/r1` ([audit](reports/WP-00-audit.md)) |
| WP-01 | Migration baseline, migrator, role dịch vụ | [WP-01.md](WP-01.md) | **PASS**, đã merge ([audit](reports/WP-01-audit.md)); CI xanh trên `integration/r1` |
| WP-02 | Hợp đồng OpenAPI và sự kiện | [WP-02.md](WP-02.md) | **PASS** sau 3 sửa của audit, đã merge ([audit](reports/WP-02-audit.md)) |
| WP-03 | Khung Core (Spring Boot 4) | [WP-03.md](WP-03.md) | Đang giao (OpenCode) |
| WP-04 | Identity | [WP-04.md](WP-04.md) | Chờ WP-03 |
| WP-05 | Consent | [WP-05.md](WP-05.md) | Chờ WP-04 |
| WP-06 | Admin | [WP-06.md](WP-06.md) | Chờ WP-04 |
| WP-07 | Khung Analytics | [WP-07.md](WP-07.md) | **PASS** sau 5 sửa của audit, đã merge ([audit](reports/WP-07-audit.md)) |
| WP-08 | Nguồn dữ liệu vnstock | [WP-08.md](WP-08.md) | Sẵn sàng; xếp hàng cho Cline sau WP-11 |
| WP-09 | Failover nguồn | [WP-09.md](WP-09.md) | Chờ WP-08 |
| WP-10 | Thu thập dữ liệu | [WP-10.md](WP-10.md) | Chờ WP-09 |
| WP-11 | Chỉ báo kỹ thuật | [WP-11.md](WP-11.md) | Đang giao (Cline) |
| WP-12 | Tổng quan thị trường | [WP-12.md](WP-12.md) | Chờ WP-10, WP-11 |
| WP-14 | Cổng LLM | [WP-14.md](WP-14.md) | Sẵn sàng; xếp hàng cho OpenCode sau WP-03 |
| WP-15 | Guardrails AI | [WP-15.md](WP-15.md) | Đang giao (Antigravity) |
| WP-12b | Trạng thái thị trường, hỗ trợ/kháng cự | — | Hoãn: chờ ngưỡng từ dự án cũ (OQ-054); tính năng có cờ, mặc định tắt |
| WP-13a | API thị trường nội bộ (Analytics) | [WP-13a.md](WP-13a.md) | Chờ WP-10 đến WP-12 |
| WP-13b | Core: quotes + marketgw | [WP-13b.md](WP-13b.md) | Chờ WP-03 |
| WP-16a | Pipeline AI (Analytics) | [WP-16a.md](WP-16a.md) | Chờ WP-11, WP-13a, WP-14, WP-15 |
| WP-16b | AI ở Core (quota, userRef) | [WP-16b.md](WP-16b.md) | Chờ WP-13b, WP-06 |
| WP-17 | Danh sách theo dõi | [WP-17.md](WP-17.md) | Chờ WP-13b, WP-05 |
| WP-18 | Cảnh báo và thông báo | [WP-18.md](WP-18.md) | Chờ WP-13b, WP-05 |
| WP-19 | Giả lập và RiskGuard | [WP-19.md](WP-19.md) | Chờ WP-13b, WP-05 |
| WP-20a | Web: khung, xác thực | [WP-20a.md](WP-20a.md) | Chờ WP-04, WP-05 |
| WP-20b | Web: thị trường, mã | [WP-20b.md](WP-20b.md) | Chờ WP-20a |
| WP-20c | Web: AI, theo dõi, cảnh báo | [WP-20c.md](WP-20c.md) | Chờ WP-20b |
| WP-20d | Web: giả lập | [WP-20d.md](WP-20d.md) | Chờ WP-20b |
| WP-20e | Web: tài khoản, quản trị | [WP-20e.md](WP-20e.md) | Chờ WP-20a |
| WP-21 | Mobile (Expo) | [WP-21.md](WP-21.md) | Chờ WP-20a đến WP-20d |
| WP-22 | Hạ tầng production | [WP-22.md](WP-22.md) | Chờ WP-03, WP-07, WP-20a |
| WP-23 | Telemetry, hỗ trợ, chỉ số | [WP-23.md](WP-23.md) | Chờ WP-05, WP-06, WP-16b |
| WP-24 | Kiểm thử phát hành R1 | [WP-24.md](WP-24.md) | Sau cùng |

Nhánh tích hợp: mọi WP được tạo từ `integration/r1`. WP nào đạt audit thì được merge vào `integration/r1`. Founder merge `integration/r1` vào `main` khi muốn.

## Cách chạy WP-00 với OpenCode

**Chuẩn bị (làm một lần):**

1. Merge nhánh `docs/brd-srs-blueprint` vào `main`, để `AGENTS.md` và thư mục `docs/` có trên `main`.
2. Bật Docker Desktop. Các lệnh kiểm tra của WP-00 cần Docker.
3. Cài OpenCode theo hướng dẫn tại opencode.ai/docs, rồi chọn một model miễn phí (lệnh `/models` trong OpenCode). Danh sách model miễn phí thay đổi thường xuyên.
4. (Tùy chọn) Cài và đăng nhập GitHub CLI (`gh auth login`) để agent tự mở pull request.

**Giao việc:**

1. Mở terminal ở thư mục gốc repo, chạy `git switch main && git pull`.
2. Chạy `opencode`. OpenCode tự đọc `AGENTS.md` ở thư mục gốc làm quy tắc dự án.
3. Dán prompt sau:

   ```text
   Read AGENTS.md and docs/workpackages/WP-00.md. Execute WP-00 exactly as written,
   on a new branch wp-00-repo-skeleton created from main. Run every acceptance
   command, write the report to docs/workpackages/reports/WP-00.md, push the branch
   and open a pull request. Do not modify files outside the WP scope.
   ```

4. Khi agent báo xong, gửi cho Claude: "audit WP-00" kèm link pull request (hoặc tên nhánh).
