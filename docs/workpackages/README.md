# Gói công việc (Work Packages)

Mỗi gói công việc (WP) là một việc nhỏ giao cho AI coding agent (OpenCode dùng model miễn phí). Quy trình (Blueprint_SDD.md mục 7):

1. Claude viết brief `WP-xx.md`.
2. Agent thực hiện trên nhánh `wp-xx-...`, ghi báo cáo vào `reports/WP-xx.md`, mở pull request.
3. Claude audit theo checklist A1–A10 và trả về `PASS` hoặc `FIX`.
4. Founder merge.

Quy tắc chung cho agent nằm ở [AGENTS.md](../../AGENTS.md). Danh sách đầy đủ 25 WP của R1 nằm ở [Blueprint_SDD.md mục 7.7](../design/Blueprint_SDD.md).

## Trạng thái

| WP | Tên | Brief | Trạng thái |
|---|---|---|---|
| WP-00 | Khung repo, hạ tầng dev, CI cơ bản | [WP-00.md](WP-00.md) | **PASS**, đã merge vào `integration/r1` ([audit](reports/WP-00-audit.md)) |
| WP-01 | Migration baseline, migrator, role dịch vụ | [WP-01.md](WP-01.md) | Đang giao |
| WP-02 | Hợp đồng OpenAPI và sự kiện | [WP-02.md](WP-02.md) | Đang giao |

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
