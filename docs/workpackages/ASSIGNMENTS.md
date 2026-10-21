# Phân việc cho agent (R1)

Claude lập kế hoạch, giao từng WP, audit và merge. Ba agent viết code, mỗi agent làm **một WP một lúc** trong worktree riêng. Trạng thái chi tiết từng WP nằm ở [README.md](README.md).

## Agent và chỗ làm việc

| Agent | Cách chạy | Model | Worktree (thư mục cạnh repo) | Hợp với |
|---|---|---|---|---|
| OpenCode | CLI không cần giao diện, script `run-wp.ps1` của Claude | Model miễn phí của OpenCode (deepseek, minimax…) | `VTI_learning_SDLC-wp02`, `VTI_learning_SDLC-wp00` | Khung dự án, backend Java/Python có brief chi tiết |
| Antigravity | Agent Manager trong Antigravity (hoặc CLI `agy`) | Gemini 3.8 Flash (High) hoặc Claude Sonnet 4.6 | `VTI_learning_SDLC-antigravity` | Việc nhạy cảm: bảo mật, tiền, AI, nhiều nội dung tiếng Việt |
| Cline | Extension Cline trong VS Code | Model miễn phí do founder chọn | `VTI_learning_SDLC-cline` | Hàm thuần có số liệu kiểm chứng, việc vừa và nhỏ |

Mỗi worktree có `infra/.env` riêng (không commit), với tên project Docker và cổng riêng, để các agent không tắt container của nhau:

| Worktree | `COMPOSE_PROJECT_NAME` | Postgres | Redis | Analytics |
|---|---|---|---|---|
| `VTI_learning_SDLC-wp00` | `vnstockai` | 5432 | 6379 | 8090 |
| `VTI_learning_SDLC-wp02` | `vnstockai-wp03` | 15432 | 16379 | 8090 |
| `VTI_learning_SDLC-antigravity` | `vnstockai-ag` | 25432 | 26379 | 28090 |
| `VTI_learning_SDLC-cline` | `vnstockai-cline` | 35432 | 36379 | 38090 |

## Phase và phân công

Cột "Agent" của các phase sau là dự kiến. Claude đổi theo chất lượng thực tế của từng agent.

### Phase 1: Nền tảng

| WP | Agent | Trạng thái |
|---|---|---|
| WP-00, WP-01, WP-02, WP-07 | OpenCode | PASS, đã merge |
| WP-03 Khung Core | OpenCode (deepseek) | Đang làm |

### Phase 2: Dịch vụ lõi

| WP | Agent | Trạng thái |
|---|---|---|
| WP-15 Guardrails AI | Antigravity | **Đang giao** (nhánh `wp-15-ai-guardrails`) |
| WP-11 Chỉ báo kỹ thuật | Cline | **Đang giao** (nhánh `wp-11-quant-indicators`) |
| WP-14 Cổng LLM | OpenCode | Chờ OpenCode xong WP-03 |
| WP-04 Identity | Antigravity | Chờ WP-03 và Antigravity xong WP-15 |
| WP-08 Nguồn vnstock | Cline | Chờ Cline xong WP-11 |

### Phase 3: Dữ liệu và miền nghiệp vụ

| WP | Agent dự kiến |
|---|---|
| WP-05 Consent | Antigravity |
| WP-06 Admin | OpenCode |
| WP-09 Failover nguồn | Cline |
| WP-10 Thu thập dữ liệu | OpenCode |
| WP-12 Tổng quan thị trường | Cline |
| WP-13a API thị trường nội bộ | OpenCode |
| WP-13b Core: quotes + marketgw | OpenCode |

### Phase 4: Tính năng

| WP | Agent dự kiến |
|---|---|
| WP-16a Pipeline AI | Antigravity |
| WP-16b AI ở Core | OpenCode |
| WP-17 Danh sách theo dõi | Cline |
| WP-18 Cảnh báo và thông báo | OpenCode |
| WP-19 Giả lập và RiskGuard | Antigravity |

### Phase 5: Giao diện

| WP | Agent dự kiến |
|---|---|
| WP-20a Web: khung, xác thực | Antigravity |
| WP-20b, WP-20d | Cline |
| WP-20c, WP-20e | OpenCode |
| WP-21 Mobile | Antigravity |

### Phase 6: Vận hành và phát hành

| WP | Agent dự kiến |
|---|---|
| WP-22 Hạ tầng production | OpenCode |
| WP-23 Telemetry, hỗ trợ, chỉ số | Cline |
| WP-24 Kiểm thử phát hành | Antigravity, Claude kiểm tra từng cổng |

## Quy trình mỗi WP

1. Claude tạo nhánh `wp-xx-...` từ `integration/r1` trong worktree của agent, rồi ghi WP vào bảng trên.
2. Agent làm theo prompt bên dưới và **commit báo cáo `docs/workpackages/reports/WP-xx.md`**. Commit báo cáo là tín hiệu đã xong: Claude theo dõi nhánh và tự audit khi thấy nó.
3. Claude audit (A1–A10, chạy lại các lệnh kiểm tra), sửa lỗi nhỏ hoặc trả về agent, ghi `reports/WP-xx-audit.md`, rồi merge vào `integration/r1` và push.
4. Claude giao WP tiếp theo trong hàng đợi của agent đó.

**Cuối mỗi phase:** Claude push `integration/r1` và gắn tag `r1-phase-<n>`. Founder merge `integration/r1` vào `main` khi muốn.

## Cách giao việc cho Antigravity và Cline

**Antigravity:** File → Open Folder → chọn `D:\VTI\Projects\VTI_learning_SDLC-antigravity`. Mở Agent Manager, chọn model, dán prompt.

**Cline:** mở một cửa sổ VS Code mới ở `D:\VTI\Projects\VTI_learning_SDLC-cline`. Mở Cline, chọn model miễn phí, dán prompt.

Agent trong IDE hỏi quyền trước khi chạy lệnh, theo cài đặt duyệt tự động của từng công cụ. Nếu không ngồi ở máy, bật duyệt tự động cho lệnh đọc/ghi file và terminal. Prompt đã cấm push, đổi git config và lệnh phá hủy.

## Prompt giao việc

Thay `<WP>`, `<BRANCH>` và `<WORKTREE>`:

```text
You are a coding agent working in the git worktree <WORKTREE>. The branch <BRANCH> is already checked out from integration/r1, which contains AGENTS.md, docs/ and every merged work package.

Read AGENTS.md fully, then docs/workpackages/<WP>.md, then execute <WP> exactly as written.

Rules for this run:
1. Stay on <BRANCH>. Do not create or switch branches, do not push, do not open a pull request. Commit locally; the reviewer pushes after the audit.
2. The machine is Windows 10 with PowerShell 5.1. Docker Desktop is running. uv is in C:\Users\Windows\AppData\Roaming\Python\Python315\Scripts (add that folder to PATH if `uv` is not found). Node and npx are installed.
3. infra/.env already exists in this worktree with its own COMPOSE_PROJECT_NAME and ports. Always pass --env-file infra/.env. Never stop or remove containers, volumes or networks of other compose projects, and never run docker system prune or docker volume prune. Never commit infra/.env. If you add a variable, add it to infra/.env.example and append it to infra/.env.
4. Never modify files outside the WP scope. Never change git config. Never run destructive commands (git reset --hard, git clean, rm -rf, Remove-Item -Recurse) outside this worktree.
5. Never write a single file longer than about 300 lines; split it.
6. Run every acceptance command and paste the key output in the report. Mark CI-only items "pending CI".
7. Finish by writing docs/workpackages/reports/<WP>.md with the template in AGENTS.md section 11, and commit it. That commit tells the reviewer you are done.
```

### Prompt đang giao

| Agent | `<WP>` | `<BRANCH>` | `<WORKTREE>` |
|---|---|---|---|
| Antigravity | `WP-15` | `wp-15-ai-guardrails` | `D:\VTI\Projects\VTI_learning_SDLC-antigravity` |
| Cline | `WP-11` | `wp-11-quant-indicators` | `D:\VTI\Projects\VTI_learning_SDLC-cline` |
