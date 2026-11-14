# Backend Architecture

`ARCHITECTURE.md` và `SKELETON.md` là bản thiết kế tổng thể; file này ghi rõ trạng thái backend hiện tại và ranh giới tích hợp (C-11).

## Hiện trạng tuần 3–4

- FastAPI phục vụ 6 operation tại `/api/v1/sessions`. `session/orchestrator.py` là nơi duy nhất đổi state; lease chỉ cho một phiên đang xử lý.
- Nội dung phiên ở RAM với TTL 60 phút. SQLite chỉ chứa metadata quota/rate/RunLog/tombstone, không lưu nội dung hợp đồng.
- `pipeline.py` (X-19, 13/11) là đường xử lý thật: extraction → scope → mask → segment → Clause Graph → LLM #1 → retrieval/Data Graph → LLM #2 → citation validation → assembly; orchestrator gọi qua `make_pipeline_runner`, harness/benchmark gọi trực tiếp.
- `session/local_validation.py` ghép PDF/DOCX extraction → scope → mask toàn văn → segment trong worker thread; artifact chỉ cho caller cục bộ hoặc ném `ValidationReject`, không ghi/publish kết quả. DOCX hỗ trợ document order, accepted-state revisions, textbox gần anchor và các kiểu numbering phổ biến; OI-11 và kiểm chứng trên D1 còn mở.
- API/orchestrator chưa gọi runner này: upload chưa giữ nội dung để extract, luồng `APP_ENV=dev` vẫn dùng fixture, demo/eval chưa được phép khởi động. Clause Graph và các stage PROCESSING thật chờ N1/N2/N3; không coi fixture dev là phân tích PDF/DOCX thật.
- `ops/runlog.py` ghi stage metrics đã kiểm kiểu vào SQLite; `ops/quota.py` ghi actual calls trước provider và chỉ áp reserve khi nhận phiên mới. Eval dùng CSV ledger tách khỏi SQLite sản phẩm. Provider tính chi phí kể cả response sai schema/hủy. Dev fixture không tạo stage log giả; orchestrator thật chưa nối RunLog/CallLedger và quota số cụ thể chờ benchmark D1.
- Hai stub rỗng `integrations/clause_ai.py` và `integrations/risk_ai.py` đã xóa; luồng thật ở `ai/clause_adapter.py` và `ai/risk_adapter.py`. `explanation_ai.py` đã xóa: không có adapter hoặc provider call thứ ba.

## Luồng đích

```text
Browser → API → Orchestrator
              ├─ VALIDATING: PDF/DOCX → canonical → scope → mask toàn văn → segment → Clause Graph
              └─ PROCESSING: Clause AI (LLM #1, chỉ masked text)
                           → retrieval kho luật đóng
                           → Risk AI (LLM #2, risk + explanation + chọn citation)
                           → backend kiểm citation, dựng risk_basis, tra severity → result
```

Chỉ masked text được gửi ra provider. LLM không quyết định span, quote hay severity. Không publish partial result; export dùng kết quả hoàn chỉnh. Xem `AI_CONTEXT.md` §3 và `SKELETON.md` §1, §5 để đối chiếu invariant và chữ ký module.