# Chốt chỉ số Dev và các slice commit — 12/11/2026

## Phạm vi, nguồn và giới hạn

- Worktree: `ai-contract-risk-analyzer-pipeline-eval-integration`, nhánh `codex/d1-m7-handoff-2026-11-09`.
- Chỉ đọc nguồn và Gold **D1/D2 Dev** trong data repo. Không mở văn bản T1/T2, không gọi Gemini, không push/merge/reset/checkout/clean.
- Python dùng `.venv` pipeline và `PYTHONPATH=backend`. `rules_v1.3` bật hai cờ `enable_plus_lists=True`, `enable_blank_line_paragraphs=True` trong **runner Dev**; mặc định toàn ứng dụng của `segment()` không đổi.
- Bộ Gold rủi ro Dev được người duyệt kỹ thuật phê duyệt: D1 M2 v02 có 6 bộ ba; D2 dùng 30 ca lỗi chèn đã VERIFIED và Gold segmentation v02, mở rộng thành 60 bộ ba cho hai vai trò. Các đoạn gốc HDLD001–004 có mặt trong cả D1 và D2, nên phép gộp không phải 66 quan sát độc lập.
- Bộ dự đoán M2 trong báo cáo là **rule Điều 17 M5 cục bộ đã khóa + rule nguồn `UNILATERAL_CHANGE` trên Dev**, không phải Risk Adapter/Gemini độc lập. Không dùng nhãn Gold, document ID hay offset Gold trong runtime detector. Gold chỉ dùng lúc chấm điểm.

## Quyết định kiến trúc đã thực thi

`make_pipeline_runner()` vẫn opt-in và bật `rules_v1.3` mặc định cho đường Dev. Hành vi hiện hữu của `risk_assembler.py` được chấp thuận: gỡ nhãn không hợp vai trò theo taxonomy, ghi `need_review` khi cần, tự tính severity từ code. `sanitize_advice_sentences()` loại câu khuyên hành động theo các pattern đã duyệt; từ nối `nên` đơn lẻ được giữ. Nếu phần giải thích trung tính còn dưới 10 ký tự, hàm raise `AiOutputInvalid`. Runner gọi hàm này trước assembly. Bộ lọc citation tiếp tục yêu cầu candidate ID thuộc đúng điều khoản và còn hiệu lực tại ngày phân tích.

## Bảng chỉ số

| Mục | Kết quả và bằng chứng | Trạng thái |
|---|---|---|
| M1 segmentation | D2 v02 Dev: 228/250 TP, F1 **0.906561** ở IoU≥0.80 theo `docs/M1_M5_FINAL_LOCK_READOUT_2026-11-11.md`. D1 HDLD001/002 context-neutral: 0.8800/0.8831. T1 read-only trước đó: 0.385116. | Dev D2 qua ngưỡng 0.85; chưa qua nghiệm thu held-out. |
| M2 D2 Dev | **58 TP, 6 FP, 2 FN**, precision **0.906250**, recall **0.966667**, macro-F1 trên 2 nhãn có Gold **0.987179**, macro-F1 trên 21 nhãn **0.094017**. Gold support **2/21**. Sáu FP là dự đoán `UNILATERAL_CHANGE` trên D2 chưa có Gold cho nhãn đó. | Diagnostic local-rule vượt 0.80 trên hai nhãn hiện có; chưa chứng minh taxonomy 21 nhãn. |
| M2 D1+D2 Dev | **64 TP, 6 FP, 2 FN**, precision **0.914286**, recall **0.969697**, macro-F1 trên 3 nhãn có Gold **0.880342**, macro-F1 trên 21 nhãn **0.125763**. Gold support **3/21**. Sáu Gold D1 `UNILATERAL_CHANGE` đều khớp; sáu FP vẫn đến từ D2 chưa gán nhãn này. | Diagnostic local-rule vượt 0.80 trên lát cắt Gold thưa; chưa nghiệm thu M2 chính thức. |
| M2b | Basis type đúng **58/58** M2 TP của D2, Wilson 95% CI **0.937882–1.0**; gộp **64/64**, CI **0.943376–1.0**. | Chỉ đánh giá các TP; chưa phản ánh FN/FP. |
| M3a | Kiểm tra **96/96** citation IDs Điều 17 do mapping rule cục bộ gán: tồn tại và còn hiệu lực trong corpus APPROVED tại 12/11/2026. | **Proxy candidate/corpus/effectivity**; không phải citation do Risk Adapter chọn hay kiểm chứng độ liên quan ngữ nghĩa. |
| M4 | `quote == canonical_text[start_char:end_char]` **70/70** dự đoán rule trên Dev. | Invariant local segmentation, chưa phải product output end-to-end. |
| M5 | Detector SHA-256 `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438`; báo cáo khóa trước đó: D2 Dev **30/30**, T2 read-only **26/30**. Không chạy lại T2. | Injected recall, không phải M2 F1. |
| M6 | Gói nguồn: `human_a` 40/40; `human_b`, `judge`, adjudication thật vẫn 0/40. Chế độ **single-reviewer Dev calibration** tạo bản sao `human_b=human_a` tạm thời và judge rule-based: **40/40 Đúng, agreement 1.0, threshold flag true**, κ không xác định do toàn bộ nhãn giống nhau. | `acceptance_scope_verified=false`, `m6_acceptance_met=false`; không có thỏa thuận hai người độc lập. |
| M7 | D1 Dev classifier TF-IDF leave-one-document-out trước đó: Macro-F1 **0.510622**, CI **0.254585–0.838930** trên 137/174 EXACT spans (`docs/D1_D2_RULES_V13_AND_TEACHER_TARGETS_2026-11-10.md`). | Chưa đạt 0.80; khác M2. |

Chi tiết per-label, CI, source SHA, số đoạn D1 **223** và D2 **253** nằm trong `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m2_m2b_dev_evaluation_2026-11-12.json`. D2 có 60 Gold tuples và 64 dự đoán (58 Điều 17, 6 `UNILATERAL_CHANGE`). Gold D2 chỉ gán nhãn Điều 17; vì thế 6 FP `UNILATERAL_CHANGE` là **chưa phân xử**, không thể tự coi là sai thật hay tự bỏ khỏi điểm thô. Gói hiệu chuẩn M6 riêng nằm trong `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m6_dev_calibration_2026-11-12.json`.

Kiểm toán nguyên nhân lệch điểm M2 cũ: script đã dùng **span Gold clause v02**, không so thẳng `insertion_span` với prediction. Sáu Gold clause chưa ghép theo IoU đều được prediction dài hơn chứa trọn. Căn chỉnh mới ưu tiên IoU≥0.50, sau đó ghép một đối một nếu prediction chứa ≥80% Gold clause; không nhân đôi TP khi một prediction chứa nhiều Gold. D2 tăng từ 46 lên 58 TP Điều 17. `gold_from_injections()` hiện tự ánh xạ câu chèn vào Gold clause theo containment≥0.80, đối chiếu clause ref đã duyệt và khử trùng lặp bộ ba. Điểm M5 30/30 dùng phép localization khác, không thay điểm M2.

## Kiểm thử và ranh giới mã

- Đã cài `pymupdf` và `pytest-asyncio` vào `.venv` pipeline vì hai phụ thuộc dev này thiếu. Không sửa dependency manifest.
- Full pytest với marker `not llm and not llm_local` sau đợt sửa M2/M6: **771 passed, 16 skipped, 4 deselected**, exit 0. Có 3 skip PII vì data submodule vắng mặt; các skip còn lại theo điều kiện test. Không gọi model thật.
- `git diff --check` exit 0 cho tracked diffs. Tệp untracked không thuộc phạm vi lệnh này; Python tests và Ruff kiểm tra các tệp mới.
- Bộ M5 giữ nguyên SHA đã khóa; không sửa logic detector. Không đọc văn bản T1/T2.
- `D2_40_ratings_ducanh_draft.csv` và `D2_40_ratings_minh_blind.csv` không bị sửa. Script M6 chỉ tạo tệp chấm tổng hợp tạm trong bộ nhớ đĩa rồi xóa; JSON đầu ra không chứa văn bản điều khoản.

## Bảy nhóm commit cô lập

1. Parser: `segmenter.py`, `structure_parser.py` và hai unit tests tương ứng.
2. Eligibility: `eligibility.py`, `clause_adapter.py`, `test_clause_eligibility.py`.
3. Clause Graph/Risk Adapter: `graph_builder.py`, `context_resolver.py`, `risk_adapter.py` và ba unit tests liên quan.
4. M6 scorer: `score_m6_review_packet.py`, `test_m6_review_packet.py`.
5. M2 metrics và Dev evaluation: `risk_classification.py`, frozen `dev_injection_candidate.py`, `run_m2_dev_evaluation.py`, các unit tests liên quan và JSON chỉ số aggregate.
6. Dev runner: `orchestrator.py`, `pipeline_runner.py`, `test_orchestrator_pipeline_integration.py`.
7. Tài liệu: báo cáo này và `M2_METRICS_AND_FULL_RUNNER_ASSEMBLY_2026-11-12.md`.

Các tracked/untracked khác đang dirty trong worktree nằm ngoài manifest này và không được stage. Mỗi commit dùng `git add --` với danh sách chính xác, không dùng `git add .`.

## Commit hashes

Danh sách hash của bảy commit được bổ sung sau khi commit để tránh ghi sai hash của chính commit chứa báo cáo. Phụ lục hash sau commit là thay đổi metadata chưa commit do tính tự tham chiếu của SHA-1 commit.

```text
162f8d8b0886abfe3abb507bc1deb1f636c7af6c docs(eval): report Dev metrics and scoped delivery
f806a4a48a828d9a60ca22b57bdcc2329c55360f feat(dev): assemble validated risk output and sanitize advice
67e3ad1baee662cb8e1b8ddbad7401d2ca44efd4 feat(eval): score approved Dev risk slices and freeze M5
42d852ca3d94f204ef931526aaeac8388c65c315 test(m6): score blinded human review packet
40e4805658b8d20840bbadea8e9f76f3717fc3bd feat(risk): attach bounded clause graph context
9ddffee90c94eeb1641c479edaa3b1556cbb21db feat(clause): filter classification eligibility from source text
3c4199404753a71481852d8e2e01ad31297661cf feat(clause): add opt-in rules v1.3 parser boundaries
```
