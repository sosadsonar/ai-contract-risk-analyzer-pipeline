# Backend Architecture

`ARCHITECTURE.md` và `SKELETON.md` là bản thiết kế tổng thể; file này ghi rõ trạng thái backend hiện tại và ranh giới tích hợp (C-11).

## Hiện trạng tuần 3

- FastAPI phục vụ 6 operation tại `/api/v1/sessions`. `session/orchestrator.py` là nơi duy nhất đổi state; lease chỉ cho một phiên đang xử lý.
- Nội dung phiên ở RAM với TTL 60 phút. SQLite chỉ chứa metadata quota/rate/RunLog/tombstone, không lưu nội dung hợp đồng.
- `session/local_validation.py` đã ghép PDF extraction → scope → mask toàn văn → segment trong worker thread; trả artifact chỉ cho caller cục bộ hoặc ném `ValidationReject`, không ghi/publish kết quả. Chưa có bộ D1 xác nhận để chạy cổng T3.
- API/orchestrator chưa gọi runner này: upload chưa giữ nội dung để extract, luồng `APP_ENV=dev` vẫn dùng fixture, demo/eval chưa được phép khởi động. Clause Graph và các stage PROCESSING thật chờ N1/N2/N3; không coi fixture dev là phân tích PDF thật.
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