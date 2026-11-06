<!-- nguồn: CLAUSE_TAXONOMY_FREEZE.md | mục: Clause Taxonomy — hồ sơ đóng băng MS-1 và chính sách đa nhãn (OI-10) > 2. Chính sách đa nhãn (OI-10) — [Đề xuất N1] | 1753 ký tự | trước: 01_1-phan-da-dong-bang.md | sau: 03_3-ba-topic-chua-co-nhan-rieng-de-xuat-n1-cho-n2-n3.md -->

## 2. Chính sách đa nhãn (OI-10) — [Đề xuất N1]

**Quy tắc cho người gán nhãn và cho prompt (một nguồn: guideline ↔ `taxonomy.py` ↔ prompt):**

1. **Mặc định 1 nhãn.** Chỉ thêm nhãn phụ khi clause có ít nhất một ý trọn vẹn (một câu hoặc một mệnh đề có chủ đề riêng) thuộc nhãn khác. Nhắc thoáng qua một từ khóa không đủ.
2. Tối đa 3 nhãn. Nhãn đầu = nhãn chính = chủ đề chiếm nhiều nội dung nhất; khi hòa, lấy chủ đề xuất hiện đầu clause. Không trùng nhãn.
3. `OTHER` chỉ dùng một mình (nếu có nhãn cụ thể thì không thêm `OTHER`). **Chưa được code ép** (`validate_labels` hiện cho phép); nếu nhóm đồng ý, thêm vào `validate_labels` kèm test và tăng `TAXONOMY_VERSION`.
4. Clause chỉ gồm tiêu đề (ví dụ `Điều 5. Tiền lương` khi các khoản con là clause riêng — TDD §11.2) gán theo chủ đề của tiêu đề, không bỏ trống. Hệ thống không có "nhãn rỗng".
5. Phân loại **không nhận role** (INV-05); nhãn không phụ thuộc NLĐ/NSDLĐ.

**Quy đổi dataset single-label ↔ dự đoán đa nhãn (cho harness M7, C-18 — N2 xác nhận):**

- Dataset `clauses_v06.csv` có một dòng cho một nhãn và không phải partition của `canonical_text` (xem `DATA_PLAN.md` §4). Mỗi clause dự đoán `p` nhận **tập nhãn vàng** = hợp nhãn của các dòng `EXACT` có span giao với `p`. Dòng `CONTEXT` (span null / không chính xác) **không** dùng để chấm.
- M7 (BRD §8.3) chấm theo cặp (clause, nhãn): mỗi nhãn dự đoán của `p` là một cặp; đúng nếu nằm trong tập nhãn vàng của `p`. Cặp vàng không có dự đoán tính là bỏ sót.
- Báo thêm chỉ số chẩn đoán "nhãn chính đúng" (nhãn đầu ∈ tập vàng), **không** thay M7. Số nhãn trung bình mỗi clause dự đoán phải được báo cùng M7 để thấy việc "gán thừa nhãn kéo recall".
- Gold T1/T2 gán trực tiếp theo quy tắc §2 (1–3 nhãn, có nhãn chính), không dùng quy đổi này.
