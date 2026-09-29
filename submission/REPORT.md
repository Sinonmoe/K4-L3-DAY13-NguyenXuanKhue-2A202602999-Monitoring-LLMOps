# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Xuân Khuê
- **MSSV:** 2A202602999
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/Sinonmoe/K4-L3-DAY13-NguyenXuanKhue-2A202602999-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602999`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` |30/100 | | |
| `validate_dashboard.py` |6/6 panel hợp lệ | | |
| `pytest` |22/22 passed | | |
| Số traces hợp lệ |0 trace | | |
| Số PII leak |0 leak | | |
| Latency P95 / TTFT P95 |151 ms / 50 ms | | |
| Retrieval success rate |100% (10/10) | | |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), mỗi request được gọi `clear_contextvars()` để xóa context cũ. Sau đó kiểm tra header `x-request-id`, nếu có thì sử dụng lại, nếu không thì sinh mới theo format `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`). ID này được gắn vào `bind_contextvars(correlation_id=correlation_id)` cho structlog, gán vào `request.state.correlation_id` cho handler, và trả lại qua header `x-request-id` cùng `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Các trường chuẩn theo schema gồm `ts` (UTC ISO), `level`, `service`, `event`, `correlation_id`. Trong endpoint `/chat` (`app/main.py`), các trường ngữ cảnh được bind trước khi ghi log gồm `user_id_hash` (SHA256 12 ký tự), `session_id`, `feature`, `model`, `env`. Khi kết thúc request bổ sung thêm: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, và `payload` đã được che PII.
- **Cách bảo đảm PII được scrub trước khi ghi:** Xây dựng các regex chuẩn hóa trong `app/pii.py` cho `email`, `phone_vn`, `credit_card`, `cccd` và thay thế bằng `[REDACTED_<TYPE>]`. Đăng ký `scrub_event` như một structlog processor đệ quy chạy trước `JsonlFileProcessor()` và `JSONRenderer()`, đảm bảo mọi trường dữ liệu string hoặc cấu trúc lồng nhau trong event dict đều được che sạch trước khi ghi ra file `data/logs.jsonl` hoặc stdout.
- **Cách kiểm chứng kết quả:** Bộ unit test `tests/test_pii.py` kiểm tra đầy đủ cả 4 mẫu PII đều pass; kiểm tra thực tế bằng `python scripts/validate_logs.py` đạt 100/100 điểm với 0 missing required, 0 missing enrichment, 0 PII leak detected và correlation IDs được truyền chuẩn xác qua các log records.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
