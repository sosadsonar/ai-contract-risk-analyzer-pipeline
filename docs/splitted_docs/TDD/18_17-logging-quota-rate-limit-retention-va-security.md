<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 17. Logging, quota, rate limit, retention và security | 3380 ký tự | trước: 17_16-export-report.md | sau: 19_18-evaluation-harness-va-gold-format.md -->

# 17. Logging, quota, rate limit, retention và security

## 17.1 RunLog schema

```text
run_log(
  id INTEGER PK,
  session_id TEXT,
  stage TEXT,
  started_at TEXT,
  duration_ms INTEGER,
  calls INTEGER,
  input_tokens INTEGER,
  output_tokens INTEGER,
  estimated_cost REAL,
  error_code TEXT,
  graph_enabled INTEGER,
  graph_added_candidates INTEGER,
  created_at TEXT
)
```

Không raw filename nếu có PII; persistent log chỉ extension/size. Không prompt/canonical/masked/quote/PII.

## 17.2 Daily quota và admission reservation

Mỗi actual provider request, kể cả retry, tăng daily counter atomically trước call. Phiên đang chạy không bị dừng khi counter vượt do retry; upload mới sau đó bị chặn, đúng BR-16.

TDD 0.2 bỏ “reserve 4 calls”. Trước demo, D1 phải đo `planned_calls = ceil(n_clause/CLAUSE_BATCH_SIZE) + ceil(n_clause/RISK_BATCH_SIZE)` cho từng contract. `SESSION_CALL_RESERVE` được cấu hình bằng p95 planned calls (hoặc conservative value nhóm chốt). Admission cho session mới chỉ pass khi:

```text
remaining_daily_calls >= SESSION_CALL_RESERVE
```

Vì actual retries có thể vượt reserve, current session vẫn hoàn tất; counter có thể vượt nhẹ quota nhưng hệ thống không nhận session mới. Báo cáo cost phải ghi cả planned vs actual calls.

`DAILY_LLM_CALL_QUOTA` **không có default 120 trong demo**. Nhóm phải chốt từ số call/token/cost D1 + giá model cụ thể + phần ngân sách vận hành $5. Ví dụ kỹ thuật: với 40-60 clause và batch 20/6, planned calls xấp xỉ 9-13 trước retry; đây là lý do không nên dùng một quota tùy ý mà không đo.

## 17.3 Evaluation budget isolation

`APP_ENV=eval` không dùng runtime quota/rate counter SQLite của product. Evaluation harness có `eval_cost_ledger.json/csv` riêng và vẫn log actual calls/tokens/cost để kiểm soát phần ngân sách đánh giá $15.

## 17.4 IP rate limit

Sliding window: tối đa 5 Create requests/10 phút/IP mặc định. Persistent key là HMAC-SHA256(server_salt, IP) truncated; raw IP chỉ request context.

## 17.5 Retention và cleanup

* last_activity cập nhật Create/Result/Retry/Export/End; Status polling không tính.
* Cleanup mỗi 60s; inactivity >=60 phút -> cancel, delete temp/content, tombstone EXPIRED.
* Tombstone chỉ session_id/status/expired_at, giữ 24h.
* Restart không restore session. Startup dọn temp stale >2h.

## 17.6 Performance/cost measurement gate

NFR-PERF-01 chỉ áp dụng PDF <=15 trang hoặc DOCX <=50.000 chars; **không cam kết 120s cho input max 150 clause**. Trước MS-2 chạy D1 benchmark và ghi p50/p90 cho: local preprocessing, LLM #1, retrieval/graphs, LLM #2, assembly. Batch size/parallelism chỉ được khóa sau số đo này.

Timeout 30s + one retry có thể làm một call gần 60s; vì vậy benchmark phải có cả case provider latency injection. Nếu p90 >120s, ưu tiên giảm payload token, tăng batch hợp lý hoặc giảm context trước khi thay invariant.

## 17.7 Security checklist

| Kiểm soát | Thiết kế/TDD test |
|---|---|
| HTTPS | TLS ở deployment. |
| Secrets | ENV/secret store; key qua header; no log. |
| Session isolation | exact session_id lookup + negative tests. |
| Upload safety | hard byte cap, sniff type, random temp dir, sanitize display filename. |
| LLM boundary | outbound capture không raw PII/canonical. |
| Logs | automated PII scan. |
| No durable contract data | DB/temp/restart audit. |
| Single worker | deployment smoke fail nếu cấu hình >1 worker trong demo profile. |
