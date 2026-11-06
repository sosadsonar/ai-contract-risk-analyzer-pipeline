<!-- nguồn: RISK_TAXONOMY_v0.1.md | mục: Risk Taxonomy - Contract Risk Analyzer > Xử lý khi gặp ô `- | 455 ký tự | trước: 03_cach-doc-bang.md | sau: 05_bang.md -->

## Xử lý khi gặp ô `-

Nếu bước 1 và 2 cho ra (nhãn, basis_type, vai trò) rơi vào `-` thì coi là gán sai: gắn cờ `need_review`, nhãn đó bị gỡ. Hết nhãn thì clause không xuất ra sản phẩm (không phải rủi ro của vai trò này) và được tính là fail khi chấm nhãn. Assembler (`backend/app/integrations/risk_assembler.py`) làm việc này, rồi dựng `risk_basis = [{label, basis_type}]` cho response sản phẩm và ghi vào `diagnostics`, không đưa vào response sản phẩm.
