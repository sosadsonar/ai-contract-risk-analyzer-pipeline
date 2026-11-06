<!-- nguồn: CLAUSE_TAXONOMY_FREEZE.md | mục: Clause Taxonomy — hồ sơ đóng băng MS-1 và chính sách đa nhãn (OI-10) > 3. Ba topic chưa có nhãn riêng — [Đề xuất N1, chờ N2/N3] | 1853 ký tự | trước: 02_2-chinh-sach-da-nhan-oi-10-de-xuat-n1.md | sau: 04_4-sign-off.md -->

## 3. Ba topic chưa có nhãn riêng — [Đề xuất N1, chờ N2/N3]

12 nhãn đã đóng băng nên **không thêm nhãn**. Đề xuất gán vào nhãn hiện có để annotation guideline có quy tắc thống nhất. Không dùng các gán này để suy ra mức rủi ro pháp lý (risk taxonomy của N3 là nơi quyết định rủi ro).

| Topic | Đề xuất | Lý do / điểm cần N2, N3 xác nhận |
|---|---|---|
| Bảo mật thông tin, không cạnh tranh, sở hữu trí tuệ của NLĐ (nhãn `CONFIDENTIALITY_IP` v1 đã mất) | Nhãn chính `EMPLOYEE_OBLIGATIONS_DISCIPLINE`; thêm `TERMINATION` làm nhãn phụ **chỉ khi** clause tự nêu hậu quả/điều kiện sau chấm dứt hợp đồng | Là nghĩa vụ của NLĐ. **Khớp** `RISK_TAXONOMY_v0.1.md` của N3: `POST_EMPLOYMENT_RESTRICTION` (bảo mật, không cạnh tranh, chuyển giao SHTT) tham chiếu clause label `EMPLOYEE_OBLIGATIONS_DISCIPLINE`; N3 xác nhận lại. Nếu cần tách nhóm này để đo, thêm nhãn ở bản taxonomy sau (version mới), không "phân biệt ngầm" trong guideline |
| Giải quyết tranh chấp / luật áp dụng (`DISPUTE_RESOLUTION` v1 đã mất) | `OTHER` (một nhãn) | Không thuộc nhãn nào trong 11 nhãn nội dung; gần "điều khoản thi hành". Nếu clause trộn với điều khoản thi hành/số bản thì vẫn `OTHER` |
| Quyền được bồi thường của NLĐ | Hai hướng theo chủ thể câu: câu viết từ **nghĩa vụ NSDLĐ** ("NSDLĐ phải bồi thường…") → `EMPLOYER_RIGHTS_OBLIGATIONS`; **quyền chung của NLĐ** không có chủ thể NSDLĐ rõ ("NLĐ được bồi thường…", ví dụ HDLD004_C027) → `OTHER` theo data v0.3 §4.6 | Định nghĩa hiện tại của hai nhãn **chồng nhau** ở điểm này (`EMPLOYER_RIGHTS_OBLIGATIONS` có "phải bồi thường cho NLĐ", `OTHER` có "quyền được bồi thường của NLĐ"). Quy tắc theo chủ thể là cách đọc nhất quán với v0.3 §4.6; cần N2 ghi vào guideline và kiểm lại 1–2 mẫu |

Nếu N2/N3 chọn khác: sửa bảng này, sửa `LABEL_DEFINITIONS` nếu cần (tăng `TAXONOMY_VERSION` lên `v05`, mục §1.3), rồi mới đưa vào guideline.
