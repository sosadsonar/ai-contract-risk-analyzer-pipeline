<!-- nguồn: DATA_LEAD_REVIEW_V03.md | mục: Data Lead review cho PR #2 — 12/10/2026 > Đối chiếu taxonomy | 2372 ký tự | trước: 01_ket-qua-hai-phan-viec-data-lead.md | sau: 03_audit-9-unmatched-span.md -->

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
