# Data Lead review cho PR #2 — 12/10/2026

Owner của phần review: 24021368-DucAnh (Data Lead).
PR gốc: https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline/pull/2
Base được kiểm: `4cc454459a23ecbdfdc7e7372887cde922f4d5fe`.
Nguồn semantics: `ai_pipeline/data/docs/clause_taxonomy_v03.md` và guideline
v1.0, qua data submodule ghim vào commit main đã merge
`c325b437f76b832b7880c2bdad912bc3401e6e5d` (Data PR #8).

## Kết quả hai phần việc Data Lead

- [x] Đối chiếu đủ 12 nhãn và các clarification v0.3; chuẩn bị sửa những
  chỗ lệch/thiếu rõ ràng trong `config/taxonomy.py`.
- [x] Audit đủ 9 unmatched span lịch sử, giữ bằng chứng text/offset/hash
  trong `data_lead_span_audit.json`, không biến CONTEXT thành exact gold.

Các thay đổi code ở nhánh review cần owner Clause AI và Risk AI review trước
khi tích hợp. Báo cáo này xác nhận phần đối chiếu Data, không thay thế sign-off
risk routing hoặc kết quả model/evaluation.

## Đối chiếu taxonomy

| Nhãn | Semantics v0.3 được đối chiếu | Kết quả |
|---|---|---|
| JOB_INFO | Công việc/chức danh/bộ phận/địa điểm/nhiệm vụ/phạm vi | Khớp |
| CONTRACT_TERM | Loại/thời hạn/ngày bắt đầu-kết thúc/thời điểm hiệu lực | Khớp; giữ hiệu lực ở đây |
| COMPENSATION_BENEFITS | Bản thân quyền lợi tài chính, mức/hình thức/kỳ hạn; khác nghĩa vụ thanh toán NSDLĐ (§4.3) | Khớp |
| WORKING_TIME | Lịch/ca/làm thêm/nghỉ giữa ca-nghỉ trong ngày (§4.1) | Khớp |
| LEAVE | Nghỉ tuần/phép/lễ/nghỉ bù/ngày nghỉ (§4.1) | Khớp |
| INSURANCE_SAFETY | Bảo hiểm/mức đóng/an toàn/vệ sinh/PPE (§4.2) | Khớp |
| WORKING_CONDITIONS | Công cụ/thiết bị/phương tiện/chỗ ăn-ở/điều kiện vật chất (§4.2) | Khớp |
| TRAINING | Đào tạo/học nghề-văn hóa/cam kết/hoàn trả chi phí | Khớp |
| EMPLOYEE_OBLIGATIONS_DISCIPLINE | Nghĩa vụ/kỷ luật/trách nhiệm vật chất/thuế; NLĐ phải bồi thường (§4.4/4.6) | Bổ sung ưu tiên nghĩa vụ tuân thủ hướng dẫn/giữ gìn thiết bị/phòng cháy; chủ đề trực tiếp PPE/an toàn/bảo hiểm dùng INSURANCE_SAFETY. Bỏ gán mặc định bảo mật/không cạnh tranh chưa được source v0.3 chốt |
| EMPLOYER_RIGHTS_OBLIGATIONS | Quyền quản lý, nghĩa vụ thanh toán/đảm bảo; quyền yêu cầu bồi thường và NSDLĐ phải bồi thường NLĐ (§4.3/4.6) | Làm rõ hai hướng bồi thường và quản lý tổng quát có nhắc chấm dứt |
| TERMINATION | Căn cứ/điều kiện/sa thải/chấm dứt/báo trước/hậu quả trực tiếp (§4.5) | Làm rõ sa thải và trọng tâm trực tiếp |
| OTHER | Thi hành/số bản/sửa đổi/phụ lục/nội dung chưa có class; quyền chung NLĐ được bồi thường (§4.6) | Bỏ hiệu lực; bỏ gán mặc định giải quyết tranh chấp chưa được source chốt |

Điểm lệch quan trọng ban đầu: `OTHER` chứa "hiệu lực", trùng phạm vi
CONTRACT_TERM. Bản sửa loại sự chồng lấn đó. Employer compensation liability
được ghi rõ theo §4.6, tương ứng HDLD004_C041 đã có trong data. Không thay
đổi clause label, risk tier hoặc ngưỡng routing.

`TAXONOMY_VERSION` tăng **v03 → v04** vì sửa định nghĩa prompt theo quy tắc
đóng băng của file. Đây là revision code/prompt; bộ 12 nhãn và semantics
nguồn **data taxonomy v0.3** được giữ. Test khóa revision và các ranh giới
vừa sửa; prompt vẫn tự sinh từ LABEL_DEFINITIONS.

Bảo mật/không cạnh tranh và giải quyết tranh chấp vẫn là câu hỏi mở cần nhóm
chốt trong PR gốc. Không dùng định nghĩa code đề xuất làm bằng chứng rằng
Data đã duyệt các mapping mới hoặc các điều khoản đó hợp pháp.

## Audit 9 unmatched span

Số "7 context + 1 C027" trong PR gốc chưa đủ 9. Ca còn lại là C014 khác
ký tự nguồn, không phải context duplication.

| Clause ID | Nhãn hiện có | Nguyên nhân / bằng chứng | Quyết định source span |
|---|---|---|---|
| HDLD001_C014 | WORKING_TIME | Nguồn có `hàng tuầnS`; annotation không có `S` và tiền tố bullet | CONTEXT; không sửa nguồn/annotation |
| HDLD003_C018 | INSURANCE_SAFETY | Tách bảo hiểm từ bullet đóng bảo hiểm và thuế; highlight `các loại bảo hiểm` | CONTEXT |
| HDLD003_C018A | EMPLOYEE_OBLIGATIONS_DISCIPLINE | Cùng bullet; highlight `các khoản thuế`, lặp ngữ cảnh nghĩa vụ đóng | CONTEXT |
| HDLD004_C023 | LEAVE | Tách nghỉ ngơi khỏi bullet nghỉ/học nghề; lặp ngữ cảnh chung | CONTEXT |
| HDLD004_C024 | TRAINING | Tách học nghề-văn hóa từ cùng bullet | CONTEXT |
| HDLD004_C025 | WORKING_CONDITIONS | Tách chỗ ăn/ở từ bullet đa chủ đề | CONTEXT |
| HDLD004_C026 | INSURANCE_SAFETY | Tách bảo hộ lao động từ cùng bullet | CONTEXT |
| HDLD004_C027 | OTHER | Quyền chung NLĐ về bồi thường; source có cụm `bồi thường thiệt hại` và chỗ trống để thỏa thuận | CONTEXT; giữ OTHER theo v0.3 §4.6 |
| HDLD004_C043 | CONTRACT_TERM | Tách ngày hiệu lực, lặp chủ ngữ `Hợp đồng này` từ câu số bản/hiệu lực | CONTEXT |

C027 có nội dung nguồn; không phải row trống hoặc nhãn pháp lý đã được xác
nhận. Không bịa mức/điều kiện bồi thường vào chỗ trống. Audit chỉ xác nhận
source reference, offset và căn cứ taxonomy đang dùng; legal-risk gold là null.

Kết quả script: 234 clause, 225 EXACT đã kiểm khớp sau gom khoảng trắng,
9 CONTEXT có source reference khớp anchor/phrase đã review trong script
`data/scripts/build_context_offsets.py` của commit được pin. Script audit tái
dựng các anchor từ v04 và so sánh offset v06; đoạn không rỗng nhưng không liên
quan bị từ chối. Giữ nguyên nội dung/nhãn của 183
annotation lịch sử khi đối chiếu v04 với v06; raw/data submodule không bị sửa.
7 ca context reuse + 1 C027 taxonomy gap + 1 source text difference = 9.

Đơn vị offset là Unicode code point, `[start,end)` trên đúng raw text đã hash.
CONTEXT phải giữ `span=null`/không chấm exact gold ở consumer; có thể dùng
source-reference span riêng cho highlight. Không ép `_locate_span` tìm một
đoạn nguyên văn giả cho câu annotation đã lặp ngữ cảnh.

## Tiến độ tuần 5 so với kế hoạch gốc

Nguồn kế hoạch: `docs/DATA_PLAN.md` §3, tại main pipeline `18e56be`.

| Mục tiêu tuần 5 | Thực tế kiểm được | Trạng thái |
|---|---|---|
| 30+ hợp đồng | v06: 5 hợp đồng annotate, 4 template family | Chưa đạt; thiếu ít nhất 25 hợp đồng so với mốc tối thiểu |
| Khoảng 150–200 clause | v06: 234 clause | Đạt khối lượng; chưa đủ đa dạng hợp đồng |
| Clause Detection F1 ≥0.85 / Risk Macro-F1 ≥0.80 đáng tin cậy | Chưa có model metrics được kiểm chứng; legal-risk gold chưa có | Chưa nghiệm thu |
| Tách dev và test giữ kín từ tuần 5 | Có provisional group split; test đã nằm công khai trong repo; thiếu WORKING_TIME test và TERMINATION dev | Có split/masks, chưa phải test giữ kín đã khóa |

6 hợp đồng / 27 clause ở `synthetic_v0.2.json` là smoke fixture theo
CONTRIBUTING §5 và không được dùng để nhận KPI đã đạt. Không gộp chúng vào
5 hợp đồng thật đã annotate để tuyên bố benchmark đáp ứng mốc 30+.

Phần Data đã hoàn thành: QC và phân bố nhãn, raw/offset, duplicate masks,
hard candidate 20 ca có nguồn, release candidate/hash, tài liệu bàn giao,
đối chiếu taxonomy và audit 9 span. Còn mở: hard-gold adjudication, mở rộng
template/coverage, provenance HDLD001–003, quyền chia sẻ HDLD007 và đo model.
Vì vậy chưa thể xác nhận toàn bộ tiến độ tuần 5 đã đạt kế hoạch.

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
