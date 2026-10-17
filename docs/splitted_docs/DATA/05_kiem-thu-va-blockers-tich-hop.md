<!-- nguồn: DATA_LEAD_REVIEW_V03.md | mục: Data Lead review cho PR #2 — 12/10/2026 > Kiểm thử và blockers tích hợp | 1275 ký tự | trước: 04_tien-do-tuan-5-so-voi-ke-hoach-goc.md | sau: - -->

## Kiểm thử và blockers tích hợp

Từ root repo:

```powershell
git submodule update --init --recursive
python -m unittest discover -s tests -v
python scripts/audit_data_lead.py --output docs/data_lead_span_audit.json
```

10 test Data Lead pass; audit 9/9 pass. Submodule được pin cụ thể vào main
data c325b43; không dùng `submodule update --remote` và không sửa file data
từ repo pipeline.

Report lưu cả hash file taxonomy thực tế đọc và hash Git blob canonical.
Checkout Windows hiện có CRLF (`76b044…`), Git blob/release có LF (`964892…`);
khác nhau ở xuống dòng. Không sửa file trong data submodule để đổi hash.

Smoke test toàn pipeline chạy đúng thư mục `ai_pipeline/` vẫn thất bại:
`ModuleNotFoundError: No module named 'config.risk_routing'`. File này chưa
có trong PR #2 và thuộc phần Risk AI Lead; không tự tạo tier/ngưỡng pháp lý.
Ngoài ra `build_golden_v0_3.py` còn đọc clauses_v02 không có offset: cần
Evaluation Lead cập nhật adapter v06, masks và policy CONTEXT trước tính F1.
SYSTEM_PROMPT hiện yêu cầu cắt theo Điều trong khi dataset tách semantic
clause bên trong Điều; Clause AI Lead cần kiểm lại mục tiêu segmentation.

Chỉ phần Data trong PR gốc được đối chiếu ở đây. Không đánh dấu checklist
Risk AI/Backend hoặc smoke test toàn pipeline là hoàn thành.
