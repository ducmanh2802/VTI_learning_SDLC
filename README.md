# VN Stock AI Pro

VN Stock AI Pro là nền tảng công cụ phân tích chứng khoán Việt Nam: dữ liệu cổ phiếu HOSE/HNX/UPCoM và VN30F, tổng quan thị trường, phân tích mã (chỉ báo kỹ thuật, chỉ số cơ bản), trợ lý AI tiếng Việt chỉ diễn đạt số liệu do hệ thống tính và không tư vấn đầu tư, danh sách theo dõi, cảnh báo giá, và giao dịch giả lập có RiskGuard và sổ cái. R1 là beta kín, chi phí 0 đồng.

## Tài liệu

- [BRD](docs/requirements/BRD.md)
- [SRS](docs/requirements/SRS.md)
- [Blueprint SDD](docs/design/Blueprint_SDD.md)
- [Work packages](docs/workpackages/)
- [AGENTS.md](AGENTS.md): quy tắc cho coding agent

## Bắt đầu với hạ tầng dev

```powershell
Copy-Item infra/.env.example infra/.env
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --wait
docker compose -f infra/docker-compose.yml --env-file infra/.env ps
```

Trên Linux/macOS, thay `Copy-Item` bằng `cp`. Đổi mật khẩu trong `infra/.env` trước khi dùng; file này bị git bỏ qua. Lệnh dừng: `docker compose -f infra/docker-compose.yml --env-file infra/.env down`. Chi tiết ở [infra/README.md](infra/README.md).

## Quy trình

Claude viết brief cho từng WP và audit kết quả; coding agent thực hiện WP trên nhánh riêng, chạy các lệnh kiểm tra, viết báo cáo rồi mở pull request; founder merge. Xem [AGENTS.md](AGENTS.md) và [Blueprint_SDD.md mục 7](docs/design/Blueprint_SDD.md).
