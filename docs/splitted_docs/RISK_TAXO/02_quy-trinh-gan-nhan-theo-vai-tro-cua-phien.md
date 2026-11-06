<!-- nguồn: RISK_TAXONOMY_v0.1.md | mục: Risk Taxonomy - Contract Risk Analyzer > Quy trình gán nhãn (theo vai trò của phiên) | 1061 ký tự | trước: 01_tl-dr.md | sau: 03_cach-doc-bang.md -->

## Quy trình gán nhãn (theo vai trò của phiên)

1. **basis_type**: một giá trị cho cả clause (LLM trả).
   - `LEGAL_VIOLATION` (LV): trái quy định cấm hoặc bắt buộc, hoặc vượt ngưỡng pháp luật rõ ràng trong kho luật.
   - `UNFAVORABLE` (UF): không trái luật nhưng bất lợi đáng kể cho vai trò đang phân tích.
   - `AMBIGUOUS` (AM): câu chữ mơ hồ, thiếu điều kiện hoặc mức cụ thể, có thể dẫn đến tranh chấp.
   - Nếu thỏa nhiều loại, ưu tiên LV, rồi UF, rồi AM.
2. **risk_labels**: 1 đến 3 nhãn trong bảng. Clause thường chỉ có một ý chính nên thường một nhãn.
3. **severity**: backend tra bảng theo (nhãn, basis_type, vai trò), LLM không trả severity. Nhiều nhãn thì lấy mức cao nhất. Severity phụ thuộc cả risk_basis, không chỉ nhãn và vai trò.
4. Nếu `evidence_status = INSUFFICIENT_EVIDENCE` thì severity trong kết quả là `null` bất kể bảng (SRS 2.3).

Lưu ý: basis_type là phán đoán về nội dung clause (trái luật, bất lợi hay mơ hồ), không phải hàm của nhãn. Vì vậy chỉ có thể tra xuôi (basis thành severity), không tra ngược severity hay nhãn về basis được.
