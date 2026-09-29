# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighTailLatency
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack (#alerts-llmops)
- SLI/SLO liên quan: `primary_slo.fast_successful_requests` (Latency P95 <= 3000ms)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` duy trì liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Trải nghiệm người dùng bị chậm nghiêm trọng, thời gian phản hồi vượt quá kỳ vọng, có nguy cơ timeout client.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel **Latency** trên Dashboard để xác định xu hướng P95, P99 và TTFT.
  2. Lọc `data/logs.jsonl` tìm correlation ID của các request có `latency_ms > 3000`.
  3. Mở trace trên Langfuse theo correlation ID, kiểm tra waterfall xem span `retrieval` hay span `generation` bị chậm (ví dụ do sự cố `rag_slow`).
- Mitigation tạm thời: Bật cache cho retrieval, giảm timeout của vector store xuống 1500ms hoặc bypass retrieval nếu upstream quá tải.
- Owner: oncall-backend

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- Duration: 3m
- Kênh thông báo: Slack (#alerts-llmops)
- SLI/SLO liên quan: `guardrails.error_rate_pct_max` (<= 2%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` duy trì liên tục trong 3 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 hoặc thông báo lỗi không có câu trả lời từ chatbot.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel **Errors** trên Dashboard để kiểm tra `count_by(error_type)`.
  2. Tìm các log entry có `event == "request_failed"` trong `data/logs.jsonl` để đọc error message chi tiết.
  3. Kiểm tra trace trên Langfuse để xác định vị trí exception (ví dụ RuntimeError trong tool call).
- Mitigation tạm thời: Kích hoạt fallback prompt hoặc circuit breaker cho downstream services; tạm thời chuyển traffic sang standby instance.
- Owner: oncall-backend

## Alert 3

- Tên: LowRetrievalSuccess
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack (#alerts-rag)
- SLI/SLO liên quan: `guardrails.retrieval_success_rate_pct_min` (>= 90%)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` duy trì liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Chất lượng câu trả lời bị giảm sút do thiếu context kiến thức chuyên ngành (buộc dùng fallback answer).
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel **Errors** - Retrieval success rate trên Dashboard xem tỉ lệ thành công giảm xuống mức nào.
  2. Truy vấn log tìm các sự kiện có `tool_name == "retrieval"` và `tool_success == false`.
  3. Kiểm tra kết nối tới dịch vụ vector store / retriever và trace trên Langfuse xem có timeout hay lỗi phân đoạn corpus.
- Mitigation tạm thời: Khởi động lại connection pool của vector store; chuyển retriever sang local in-memory fallback corpus.
- Owner: oncall-rag

