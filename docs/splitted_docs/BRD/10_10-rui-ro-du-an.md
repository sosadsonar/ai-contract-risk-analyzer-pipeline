<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 10. Rủi ro dự án | 2140 ký tự | trước: 09_9-rang-buoc-gia-dinh-phu-thuoc.md | sau: 11_phu-luc-a-noi-dung-hien-thi-de-xuat.md -->

## 10. Rủi ro dự án

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Phạm vi luật quá rộng so với 10 tuần và 5 người | Kho luật thiếu hoặc sai, trích dẫn không đủ | Nạp theo tầng ưu tiên, chốt danh mục sớm, chỉ trích dẫn văn bản có trong kho |
| Không có chuyên gia pháp lý | Sai nghĩa pháp lý khó phát hiện | Disclaimer, tự rà soát mẫu, nêu rõ hạn chế khi bảo vệ |
| Ẩn dữ liệu bỏ sót hoặc làm mất thông tin cần thiết | Lộ dữ liệu cá nhân hoặc phân tích sai | Tập kiểm thử riêng cho dữ liệu cá nhân, giữ các trường số liệu, không cam kết tuyệt đối |
| Đo tỷ lệ bỏ sót bằng LLM-Judge thiếu tin cậy | Kết luận chất lượng khó đứng vững khi bảo vệ | Judge khác họ model, hiệu chuẩn thủ công, báo cáo kèm giới hạn |
| Chi phí và độ trễ API LLM | Vượt ngân sách, phản hồi chậm | Giới hạn file và lượt phân tích, lưu đệm kết quả trung gian |
| Luật thay đổi | Kết quả lỗi thời | Ghi phiên bản và hiệu lực từng văn bản, người phụ trách dữ liệu cập nhật |
| Tập hợp đồng kiểm thử nhỏ | Kết quả đo không đại diện | Bổ sung hợp đồng đa dạng trước khi đo |
| Hợp đồng có cấu trúc dị thường (Hard-cases): điều khoản quá dài, nhiều ý lồng nhau (hybrid), wording lạ, hoặc hoàn toàn không có tiêu đề/heading (chỉ có gạch đầu dòng). | Tách sai ranh giới điều khoản, phân loại nhầm nhãn, làm tụt F1 < 0.85 .  | 1. Kết hợp Regex nhận diện cấu trúc + LLM semantic chunking. 2. Xây dựng chiến lược fallback: nếu không có heading thì phân đoạn theo paragraph/ngữ nghĩa. 3. Bổ sung các ca dị thường này vào tập Prompt Few-shot để mô hình học mẫu. |
| Refine pipeline làm đổi thiết kế muộn | SDD, TDD và mã lệch nhau | Mọi thay đổi pipeline phải giữ các invariant ở SRS 4.2 (SRS OI-01) |
| Graph do giảng viên yêu cầu làm phình việc kho luật và retrieval | Trễ kho luật và truy xuất, kéo theo M8 và M3 | Graph là lớp mở rộng trên retrieval nền; hệ thống chạy được khi tắt Graph; cạnh cấu trúc sinh tự động; cạnh dẫn chiếu là hạng mục cắt số 5 (9.5) |
| Codebase hiện tại là thiết kế tuần 1, lệch tài liệu | Làm tiếp theo bản cũ rồi phải làm lại | Danh sách thay đổi ở SRS Phụ lục C và Phụ lục C của BRD; làm schema và mock mới trước để các mảng không bị chặn |
