<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 6. Yêu cầu phi chức năng | 970 ký tự | trước: 05_5-yeu-cau-nghiep-vu.md | sau: 07_7-du-lieu-ca-nhan-va-bao-mat.md -->

## 6. Yêu cầu phi chức năng

* Hiệu năng: mục tiêu tối đa 2 phút cho hợp đồng 15 trang (đề xuất). Hiển thị trạng thái xử lý trong lúc chờ.
* Giới hạn file: đề xuất 10MB và 30 trang để kiểm soát chi phí và độ trễ.
* Hệ thống chỉ cam kết xử lý một phiên tại một thời điểm; phiên mới bị từ chối khi đang có phiên xử lý. Dữ liệu giữa các phiên cách ly hoàn toàn.

* Tương thích: trình duyệt máy tính bản mới nhất (Chrome, Edge, Firefox). Không hỗ trợ di động.

* Ngôn ngữ: giao diện và nội dung phân tích hoàn toàn bằng tiếng Việt.

* Độ tin cậy: kết quả dở dang không bao giờ được hiển thị như kết quả cuối; mỗi phiên được thử lại thủ công tối đa 2 lần khi lỗi.

* Chi phí: ngân sách dành cho hosting, backend và API LLM: \$20. Cần giới hạn dung lượng file để kiểm soát chi phí API.
* Bảo trì: cập nhật kho luật không đòi hỏi sửa mã nguồn. Clause taxonomy và risk taxonomy được quản lý tách biệt Cạnh của Data Graph là dữ liệu đi cùng kho luật, cập nhật không sửa mã nguồn.
