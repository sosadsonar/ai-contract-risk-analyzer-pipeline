<!-- nguồn: D1_INVENTORY_2026-10-28.md | mục: Kiểm kê D1 từ dữ liệu v06 (28/10/2026) | 2364 ký tự | trước: - | sau: - -->

# Kiểm kê D1 từ dữ liệu v06 (28/10/2026)

Nguồn đọc tại repo dữ liệu cùng workspace: `data/processed/clauses_v06.csv`, `data/splits/provisional_v06.json`, `data/contracts_metadata.csv`. Báo cáo chỉ chứa số liệu tổng hợp; không sao chép nội dung hợp đồng hay thông tin cá nhân.

| Hợp đồng | Số clause v06 | Split tạm | Nhóm tương đồng |
|---|---|---|---|
| HDLD001 | 39 | dev | SIM_A |
| HDLD002 | 40 | dev | SIM_A |
| HDLD003 | 61 | train | SIM_B |
| HDLD004 | 43 | test | SIM_C |
| HDLD005 | 51 | train | SIM_D |

Tổng: **5 hợp đồng, 234 clause**, trong đó **225 `EXACT` và 9 `CONTEXT`** theo `offset_quality`. Split hiện mang trạng thái `PROVISIONAL`: train 112, dev 79, test 43 clause. HDLD006 là `HOLD_NEAR_DUPLICATE` và chưa có annotation v06 đầy đủ.

BRD §8.2 ghi D1 là 4 hợp đồng/183 clause. Con số 183 không khớp 234 clause v06; chưa có quyết định nào xác định 4 hợp đồng D1. Vì vậy **chưa chốt thành phần D1** và chưa dùng split tạm làm gold D1. HDLD001/002 ở cùng nhóm SIM_A phải giữ cùng split để tránh rò rỉ mẫu gần trùng.

## Việc còn cần xác nhận trước khi tạo gold D1

1. N2 và chủ BRD chọn 4 hợp đồng D1, đối chiếu mục tiêu 183 clause; lưu quyết định và version split.
2. Người chịu trách nhiệm dữ liệu kiểm tra quyền sử dụng và khử định danh từng hợp đồng; trạng thái `ANNOTATED` và offset `EXACT` không chứng minh đã loại PII.
3. Gold M1 cần ranh giới ký tự sửa tay trên văn bản canonical. `clauses_v06.csv` là annotation nhãn clause, không phải gold segmentation; 9 dòng `CONTEXT` cần policy riêng trước khi tính F1.

## Addendum — 2026-11-02

**D1 working scope is fixed to HDLD001–004**, matching BRD §8.2 (4 contracts,
183 clauses); HDLD005's 51 v06 clauses remain supplemental and outside D1.
No BRD text was changed. The data-repository inventory at
`ai_pipeline/data/docs/archive/reports/D1_DATA_INVENTORY_2026-10-19.md` records the current
source hashes, local regex counts and limitations.

The current canonical-text scan found no email, phone-pattern or continuous
9–12 digit strings for the four D1 contracts. This does not prove the sources
are de-identified: manual review of names, addresses, images/signatures,
metadata and indirect identifiers is incomplete, as are documented reuse
rights and independent review. The raw inputs remain ineligible for gold
privacy or T1 acceptance. This closes the inventory/scope question only.
