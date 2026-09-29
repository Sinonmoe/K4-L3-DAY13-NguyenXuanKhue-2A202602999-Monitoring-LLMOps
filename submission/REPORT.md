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

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Tất cả các trace được đẩy trực tiếp về project Langfuse riêng của tôi (`day13-k4-l3a-2A202602999`) qua API keys cấu hình trong `.env`. Trace metadata chứa thông tin định danh: `user_id_hash` (băm từ mã sinh viên 2A202602999), `session_id`, `environment: dev`, tags `["lab", feature, "claude-sonnet-4-5"]` và correlation ID tương ứng.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `lab-agent-run` (type `agent`), bao quát toàn bộ vòng đời của request.
  - Observation con 1: `retrieval` (type `retriever`), đo đạc bước tra cứu tài liệu với metadata `doc_count`, input và output sanitized.
  - Observation con 2: `generation` (type `generation`), đo bước gọi LLM (`FakeLLM`), nhận link prompt từ Langfuse, ghi nhận model, `usage_details` (input/output tokens) và `cost_details` (USD).
  - Cấu trúc cây quan hệ cha–con hiển thị rõ ràng trên trace waterfall, cho phép phân biệt chính xác khi xảy ra nghẽn ở bước retrieval (chậm >2.5s) hay generation.
- **Cách nối trace với log:** `correlation_id` được sinh từ middleware và gắn đồng thời vào `data/logs.jsonl` (qua structlog contextvars) và trace metadata trên Langfuse (qua `propagate_attributes(metadata={"correlation_id": correlation_id})`). Ta có thể copy correlation ID từ log line bất kỳ rồi dán vào ô tìm kiếm metadata trên Langfuse để mở đúng trace.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, gắn nhãn `baseline` và `production` ban đầu. Template: `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`.
- **Version/label candidate:** Version 2, gắn nhãn `candidate`. Template có tinh chỉnh: `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nTrả lời ngắn gọn, súc tích trong 2 câu.`
- **Trace ID của mỗi version:**
  - Trace ID dùng Version 1 (`production` / `baseline`): `<Dán trace ID từ Langfuse sau khi gửi request với label production/baseline>`
  - Trace ID dùng Version 2 (`candidate`): `<Dán trace ID từ Langfuse sau khi gửi request với label candidate>`
- **Cách promote và rollback `production`:**
  - **Promote:** Trên Langfuse Cloud, mở prompt `day13-chat` > chọn Version 2 > gán thêm nhãn `production` (chuyển nhãn từ v1 sang v2).
  - **Rollback:** Khi cần khôi phục lại bản cũ, mở danh sách versions của `day13-chat` > chọn lại Version 1 > gán nhãn `production` về Version 1. Ứng dụng tự động lấy đúng bản v1 trong lần gọi tiếp theo mà không cần sửa code hay redeploy.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đúng theo contract `config/dashboard.yaml` tại endpoint `/dashboard` (hoặc Streamlit), đọc từ `data/logs.jsonl` trong cửa sổ 60 phút và làm mới mỗi 30s:
  1. *Latency percentiles and TTFT* (ms): P50, P95, P99 và TTFT P95; threshold P95 &le; 3000 ms.
  2. *Request traffic* (requests_per_minute): số lượng request và tốc độ req/phút; threshold &ge; 1 req/min.
  3. *Error rate and retrieval success* (%): tỉ lệ lỗi, phân loại lỗi theo `error_type`, và tỉ lệ retrieval thành công (`tool_success == true`); threshold error rate &le; 2%.
  4. *Cost over time* (USD): tổng chi phí token trong cửa sổ thời gian; threshold &le; $2.50.
  5. *Input and output tokens* (tokens): tổng tokens nạp vào và tạo ra; threshold &le; 50,000 tokens.
  6. *Quality proxy* (score 0-1): điểm số chất lượng phản hồi trung bình; threshold &ge; 0.75.
- **SLO và lý do chọn:** Chọn `fast_successful_requests` với mục tiêu 99.5% requests đạt chuẩn (`event == "response_sent"` và `latency_ms <= 3000`) trong cửa sổ 28 ngày. Lý do chọn: Baseline bình thường đạt ~150ms. Ngưỡng 3000ms là ranh giới trải nghiệm người dùng đối với chat trợ lý LLM; nếu retrieval bị nghẽn (chẳng hạn incident `rag_slow` thêm 2500ms delay), latency sẽ lập tức chạm ngưỡng 3s để cảnh báo kịp thời trước khi timeout.
- **Cách tính error budget:**
  - Với SLO 99.5%, ngân sách lỗi (Error Budget) là `100% - 99.5% = 0.5%`.
  - Nếu hệ thống nhận 100,000 requests trong chu kỳ 28 ngày, Error Budget cho phép tối đa `100,000 * 0.5% = 500` bad requests (requests bị lỗi 500 hoặc có latency > 3000ms).
  - Khi số bad requests vượt quá 500, ngân sách lỗi cạn kiệt (Burn rate cao), kích hoạt chính sách đóng băng deploy tính năng mới để tập trung khắc phục sự cố.
- **Ba alert và runbook tương ứng:**
  1. `HighTailLatency`: Severity critical, duration 5m, condition `p95(latency_ms) > 3000ms`, channel `#alerts-llmops`, owner `oncall-backend`, runbook `docs/alerts.md#alert-1`.
  2. `HighErrorRate`: Severity critical, duration 3m, condition `error_rate_pct > 2%`, channel `#alerts-llmops`, owner `oncall-backend`, runbook `docs/alerts.md#alert-2`.
  3. `LowRetrievalSuccess`: Severity warning, duration 5m, condition `retrieval_success_rate_pct < 90%`, channel `#alerts-rag`, owner `oncall-rag`, runbook `docs/alerts.md#alert-3`.

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
