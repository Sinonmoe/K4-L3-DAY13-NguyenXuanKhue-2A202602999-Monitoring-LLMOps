from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logging_config import LOG_PATH


def _percentile(values: list[int | float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def compute_dashboard_metrics(time_range_minutes: int = 60) -> dict[str, Any]:
    if not LOG_PATH.exists():
        return {
            "time_range_minutes": time_range_minutes,
            "latency": {"p50": 0, "p95": 0, "p99": 0, "ttft_p95": 0, "threshold": 3000},
            "traffic": {"count": 0, "rate_per_minute": 0.0, "threshold": 1},
            "errors": {"error_rate_pct": 0.0, "count_by_value": {}, "tool_success_rate_pct": 100.0, "threshold": 2},
            "cost": {"total": 0.0, "sum_by_minute": {}, "threshold": 2.5},
            "tokens": {"tokens_in": 0, "tokens_out": 0, "total": 0, "threshold": 50000},
            "quality": {"mean": 0.0, "threshold": 0.75},
        }

    now = datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            ts_str = rec.get("ts")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta_minutes = (now - ts).total_seconds() / 60.0
                if delta_minutes <= time_range_minutes:
                    records.append(rec)
            else:
                records.append(rec)
        except Exception:
            continue

    req_received = [r for r in records if r.get("event") == "request_received"]
    req_sent = [r for r in records if r.get("event") == "response_sent"]
    req_failed = [r for r in records if r.get("event") == "request_failed"]

    # 1. Latency & TTFT
    latencies = [r["latency_ms"] for r in req_sent if "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in req_sent if "ttft_ms" in r]
    latency_data = {
        "p50": _percentile(latencies, 50),
        "p95": _percentile(latencies, 95),
        "p99": _percentile(latencies, 99),
        "ttft_p95": _percentile(ttfts, 95),
        "threshold": 3000,
        "unit": "ms",
        "recent_latencies": latencies[-20:],
    }

    # 2. Traffic
    traffic_count = len(req_received)
    rate_per_min = round(traffic_count / max(1, min(60, time_range_minutes)), 2)
    traffic_data = {
        "count": traffic_count,
        "rate_per_minute": rate_per_min,
        "threshold": 1,
        "unit": "requests_per_minute",
    }

    # 3. Errors
    error_types: dict[str, int] = {}
    for r in req_failed:
        etype = r.get("error_type", "UnknownError")
        error_types[etype] = error_types.get(etype, 0) + 1
    total_reqs = traffic_count or (len(req_sent) + len(req_failed))
    error_rate = round((len(req_failed) / total_reqs * 100), 2) if total_reqs else 0.0

    retrieval_ops = [r for r in (req_sent + req_failed) if r.get("tool_name") == "retrieval" and r.get("tool_success") is not None]
    retrieval_successes = sum(1 for r in retrieval_ops if r.get("tool_success") is True)
    tool_success_pct = round((retrieval_successes / len(retrieval_ops) * 100), 2) if retrieval_ops else 100.0

    errors_data = {
        "error_rate_pct": error_rate,
        "count_by_value": error_types,
        "tool_success_rate_pct": tool_success_pct,
        "threshold": 2,
        "unit": "percent",
    }

    # 4. Cost
    costs = [r.get("cost_usd", 0.0) for r in req_sent]
    total_cost = round(sum(costs), 4)
    cost_data = {
        "total": total_cost,
        "threshold": 2.5,
        "unit": "usd",
    }

    # 5. Tokens
    t_in = sum(r.get("tokens_in", 0) for r in req_sent)
    t_out = sum(r.get("tokens_out", 0) for r in req_sent)
    token_data = {
        "tokens_in": t_in,
        "tokens_out": t_out,
        "total": t_in + t_out,
        "threshold": 50000,
        "unit": "tokens",
    }

    # 6. Quality
    q_scores = [r["quality_score"] for r in req_sent if "quality_score" in r]
    mean_q = round(sum(q_scores) / len(q_scores), 2) if q_scores else 0.0
    quality_data = {
        "mean": mean_q,
        "threshold": 0.75,
        "unit": "score_0_to_1",
    }

    return {
        "time_range_minutes": time_range_minutes,
        "latency": latency_data,
        "traffic": traffic_data,
        "errors": errors_data,
        "cost": cost_data,
        "tokens": token_data,
        "quality": quality_data,
    }


def render_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K4-L3A Day 13 Monitoring Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid #334155; padding-bottom: 16px; }
    h1 { font-size: 24px; font-weight: 700; color: #38bdf8; }
    .badge { background: #1e293b; border: 1px solid #475569; padding: 6px 12px; border-radius: 6px; font-size: 13px; color: #94a3b8; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
    .panel { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; }
    .panel-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
    .panel-title { font-size: 16px; font-weight: 600; color: #e2e8f0; }
    .panel-unit { font-size: 12px; color: #94a3b8; }
    .stat-main { font-size: 32px; font-weight: 700; color: #f1f5f9; margin-bottom: 8px; }
    .stat-row { display: flex; gap: 16px; margin-top: 8px; font-size: 13px; color: #cbd5e1; }
    .stat-pill { background: #0f172a; padding: 4px 8px; border-radius: 4px; }
    .threshold-badge { margin-top: auto; padding-top: 12px; font-size: 12px; color: #f59e0b; border-top: 1px solid #334155; display: flex; justify-content: space-between; }
    .status-ok { color: #10b981; }
    .status-alert { color: #ef4444; }
    .bar-bg { width: 100%; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; margin-top: 8px; }
    .bar-fill { height: 100%; background: #38bdf8; transition: width 0.3s; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>K4-L3A Day 13 Monitoring & LLMOps Dashboard</h1>
      <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Source: <code>data/logs.jsonl</code> | Contract: <code>config/dashboard.yaml</code></p>
    </div>
    <div style="display: flex; gap: 12px; align-items: center;">
      <span class="badge">Time range: <strong>60 phút</strong></span>
      <span class="badge">Refresh: <strong>30s</strong></span>
      <span id="last-update" class="badge">Đang cập nhật...</span>
    </div>
  </header>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="panel" id="panel-latency">
      <div class="panel-header">
        <span class="panel-title">1. Latency percentiles & TTFT</span>
        <span class="panel-unit">Đơn vị: ms</span>
      </div>
      <div class="stat-main" id="p95-val">-- ms</div>
      <div class="stat-row">
        <span class="stat-pill">P50: <strong id="p50-val">--</strong></span>
        <span class="stat-pill">P95: <strong id="p95-val2">--</strong></span>
        <span class="stat-pill">P99: <strong id="p99-val">--</strong></span>
        <span class="stat-pill">TTFT P95: <strong id="ttft-val">--</strong></span>
      </div>
      <div class="threshold-badge">
        <span>SLO / Threshold: P95 &le; 3000 ms</span>
        <span id="latency-status" class="status-ok">HỢP LỆ</span>
      </div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="panel" id="panel-traffic">
      <div class="panel-header">
        <span class="panel-title">2. Request traffic</span>
        <span class="panel-unit">Đơn vị: req/min</span>
      </div>
      <div class="stat-main" id="traffic-rate">-- req/m</div>
      <div class="stat-row">
        <span class="stat-pill">Tổng requests (60m): <strong id="traffic-count">--</strong></span>
      </div>
      <div class="threshold-badge">
        <span>SLO / Threshold: Rate &ge; 1 req/min</span>
        <span id="traffic-status" class="status-ok">HỢP LỆ</span>
      </div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="panel" id="panel-errors">
      <div class="panel-header">
        <span class="panel-title">3. Error rate & retrieval success</span>
        <span class="panel-unit">Đơn vị: %</span>
      </div>
      <div class="stat-main" id="error-rate">--%</div>
      <div class="stat-row">
        <span class="stat-pill">Retrieval success: <strong id="retrieval-rate">--%</strong></span>
        <span class="stat-pill">Lỗi phân loại: <strong id="error-breakdown">0</strong></span>
      </div>
      <div class="threshold-badge">
        <span>SLO / Threshold: Error rate &le; 2%</span>
        <span id="errors-status" class="status-ok">HỢP LỆ</span>
      </div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="panel" id="panel-cost">
      <div class="panel-header">
        <span class="panel-title">4. Cost over time</span>
        <span class="panel-unit">Đơn vị: USD ($)</span>
      </div>
      <div class="stat-main" id="cost-total">$0.00</div>
      <div class="bar-bg">
        <div id="cost-bar" class="bar-fill" style="width: 0%;"></div>
      </div>
      <div class="threshold-badge">
        <span>Threshold: Tổng chi phí &le; $2.50 USD</span>
        <span id="cost-status" class="status-ok">HỢP LỆ</span>
      </div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="panel" id="panel-tokens">
      <div class="panel-header">
        <span class="panel-title">5. Input & output tokens</span>
        <span class="panel-unit">Đơn vị: tokens</span>
      </div>
      <div class="stat-main" id="tokens-total">0</div>
      <div class="stat-row">
        <span class="stat-pill">Tokens In: <strong id="tokens-in">0</strong></span>
        <span class="stat-pill">Tokens Out: <strong id="tokens-out">0</strong></span>
      </div>
      <div class="threshold-badge">
        <span>Threshold: Tổng tokens &le; 50,000</span>
        <span id="tokens-status" class="status-ok">HỢP LỆ</span>
      </div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="panel" id="panel-quality">
      <div class="panel-header">
        <span class="panel-title">6. Quality proxy</span>
        <span class="panel-unit">Thang đo: 0.0 &rarr; 1.0</span>
      </div>
      <div class="stat-main" id="quality-mean">0.00</div>
      <div class="bar-bg">
        <div id="quality-bar" class="bar-fill" style="width: 0%; background: #10b981;"></div>
      </div>
      <div class="threshold-badge">
        <span>SLO / Threshold: Mean quality &ge; 0.75</span>
        <span id="quality-status" class="status-ok">HỢP LỆ</span>
      </div>
    </div>
  </div>

  <script>
    async function loadData() {
      try {
        const res = await fetch('/api/dashboard-metrics');
        const data = await res.json();
        
        // 1. Latency
        document.getElementById('p50-val').textContent = data.latency.p50 + ' ms';
        document.getElementById('p95-val').textContent = data.latency.p95 + ' ms';
        document.getElementById('p95-val2').textContent = data.latency.p95 + ' ms';
        document.getElementById('p99-val').textContent = data.latency.p99 + ' ms';
        document.getElementById('ttft-val').textContent = data.latency.ttft_p95 + ' ms';
        const latOk = data.latency.p95 <= data.latency.threshold;
        const latEl = document.getElementById('latency-status');
        latEl.textContent = latOk ? 'HỢP LỆ' : 'VI PHẠM (ALERT)';
        latEl.className = latOk ? 'status-ok' : 'status-alert';

        // 2. Traffic
        document.getElementById('traffic-rate').textContent = data.traffic.rate_per_minute + ' req/m';
        document.getElementById('traffic-count').textContent = data.traffic.count;
        const traOk = data.traffic.count === 0 || data.traffic.rate_per_minute >= data.traffic.threshold;
        const traEl = document.getElementById('traffic-status');
        traEl.textContent = traOk ? 'HỢP LỆ' : 'THẤP';
        traEl.className = traOk ? 'status-ok' : 'status-alert';

        // 3. Errors
        document.getElementById('error-rate').textContent = data.errors.error_rate_pct + '%';
        document.getElementById('retrieval-rate').textContent = data.errors.tool_success_rate_pct + '%';
        document.getElementById('error-breakdown').textContent = Object.keys(data.errors.count_by_value).length ? JSON.stringify(data.errors.count_by_value) : '0';
        const errOk = data.errors.error_rate_pct <= data.errors.threshold;
        const errEl = document.getElementById('errors-status');
        errEl.textContent = errOk ? 'HỢP LỆ' : 'VI PHẠM (ALERT)';
        errEl.className = errOk ? 'status-ok' : 'status-alert';

        // 4. Cost
        document.getElementById('cost-total').textContent = '$' + data.cost.total.toFixed(4);
        const costPct = Math.min(100, (data.cost.total / data.cost.threshold) * 100);
        document.getElementById('cost-bar').style.width = costPct + '%';
        const costOk = data.cost.total <= data.cost.threshold;
        const costEl = document.getElementById('cost-status');
        costEl.textContent = costOk ? 'HỢP LỆ' : 'VƯỢT NGÂN SÁCH';
        costEl.className = costOk ? 'status-ok' : 'status-alert';

        // 5. Tokens
        document.getElementById('tokens-total').textContent = data.tokens.total.toLocaleString();
        document.getElementById('tokens-in').textContent = data.tokens.tokens_in.toLocaleString();
        document.getElementById('tokens-out').textContent = data.tokens.tokens_out.toLocaleString();
        const tokOk = data.tokens.total <= data.tokens.threshold;
        const tokEl = document.getElementById('tokens-status');
        tokEl.textContent = tokOk ? 'HỢP LỆ' : 'VƯỢT NGƯỠNG';
        tokEl.className = tokOk ? 'status-ok' : 'status-alert';

        // 6. Quality
        document.getElementById('quality-mean').textContent = data.quality.mean.toFixed(2);
        document.getElementById('quality-bar').style.width = (data.quality.mean * 100) + '%';
        const qOk = data.quality.mean >= data.quality.threshold;
        const qEl = document.getElementById('quality-status');
        qEl.textContent = qOk ? 'HỢP LỆ' : 'DƯỚI CHUẨN';
        qEl.className = qOk ? 'status-ok' : 'status-alert';

        document.getElementById('last-update').textContent = 'Cập nhật: ' + new Date().toLocaleTimeString();
      } catch (err) {
        console.error(err);
      }
    }

    loadData();
    setInterval(loadData, 30000);
  </script>
</body>
</html>
"""
