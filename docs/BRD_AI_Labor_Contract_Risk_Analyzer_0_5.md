# **BRD: AI Labor Contract Risk Analyzer**

*Phiên bản 0.5 (dự thảo, chờ duyệt) | 12/10/2026*

Thay đổi chính trong 0.5 so với 0.4:

- 1, 2.1, 3.1: thêm Data Graph (Retrieval & Fact-finding) và Clause Graph (Validation & Reasoning) theo yêu cầu của giảng viên (BO-5, BR-17, BR-18); BO-4 bỏ chữ "đều" như đã ghi ở 0.4.  
- 5: bảng BR nay có BR-05a, BR-05b, BR-05c và BR-16 (đã ghi ở 0.4 nhưng chưa có trong bảng); thêm BR-17, BR-18.  
- 7: đánh số 7.1 đến 7.6; thêm 7.3 ngưỡng ẩn dữ liệu cá nhân (chuyển từ SRS NFR-SEC-01); 7.5 gồm cả judge; 7.6 dữ liệu dev và test; thêm quy định không lưu nội dung hợp đồng ở kho bền vững.  
- 8: M1 ghi rõ cách khớp IoU; M8 báo thêm có và không dùng Graph; sửa hai câu cụt (BL-1, 8.5).  
- 9: 9.1 làm rõ 10 tuần là 8 tuần xây dựng cộng 2 tuần đánh giá; thêm 9.4 Mốc thời gian, đổi Thứ tự cắt thành 9.5, thêm 9.6 Phân công (khớp các tham chiếu §9.4, §9.5, §9.6 đã có sẵn trong BRD 0.4); thêm hạng mục cắt số 5 cho Graph.  
- 10: thêm rủi ro về Graph và về codebase lệch tài liệu. 11: thêm OI-14 đến OI-18.  
- Phụ lục B thêm thuật ngữ Graph; thêm Phụ lục C ghi nhận chỗ codebase hiện tại lệch BRD (chưa sửa code; chi tiết kỹ thuật ở SRS Phụ lục C).

Thay đổi chính trong 0.4 so với 0.3:

- 1: BO-1 đổi từ 10 tuần sang 8 tuần, BO-2 và BO-4 viết lại theo cách đo được; bảng chỉ số thành công chỉ dẫn ID ở §8, không lặp số.  
- 3: thêm định nghĩa "rủi ro" và 5 điều khoản mẫu theo vai trò.  
- 4.1: bước 5 đổi thành che dữ liệu cá nhân trước, tách điều khoản sau; bỏ tên model và tên thuật toán khỏi luồng người dùng.   
- 4.2 và 6: thêm ca từ chối khi hệ thống bận, khi vượt trần điều khoản hoặc trần chi phí; file bị từ chối kết thúc phiên.  
- 5: tách BR-05 thành BR-05a, BR-05b, BR-05c; BR-09 đổi sang highlight trên văn bản trích xuất; BR-10 bổ sung cảnh báo không kiểm tra điều khoản thiếu; thêm BR-16 (trần chi phí).  
- 7: ngưỡng PII theo loại, bỏ chữ "đều" ở BO-4, thông báo dữ liệu nói rõ nhà cung cấp LLM có chính sách lưu riêng.  
- 8: viết lại thành Evaluation Plan nằm trong BRD: bốn tập dữ liệu (T1, T2, D1, D2), chỉ số M1 đến M8 (M3 tách thành M3a và M3b, thêm M7 và M8) và BL-1, giao thức judge dùng Claude, tiêu chí nghiệm thu.  
- 9: ngân sách \$20, mốc thời gian, phân công, thứ tự cắt bỏ tính năng (nếu quá deadline).  
- 11: Open Issues.

## **1\. Tổng quan**

### **1.1 Bối cảnh và vấn đề**

Phần lớn người ký hợp đồng lao động (HĐLĐ) không đủ kiến thức pháp lý để biết điều khoản nào bất lợi hoặc trái luật. Người lao động (NLĐ) thường chỉ nhận được bản hợp đồng để ký. Người sử dụng lao động (NSDLĐ), đặc biệt là doanh nghiệp nhỏ không có bộ phận pháp chế, có thể soạn điều khoản không phù hợp pháp luật và phải chịu rủi ro tranh chấp hoặc xử phạt. Cùng một điều khoản có thể là rủi ro với bên này nhưng không phải với bên kia, nên phân tích phải theo vai trò.

Hai phương án thay thế hiện nay đều có điểm yếu. Thuê luật sư thì tốn kém và chậm. Hỏi các LLM thông dụng (ví dụ ChatGPT) thì nhanh và rẻ nhưng dễ bịa nội dung hoặc trích dẫn sai điều luật.

### **1.2 Mục tiêu nghiệp vụ**

Sản phẩm là một web app: người dùng chọn vai trò, tải HĐLĐ lên và nhận báo cáo rủi ro có căn cứ pháp luật.

* BO-1: có bản demo chạy full luồng từ upload đến báo cáo trong 8 tuần.  
* BO-2: mọi rủi ro nêu ra đều gắn với điều khoản gốc và điều luật có thật trong kho luật của hệ thống và liên quan đến rủi ro đó. Rủi ro không có căn cứ trong kho luật được gắn nhãn "chưa đủ căn cứ" (BR-15), không bị gán điều luật.  
* BO-3: cùng một hợp đồng, kết quả (loại rủi ro, mức độ nghiêm trọng, giải thích) thay đổi theo vai trò đã chọn. Nghiệm thu bằng các ca mẫu ở mục 3.3 và 8.6  
* BO-4: dữ liệu cá nhân trong hợp đồng được ẩn trước khi gửi cho LLM bên thứ ba, đạt ngưỡng theo loại ở 7.3.  
* BO-5: có Data Graph (đồ thị kho luật, phục vụ Retrieval & Fact-finding: tìm kiếm thông tin, truy vấn tri thức, tức truy xuất căn cứ pháp lý) và Clause Graph (đồ thị điều khoản của hợp đồng đang phân tích, phục vụ Validation & Reasoning: kiểm tra mâu thuẫn, suy diễn điều kiện) theo yêu cầu của giảng viên. Nghiệm thu bằng BR-17, BR-18 và M8 báo có và không dùng Graph (8.3).  

### **1.3 Chỉ số thành công**

| Mục tiêu | Chỉ số đo | Nơi định nghĩa |
| :---- | :---- | :---- |
| BO-1: luồng chính chạy trọn | Tiêu chí hoàn thành luồng; thời gian phân tích | 8.6; 6 |
| BO-2: gắn điều khoản gốc, điều luật có thật và liên quan | M3a, M3b, M4, M8 | 8.3 |
| BO-3: kết quả đổi theo vai trò | Ca mẫu theo vai trò | 3.3, §.6 |
| BO-4: ẩn dữ liệu cá nhân | Ngưỡng PII theo loại | 7.3 |
| Chất lượng phân tích | M1, M2, M5, M7 | 8.3 |
| Độ tin cậy của phép chấm | M6 | 8.3 |
| Tốt hơn LLM thông dụng | BL-1 | 8.3 |
| BO-5: Data Graph và Clause Graph | BR-17, BR-18; M8 có và không Graph | 5; 8.3 |

### 

### **1.4 So sánh với phương án thay thế**

| Phương án | Chi phí | Tốc độ | Điểm yếu |
| :---- | :---- | :---- | :---- |
| Luật sư | Cao | Chậm | Chi phí, phải hẹn và chờ |
| LLM thông dụng | Thấp | Nhanh | Dễ bịa nội dung, trích dẫn sai điều luật |
| Sản phẩm này | Miễn phí (demo) | Vài phút | Không thay thế tư vấn pháp lý; chất lượng phụ thuộc database luật; mức vượt trội so với LLM thông dụng cần được kiểm chứng (mục 8\) |

## **2\. Phạm vi**

### **2.1 Trong phạm vi**

* Web app cho máy tính, giao diện tiếng Việt, không cần đăng ký tài khoản.  
* Đầu vào: HĐLĐ tiếng Việt, định dạng PDF hoặc DOCX có sẵn text, đã soạn đầy đủ điều khoản và chưa ký.  
* Chọn vai trò (NLĐ hoặc NSDLĐ) cùng chỗ với nút Upload. Mỗi lần upload một hợp đồng.  
* Phân loại từng điều khoản theo 12 nhãn đã được định nghĩa (clause [taxonomy](https://github.com/24021368-DucAnh/ai-contract-risk-analyzer/blob/main/docs/clause_taxonomy_v03.md?plain=1)).  
* Đánh giá điều khoản có mức độ rủi ro như nào, rủi ro đó là gì (risk taxonomy).  
* Báo cáo rủi ro gồm: điều khoản rủi ro, giải thích theo luật, điều luật liên quan, mức độ nghiêm trọng, highlight trên văn bản gốc. Cho phép xuất báo cáo  
* Ẩn dữ liệu cá nhân.  
* Data Graph (đồ thị kho luật, phục vụ Retrieval & Fact-finding, tức truy xuất căn cứ pháp lý) và Clause Graph (đồ thị điều khoản của hợp đồng trong phiên, phục vụ Validation & Reasoning: kiểm tra mâu thuẫn, suy diễn điều kiện), theo yêu cầu của giảng viên. Chi tiết thiết kế ở SDD và TDD (OI-14, OI-17).  
* Disclaimer: kết quả chỉ mang tính tham khảo.

### **2.2 Ngoài phạm vi**

* Chatbot hoặc hỏi đáp tiếp sau khi có kết quả. Sản phẩm không phải chatbot.  
* Lời khuyên pháp lý, gợi ý sửa điều khoản, đề xuất thương lượng.  
* Missing-clause risks: Rủi ro thiếu hoàn toàn 1 điều khoản bắt buộc  
* So sánh các phiên bản của cùng một hợp đồng.  
* PDF scan, ảnh chụp, OCR.  
* Hợp đồng mẫu (template).  
* Hợp đồng không phải tiếng Việt.  
* Tài khoản, lịch sử lâu dài, thanh toán, gói đăng ký.  
* Nhiều phiên xử lý song song.  
* Ứng dụng di động, giao diện tiếng Anh.  
* Tự huấn luyện hoặc tự host model.  
* Quy mô và độ ổn định ở mức production.

### **2.3 Phạm vi nguồn luật**

Kho luật gồm các nhóm văn bản sau, nạp theo thứ tự ưu tiên từ 1 đến 5:

1. Bộ luật Lao động 2019 và các nghị định hướng dẫn liên quan.  
2. Nhóm luật về bảo hiểm.  
3. Nhóm luật về thuế và dữ liệu cá nhân.  
4. Luật nền về hợp đồng và doanh nghiệp, trong đó có Bộ luật Dân sự.  
5. Nhóm về chế tài và giải quyết tranh chấp.

Hệ thống chỉ được trích dẫn văn bản có trong kho (yêu cầu BR-07 và BR-15).

## **3\. Bên liên quan và định nghĩa rủi ro**

### **3.1 Bên liên quan**

| Bên liên quan | Vai trò | Mối quan tâm chính |
| :---- | :---- | :---- |
| Người lao động (NLĐ) | Người dùng cuối | Hợp đồng sắp ký có điều khoản nào bất lợi hoặc trái luật. |
| Người sử dụng lao động (NSDLĐ) | Người dùng cuối | Hợp đồng đã soạn có điều khoản nào trái luật hoặc dễ phát sinh tranh chấp, xử phạt. |
| Người phụ trách dữ liệu | Thành viên nhóm phát triển | Xây dựng và cập nhật kho luật. |
| Giảng viên hướng dẫn | Người yêu cầu và nghiệm thu | Yêu cầu có Data Graph và Clause Graph (BR-17, BR-18). |

\* Rủi ro phụ thuộc vai trò: hệ thống phải nêu đúng loại rủi ro theo góc nhìn của vai trò đã chọn, không dùng chung một danh sách cho cả hai bên.

### **3.2 Định nghĩa rủi ro**

Một điều khoản là rủi ro đối với một vai trò khi thuộc một trong ba loại:

- Trái luật (LEGAL\_VIOLATION): xung đột quy định cấm hoặc bắt buộc, hoặc vượt ngưỡng pháp luật rõ ràng có trong kho luật.  
- Bất lợi hợp pháp (UNFAVORABLE): không trái luật nhưng gây bất lợi đáng kể cho vai trò đó.  
- Mơ hồ (AMBIGUOUS): câu chữ không rõ, có khả năng dẫn đến tranh chấp.

Điều khoản có lợi hơn mức pháp luật yêu cầu cho một bên không phải rủi ro của bên đó. Cùng một điều khoản có thể không là rủi ro với bên này, hoặc là rủi ro với cả hai bên nhưng khác loại, khác mức độ và khác giải thích. Mức độ nghiêm trọng (HIGH, MEDIUM, LOW) theo rubric ở SRS 2.3. Danh sách nhãn rủi ro thuộc risk taxonomy (BRD 8.2).

### 

### **3.3 Năm điều khoản mẫu theo vai trò**

Bảng dưới minh họa cách hai vai trò cho kết quả khác nhau trên cùng một điều khoản. Đây là ca nghiệm thu BO-3 (§8.6). Kết quả kỳ vọng chỉ mang tính minh họa; người phụ trách dữ liệu phải xác minh lại với văn bản luật gốc trong kho trước khi đưa vào bộ test.

| STT | Điều khoản mẫu | Căn cứ (Bộ luật Lao động 2019\) | Với NLĐ | Với NSDLĐ |
| :---- | :---- | :---- | :---- | :---- |
| 1 | "Mỗi lần đi làm muộn, NLĐ bị phạt 100.000 đồng, trừ trực tiếp vào lương tháng." | Điều 127: cấm phạt tiền, cắt lương thay việc xử lý kỷ luật | Trái luật, HIGH: lương bị trừ không có căn cứ | Trái luật, HIGH: vi phạm điều cấm, có nguy cơ bị xử phạt |
| 2 | "Lương thử việc bằng 70% mức lương chính thức." | Điều 26: ít nhất 85% mức lương của công việc đó | Trái luật, HIGH: bị trả thấp hơn mức tối thiểu | Trái luật, HIGH: có nguy cơ bị xử phạt |
| 3 | "NLĐ giao bản chính bằng tốt nghiệp để công ty giữ trong suốt thời gian làm việc." | Điều 17 khoản 1: cấm giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ | Trái luật, HIGH: mất quyền kiểm soát giấy tờ, bị ràng buộc khi muốn nghỉ việc | Trái luật, HIGH: vi phạm điều cấm |
| 4 | "Hợp đồng 24 tháng; NLĐ chỉ cần báo trước 3 ngày làm việc khi nghỉ việc." | Điều 35 khoản 1 điểm b: báo trước ít nhất 30 ngày với hợp đồng từ 12 đến 36 tháng | LOW: không bất lợi trực tiếp, nhưng điều khoản trái luật nên không đáng tin cậy làm căn cứ nghỉ sớm | Trái luật, HIGH: dễ phát sinh tranh chấp khi NLĐ nghỉ đột xuất |
| 5 | "Lương thử việc bằng 100% mức lương chính thức." | Điều 26: ít nhất 85% mức lương của công việc đó | Không rủi ro | Không rủi ro pháp lý: cao hơn mức tối thiểu hợp pháp |

*\* Nguồn đối chiếu: trang [Doanh nghiệp có được phạt tiền nhân viên không?](https://thuvienphapluat.vn/lao-dong-tien-luong/doanh-nghiep-co-duoc-phat-tien-nhan-vien-khong-63945.html) cho Điều 124 và Điều 127\. Điều 25 và 26 ([CareerLink](https://www.careerlink.vn/cam-nang-viec-lam/luat-lao-dong/luong-thu-viec-toi-thieu-bao-nhieu-phan-tram)), Điều 17 ([Thư Viện Pháp Luật](https://thuvienphapluat.vn/hoi-dap-phap-luat/dang-thu-viec-cong-ty-co-duoc-giu-cmnd-ban-goc-khong-357958.html)), Điều 35 ([LuatVietnam](https://luatvietnam.vn/tin-tuc-doanh-nghiep/co-phai-nguoi-lao-dong-duoc-don-phuong-cham-dut-hop-dong-khong-can-ly-do-2767-85777-legal.html)).*

## **4\. Quy trình người dùng**

### **4.1 Luồng chính**

1. Người dùng mở web app, không cần đăng nhập. Màn hình hiển thị disclaimer và thông báo về dữ liệu cá nhân.  
2. Chọn vai trò (NLĐ hoặc NSDLĐ) ở cạnh nút Upload.  
3. Upload một file hợp đồng.  
4. Hệ thống kiểm tra định dạng, kích thước và việc file có text.  
5. Hệ thống trích văn bản thô, ẩn dữ liệu cá nhân (PII Masking), thực hiện Clause Segmentation (tách điều khoản giữ nguyên tọa độ/offset văn bản gốc), phân loại loại điều khoản (Clause Classification qua Gemini Flash).  
6. Hệ thống phân tích rủi ro theo vai trò, đối chiếu với kho luật.  
7. Hệ thống hiển thị báo cáo: danh sách điều khoản rủi ro, highlight trên văn bản gốc.  
8. Người dùng có thể chọn xuất kết quả ra file PDF/docx  
9. Khi phiên kết thúc, dữ liệu bị xóa theo mục 7\.

### **4.2 Luồng ngoại lệ**

| Tình huống | Hành vi mong muốn |
| :---- | :---- |
| Định dạng không hỗ trợ | Từ chối, nêu rõ định dạng được hỗ trợ |
| File vượt giới hạn dung lượng hoặc số trang | Từ chối, nêu giới hạn |
| PDF không có text (scan, ảnh) | Báo chưa hỗ trợ file scan |
| Nội dung không giống HĐLĐ | Báo và không phân tích |
| Lỗi hoặc quá thời gian khi gọi LLM | Báo lỗi, cho thử lại, không hiển thị kết quả dở dang |
| Không phát hiện rủi ro | Hiển thị kết quả đó kèm disclaimer, không khẳng định hợp đồng an toàn |
| Hệ thống đang xử lý phiên khác | Từ chối phiên mới, báo thử lại sau. |
| Phiên hết hạn (60 phút không hoạt động) | Dữ liệu đã bị xóa, báo phiên hết hạn và mời mở phiên mới. |

## 

## **5\. Yêu cầu nghiệp vụ**

Tất cả yêu cầu dưới đây là bắt buộc (Must). Dự án không có yêu cầu mức Should hay Could.

| ID | Yêu cầu |
| :---- | :---- |
| BR-01 | Người dùng chọn vai trò NLĐ hoặc NSDLĐ trước khi upload. Không thể đổi vai trò trong khi đang phân tích. |
| BR-02 | Hệ thống nhận file PDF và DOCX có text. Một phiên chỉ phân tích một hợp đồng. Có thể xuất kết quả ra file PDF/docx. |
| BR-03 | Hệ thống từ chối file scan, ảnh và định dạng khác; từ chối HĐ không phải HĐLĐ. kèm thông báo rõ ràng. File bị từ chối \-\> kết thúc phiên; muốn thử file khác phải mở phiên mới |
| BR-04 | Hệ thống ẩn dữ liệu cá nhân trước khi gửi nội dung cho LLM bên thứ ba, đồng thời giữ lại thông tin cần cho việc đánh giá rủi ro (mục 7). |
| BR-05a | Mỗi rủi ro trích nguyên văn điều khoản trong hợp đồng (từ văn bản trích xuất), không diễn đạt lại. |
| BR-05b | Hệ thống lưu vị trí (character offset) của từng điều khoản trên văn bản trích xuất để highlight (BR-09). Vị trí do hệ thống tính, không do LLM tạo. |
| BR-05c | Đầu ra của mỗi bước xử lý ở dạng cấu trúc chuẩn (Structured Output, JSON Schema) đặt trong thư mục schemas của pipeline (hiện là ai\_pipeline/schemas). Schema có version và khai báo các trường version (SRS FR-29). |
| BR-06 | Mỗi rủi ro có giải thích vì sao đó là rủi ro, dựa trên luật và theo vai trò đã chọn. |
| BR-07 | Mỗi rủi ro nêu điều luật liên quan (tên văn bản, điều, khoản). Chỉ trích dẫn văn bản có trong kho luật. |
| BR-08 | Mỗi rủi ro có mức độ nghiêm trọng theo thang do đã định nghĩa (H/M/L). Mức độ có thể khác nhau giữa hai vai trò. Rủi ro chưa đủ căn cứ không được gán mức độ |
| BR-09 | Các rủi ro được highlight trên văn bản đã trích xuất từ file gốc của người dùng (canonical text), bấm vào để xem chi tiết. Giao diện ghi rõ đây là văn bản trích xuất, không phải file gốc |
| BR-10 | Mọi màn hình kết quả hiển thị disclaimer: thông tin chỉ mang tính chất tham khảo, không phải tư vấn pháp lý. Hệ thống không kiểm tra rủi ro do thiếu điều khoản. |
| BR-11 | Nội dung báo cáo chỉ phân tích và liệt kê rủi ro. Không đưa lời khuyên pháp lý, không gợi ý sửa điều khoản. |
| BR-12 | Giao diện có dòng thông báo ngắn về việc xử lý dữ liệu cá nhân (nội dung đề xuất ở Phụ lục A). |
| BR-13 | Dữ liệu hợp đồng và kết quả bị xóa khi phiên kết thúc (mục 7). |
| BR-14 | Kho luật do Người phụ trách dữ liệu duy trì. Mỗi văn bản ghi phiên bản và ngày hiệu lực. Cập nhật kho luật  đòi hỏi sửa mã nguồn |
| BR-15 | Khi kho luật không đủ căn cứ cho một nhận định, hệ thống không tự suy ra điều luật. Nhận định đó được gắn nhãn ‘chưa đủ căn cứ’, không gán mức . Phải nói rõ trong kết quả trả về. |
| BR-16 | Hệ thống giới hạn dung lượng file, số điều khoản mỗi hợp đồng và số lượt gọi LLM mỗi ngày để chi phí vận hành không vượt phần ngân sách vận hành (\$5, mục 6). Vượt trần thì từ chối phiên mới; phiên đang chạy vẫn hoàn tất. |
| BR-17 | Hệ thống có Data Graph: biểu diễn văn bản, điều, khoản, điểm của kho luật và quan hệ giữa chúng (cấu trúc, dẫn chiếu, hướng dẫn thi hành), dùng để mở rộng và xếp hạng ứng viên căn cứ khi truy xuất. Truy xuất vẫn chỉ trả điều luật có trong kho và đang hiệu lực (BR-07), và hệ thống vẫn chạy đúng khi tắt phần mở rộng này. |
| BR-18 | Hệ thống có Clause Graph: biểu diễn các điều khoản của hợp đồng đang phân tích và quan hệ giữa chúng. Tạo cục bộ, chỉ chứa mã định danh điều khoản và loại quan hệ, xóa cùng phiên (BR-13), không được làm đổi nội dung trích hay vị trí (BR-05a, BR-05b). Mục đích: kiểm tra mâu thuẫn và suy diễn điều kiện giữa các điều khoản (Validation & Reasoning); cách dùng chi tiết ở các bước sau do SDD và TDD xác định (OI-14). |

## **6\. Yêu cầu phi chức năng**

* Hiệu năng: mục tiêu tối đa 2 phút cho hợp đồng 15 trang (đề xuất). Hiển thị trạng thái xử lý trong lúc chờ.  
* Giới hạn file: đề xuất 10MB và 30 trang để kiểm soát chi phí và độ trễ.  
* Hệ thống chỉ cam kết xử lý một phiên tại một thời điểm; phiên mới bị từ chối khi đang có phiên xử lý. Dữ liệu giữa các phiên cách ly hoàn toàn.

* Tương thích: trình duyệt máy tính bản mới nhất (Chrome, Edge, Firefox). Không hỗ trợ di động.

* Ngôn ngữ: giao diện và nội dung phân tích hoàn toàn bằng tiếng Việt.

* Độ tin cậy: kết quả dở dang không bao giờ được hiển thị như kết quả cuối; mỗi phiên được thử lại thủ công tối đa 2 lần khi lỗi.

* Chi phí: ngân sách dành cho hosting, backend và API LLM: \$20. Cần giới hạn dung lượng file để kiểm soát chi phí API.  
* Bảo trì: cập nhật kho luật không đòi hỏi sửa mã nguồn. Clause taxonomy và risk taxonomy được quản lý tách biệt Cạnh của Data Graph là dữ liệu đi cùng kho luật, cập nhật không sửa mã nguồn.

## **7\. Dữ liệu cá nhân và bảo mật**

### **7.1 Luồng xử lý dữ liệu**

Luồng xử lý dữ liệu: file được upload, hệ thống trích văn bản, ẩn dữ liệu cá nhân ngay trong hệ thống của nhóm, chỉ văn bản đã ẩn được gửi cho LLM bên thứ ba, kết quả trả về được ánh xạ lại vào vị trí trong văn bản gốc để highlight, và cuối cùng toàn bộ dữ liệu bị xóa.

### **7.2 Dữ liệu cần ẩn và cần giữ**

**Cần ẩn:** họ tên, ngày sinh, số CCCD hoặc hộ chiếu, địa chỉ cư trú, số điện thoại, email, số tài khoản, tên pháp nhân.

**Cần giữ:** mức lương và phụ cấp, thời hạn hợp đồng, thời giờ làm việc, chức danh, địa bàn làm việc ở cấp tỉnh, v.v. Đây chính là dữ liệu cần để phát hiện rủi ro. Nếu ẩn hết mọi con số và địa danh thì phân tích sẽ mất độ chính xác.

### **7.3 Ngưỡng ẩn dữ liệu cá nhân**

| Nhóm dữ liệu | Chỉ số | Ngưỡng |
| :---- | :---- | :---- |
| Số CCCD hoặc hộ chiếu, số điện thoại, email, số tài khoản | Recall khi che | ≥ 99% |
| Họ tên, ngày sinh, địa chỉ cư trú, tên pháp nhân | Recall khi che | ≥ 90% |
| Trường cần giữ (lương, phụ cấp, thời hạn, thời giờ, chức danh, tỉnh, từ chỉ vai trò) | Tỷ lệ giữ nguyên | ≥ 95% |

Đo trên nội dung thực tế gửi cho LLM, bằng tập kiểm thử riêng có gold span (mục 10). Đây là mục tiêu cho demo, không phải cam kết với người dùng (Phụ lục A).

### **7.4 Lưu và xóa**

**Lưu và xóa:** file gốc và kết quả chỉ tồn tại trong phiên. Đề xuất xóa khi người dùng đóng phiên hoặc sau 60 phút không hoạt động. Nội dung hợp đồng không được ghi vào cơ sở dữ liệu hay kho bền vững; chỉ tồn tại trong bộ nhớ hoặc kho tạm bị xóa theo phiên.

### **7.5 Nhà cung cấp LLM**

**Nhà cung cấp LLM:** Hệ thống sử dụng mô hình Gemini Flash (Paid Tier) thông qua API thay vì triển khai tự lưu trữ (self-host). Demo và đánh giá dùng gói trả phí. Gói miễn phí và model chạy cục bộ chỉ dùng cho phát triển với dữ liệu đã de-identify. Model id phải được cấu hình tường minh. Judge (Claude, mục 8.5) chỉ nhận dữ liệu đã che hoặc đã de-identify.

### **7.6 Pháp lý và dữ liệu dev, test**

Pháp lý: nhóm cần xác nhận văn bản hiện hành về bảo vệ dữ liệu cá nhân áp dụng cho demo. Việc ẩn dữ liệu tự động không đạt 100%, vì vậy thông báo cho người dùng không nên cam kết tuyệt đối. Hợp đồng dùng cho dev và test là hợp đồng thật, được de-identify thủ công trước khi đưa vào kho mã.

## **8\. Đo lường chất lượng và nghiệm thu**

Đây là nguồn duy nhất cho mọi chỉ số chất lượng. SRS chỉ dẫn ID ở đây, không lặp số.

### **8.1 Nguyên tắc và giới hạn**

Nhóm không có luật sư và nhãn gold hiện có do LLM tạo. Vì vậy:

* Tầng nào kiểm tra tự động được bằng quy tắc xác định thì kiểm tự động, không dùng LLM.

* Mọi con số báo cáo phải kèm nguồn nhãn gold (người sửa, LLM gán rồi người xác minh, lỗi chèn) và kích thước tập test.

* LLM-as-a-judge chỉ dùng khi có bằng chứng trong tay (văn bản hợp đồng đã che, điều luật trong kho) và phải được hiệu chuẩn bằng người trước khi tin kết quả (M6). Judge không được dùng để quyết định false negative và không tham gia tính M5.

* Gold của taxonomy là sự đồng thuận của nhóm không có chuyên môn pháp lý, không phải chân lý pháp lý. Báo cáo phải nói rõ điều này.

Ngoài phạm vi: không đo false positive riêng. Precision nằm trong F1 của M1, M2 và M7.

### **8.2 Dữ liệu đánh giá**

| Tập | Nội dung | Dùng cho |
| :---- | :---- | :---- |
| D1 | 4 hợp đồng dev hiện có (183 điều khoản) | Phát triển, tuning prompt, few-shot; không báo số nghiệm thu |
| D2 | D1 kèm lỗi chèn riêng cho dev, câu chữ và quy định không dùng chung với T2 (tốt nhất tách quy định) | Phát triển |
| T1 | Tối thiểu 10 hợp đồng gốc, tách hoàn toàn khỏi dữ liệu dev, few-shot, prompt; đa dạng định dạng (PDF, DOCX), kiểu đánh số điều khoản, ngành và độ dài | M1, M2, M3a, M3b, M4, M6, M7, BL-1 |
| T2 | Bản sao T1 đã chèn tối thiểu 30 lỗi (8.4) | M5, M8 |

Quy tắc:

1. Số hợp đồng của T1 hiện là 10 và có thể đổi sau; khi đổi, xem lại ngưỡng và cỡ mẫu.

2. Chèn lỗi đổi văn bản, ranh giới và nhãn, nên T1 và T2 không dùng chung một bộ gold; gold segmentation của T2 được sửa lại sau khi chèn.

3. Gold segmentation: người sửa tay ranh giới điều khoản, không cần chuyên môn pháp lý.

4. Gold clause taxonomy và risk taxonomy: một LLM khác họ với LLM trong pipeline (Claude) gán trước; toàn bộ item của T1 được một thành viên xác minh độc lập theo annotation guideline và văn bản luật trong kho; chỗ bất đồng thì thảo luận và chốt. Ít nhất 20% item do hai thành viên gán độc lập để đo Cohen's kappa.

5. Clause taxonomy, risk taxonomy, severity rubric và annotation guideline phải đóng băng trước khi gán nhãn T1 (mốc MS-1). Đổi sau đó làm mất giá trị mọi số đo. Model id và phiên bản prompt được ghi lại nhưng không đóng băng.

6. Một điều khoản có thể có nhiều nhãn khác nhau.

7. Không chỉnh hệ thống dựa trên kết quả T1 và T2. Mọi chỉnh sửa làm trên D1 và D2.

### **8.3 Các chỉ số**

Một "output" là một bản ghi rủi ro gồm điều khoản, nhãn, giải thích và citation. Chỉ số về dữ liệu cá nhân nằm ở §7.3.

| ID | Chỉ số | Ngưỡng | Đơn vị so khớp | Nhãn gold | Tập | Cách đo |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| M1 | Clause segmentation F1 | ≥ 0.85 | Khoảng văn bản của một điều khoản; khớp khi IoU ký tự ≥ 0.80, ghép tham lam theo IoU giảm dần | Người sửa tay | T1 | Tự động |
| M2 | Risk classification macro-F1 | ≥ 0.80 | Bộ ba (điều khoản, vai trò, risk label) | LLM khác họ gán, người xác minh | T1 | Tự động; báo per-class; macro chỉ tính nhãn có ≥ 5 mẫu |
| M3a | Citation tồn tại và hợp lệ | 100% | Mỗi điều luật được trích | Kho luật | T1, T2 | Tự động: nằm trong candidate, thuộc kho, đúng phiên bản hiệu lực tại ngày phân tích |
| M3b | Citation liên quan đến rủi ro | ≥ 85% | Mỗi điều luật được trích | Người chấm | T1 (mẫu 40 output) | Chấm tay theo rubric relevance; dùng judge nếu M6 đạt. Báo thêm số citation LLM chọn ngoài candidate trước khi lọc |
| M4 | Trích nguyên văn và vị trí | 100% | Mỗi rủi ro | Văn bản trích xuất | T1, T2 | Tự động: đoạn trích là chuỗi con nguyên văn, offset đúng |
| M5 | Recall trên lỗi chèn | ≥ 90%, với ≥ 30 lỗi chèn | Mỗi lỗi chèn | Lỗi chèn do nhóm tạo | T2 | Tự động: đúng điều khoản, đúng vai trò, đúng nhãn |
| M6 | Judge và người trùng nhau | ≥ 80% và Cohen's kappa ≥ 0.6 | Kết quả mỗi output | Hai người chấm | T1 (mẫu 40 output) | Tỷ lệ judge trùng nhãn với người; đạt cả hai thì dùng judge cho phần còn lại |
| M7 | Clause classification macro-F1 | ≥ 0.80 | Cặp (điều khoản, clause label) | LLM khác họ gán, người xác minh | T1 | Tự động; báo per-class; macro chỉ tính nhãn có ≥ 5 mẫu |
| M8 | Retrieval recall@5 | ≥ 90% | Mỗi lỗi chèn | Điều luật gold của lỗi chèn | T2 | Tự động: điều luật gold nằm trong 5 candidate đầu. Chỉ số chẩn đoán. Báo thêm recall@5 khi tắt mở rộng qua Data Graph để thấy đóng góp của Graph (BR-17); không có ngưỡng riêng |
| BL-1 | So với LLM thông dụng | Tỷ lệ citation sai của hệ thống ≤ một nửa của baseline | Mỗi điều luật được trích | Người đối chiếu văn bản luật thật | T1 (cùng mẫu 40\) | "Sai" \= không tồn tại hoặc nội dung không khớp. Cùng hợp đồng đã che, cùng vai trò, cùng yêu cầu. Baseline: LLM thông dụng chọn ở OI-07, cấu hình cụ thể ghi trong báo cáo. |

\* Ngưỡng M2, M7 và M3b được đặt lại sau số đo dev đầu tiên (OI-09). Mọi con số báo kèm khoảng tin cậy (bootstrap) và số mẫu mỗi nhãn.

### **8.4 Đánh giá false negative bằng lỗi chèn**

Mục tiêu là ước lượng hệ thống bỏ sót bao nhiêu rủi ro mà không cần luật sư và không dùng judge.

1. Chọn các quy định trong kho luật có ngưỡng hoặc cấm đoán rõ ràng, mà người đọc văn bản luật tự kiểm chứng được. Ví dụ: lương thử việc thấp hơn mức luật cho phép, thời gian thử việc vượt mức tối đa, phạt tiền người lao động.

2. Mỗi quy định tạo ít nhất một điều khoản vi phạm, gắn với nhãn (risk taxonomy), một điều luật gold và vai trò chịu rủi ro. Tối thiểu 30 lỗi chèn cho T2, mỗi vai trò tối thiểu 10\. D2 có bộ lỗi chèn riêng.

3. Hai thành viên xác minh từng lỗi chèn với văn bản luật trước khi dùng.

4. Chèn vào hợp đồng sạch (không chứa lỗi tương ứng), ở các vị trí khác nhau.

5. M5 \= số lỗi chèn bị phát hiện đúng (đúng điều khoản, đúng vai trò, đúng nhãn) / tổng số lỗi chèn. Khớp tự động. Lỗi chèn bị gắn "chưa đủ căn cứ" vẫn tính là phát hiện nếu khớp; báo riêng tỷ lệ thiếu citation.

Với 30 lỗi chèn, ngưỡng 90% cho phép sót tối đa 3\. Giới hạn: lỗi tự chèn rõ ràng hơn rủi ro thực tế và chỉ bao phủ các quy định có ngưỡng rõ. M5 là recall trên rủi ro có căn cứ rõ, không phải tỷ lệ bỏ sót trên mọi rủi ro.

Judge không tham gia tính M5. Có thể dùng judge để gợi ý các điều khoản nghi bị bỏ sót cho người rà soát, nhưng kết quả đó không tính vào chỉ số.

### **8.5 LLM-as-a-judge và M6**

Judge dùng để chấm hai việc trên các bản ghi rủi ro của T1: giải thích có đúng theo căn cứ và đúng vai trò không, và citation có liên quan không. Judge không chấm recall.

* Model: Claude. chỉ nhận dữ liệu đã che hoặc đã de-identify của bộ test, kèm điều khoản và điều luật trong kho làm bằng chứng.

* Hiệu chuẩn: lấy 40 output; hai thành viên chấm độc lập theo ba mức Đúng, Đúng một phần, Sai, rồi thảo luận chốt nhãn. Cho judge chấm đúng 40 output đó. Tính tỷ lệ judge trùng nhãn đã chốt (32/40 là 80%) và Cohen's kappa; báo thêm kappa giữa hai người chấm.

* Quyết định: đạt cả hai ngưỡng ở M6 thì tin judge cho phần còn lại của T1. Không đạt thì không báo số của judge; chấm tay một mẫu nhỏ hơn và nêu rõ cỡ mẫu. Với 40 mẫu, tỷ lệ trùng 80% có khoảng tin cậy 95% rộng (xấp xỉ ±12 điểm phần trăm), nên phải báo kèm khoảng tin cậy. 

* M6 đo độ tin cậy của judge, không phải độ chính xác của hệ thống. Độ chính xác của hệ thống là tỷ lệ output được chấm Đúng trên cả tập.

* Chi phí judge nằm trong ngân sách đánh giá (§6). Chọn model Claude cụ thể ở OI-11.

### **8.6 Tiêu chí nghiệm thu**

* Luồng chính chạy trọn vẹn cho cả hai vai trò trên toàn bộ T1: mỗi hợp đồng đạt trạng thái hoàn thành sau tối đa 2 lần thử lại thủ công mỗi phiên.

* BO-3: năm ca mẫu ở §3.3 cho kết quả khác nhau giữa hai vai trò đúng như kỳ vọng đã được người phụ trách dữ liệu xác minh (đạt hoặc không đạt, không tính tỷ lệ).

* Đạt các ngưỡng M1 đến M8 và ngưỡng ở §7.3, hoặc có giải trình nếu chưa đạt. BL-1 nếu chưa bị cắt theo §9.5.

* Mọi yêu cầu BR-01 đến BR-16 được kiểm tra và có kết quả.

* Báo cáo đánh giá nêu rõ phương pháp, nguồn gold, cỡ tập và giới hạn của phép đo.

* Không chỉnh hệ thống dựa trên kết quả T1 và T2.

## **9\. Ràng buộc, giả định, phụ thuộc**

### **9.1 Ràng buộc**

* 10 tuần, 5 người: 8 tuần xây dựng đến demo (tuần đầu bắt đầu 12/10/2026, hạn demo 06/12/2026) và 2 tuần đánh giá T1, T2 và báo cáo (9.4). Đã xác nhận 12/10/2026 (OI-15).  
* Không huấn luyện hoặc tự host model. Một số bước của pipeline gọi API LLM bên thứ ba.  
* Ngân sách hạn chế (\$20)  
* Không có luật sư hoặc chuyên gia pháp lý rà soát.  
* Web máy tính, chỉ tiếng Việt.

### **9.2 Giả định do tài liệu đặt ra**

| ID | Giả định |
| :---- | :---- |
| A1 | Loại hợp đồng chấp nhận: HĐLĐ tiếng Việt, gồm cả hợp đồng thử việc, phụ lục nằm trong cùng file. |
| A2 | Giới hạn file 10MB và 30 trang; DOCX 10MB 100k kí tự. |
| A3 | Kết quả của  hợp đồng đã phân tích có thể được xuất ra file PDF/docx. Sẽ mất khi phiên kết thúc. |
| A4 | Ngưỡng thời gian: \< 2 phút cho hợp đồng 15 trang. 90% phiên được test đạt được hiệu năng này |
| A5 | Thang mức độ gồm 3 bậc (H/M/L) |
| A6 | Văn bản không giống HĐLĐ bị từ chối. |
| A7 | Một phiên gắn với một vai trò và một hợp đồng; đổi vai trò hoặc đổi file là mở phiên mới. |
| A8 | Hệ thống phục vụ một phiên đang xử lý tại một thời điểm. |

### 

### **9.3 Phụ thuộc**

* API LLM của nhà cung cấp bên thứ ba.  
* Kho luật do người phụ trách dữ liệu xây dựng.  
* Dịch vụ hosting cho web và backend.

### **9.4 Mốc thời gian (đề xuất)**

| Mốc | Ngày | Nội dung |
| :---- | :---- | :---- |
| MS-1 | 25/10/2026 (hết tuần 2) | Đóng băng clause taxonomy, risk taxonomy, severity rubric, annotation guideline (SRS DEC-10). Risk taxonomy có người phụ trách và bản đầu (OI-01). Chốt danh mục kho luật tầng 1 (OI-02). |
| MS-2 | 08/11/2026 (hết tuần 4) | Chốt các cấu hình còn mở (SRS OI-03 đến OI-05, OI-09 đến OI-12). Bản đầu kho luật tầng 1 và Data Graph cấu trúc. Pipeline đến Clause Classification chạy trên D1. Che dữ liệu cá nhân có số đo đầu trên D1. |
| MS-3 | 06/12/2026 (hết tuần 8) | Demo full luồng cho cả hai vai trò. Khóa phiên bản hệ thống và ghi commit hash (SRS EV-07). |
| MS-4 | 13/12/2026 (hết tuần 9) | Chạy xong T1, T2, M1 đến M8, hiệu chuẩn judge (M6). |
| MS-5 | 20/12/2026 (hết tuần 10) | Báo cáo đánh giá và bảo vệ. |

MS-1 và MS-3 lấy từ SRS (DEC-10, DEC-14, EV-07); MS-2, MS-4, MS-5 là đề xuất chờ OI-05. Gán nhãn gold cho T1 và T2 chạy song song từ sau MS-1 đến trước MS-4 và không dùng gold để chỉnh hệ thống (8.2, quy tắc 7).

### **9.5 Thứ tự cắt tính năng**

Khi trễ tiến độ, nhóm cắt từ trên xuống dưới và không cắt hạng mục khác khi chưa cắt hết hạng mục phía trên. Hạng mục 4 cần chủ sở hữu BRD duyệt vì BR-02 yêu cầu cả hai định dạng. Hạng mục 5 cần chủ sở hữu BRD và giảng viên duyệt vì BR-17 và BR-18 do giảng viên yêu cầu.

1. BL-1, so sánh với LLM thông dụng (§8.3).

2. Stage resume: retry chạy lại từ đầu, vẫn giữ hạn 2 lần thử lại thủ công mỗi phiên.

3. LLM hỗ trợ tách điều khoản: chỉ dùng luật và fallback theo paragraph.

4. Export PDF: chỉ giữ DOCX.

5. Graph: chỉ giữ cạnh cấu trúc; bỏ cạnh dẫn chiếu và hướng dẫn giữa các điều luật (REFERS\_TO, GUIDES) và cạnh dẫn chiếu giữa các điều khoản (SRS FR-30, FR-31). Data Graph và Clause Graph vẫn phải có.

### **9.6 Phân công (đề xuất)**

Theo vai trò ghi trong tài liệu của repo; chốt ở OI-04.

| Mảng | Phụ trách đề xuất |
| :---- | :---- |
| Tách và phân loại điều khoản (Clause AI) | Người 1 |
| Dữ liệu: kho luật, gold, nguồn cạnh Data Graph | Người 2 |
| Risk, severity, giải thích, citation (Risk AI) | Người 3 |
| Hệ thống: extraction, phiên, API, export | Người 4 |
| Giao diện, highlight, báo cáo | Người 5 |
| Chưa có chủ: risk taxonomy (OI-01), che dữ liệu cá nhân (SRS FR-10), dựng Data Graph và Clause Graph, harness đánh giá, pháp lý dữ liệu cá nhân (OI-03) | Cả nhóm |

## **10\. Rủi ro dự án**

| Rủi ro | Tác động | Giảm thiểu |
| :---- | :---- | :---- |
| Phạm vi luật quá rộng so với 10 tuần và 5 người | Kho luật thiếu hoặc sai, trích dẫn không đủ | Nạp theo tầng ưu tiên, chốt danh mục sớm, chỉ trích dẫn văn bản có trong kho |
| Không có chuyên gia pháp lý | Sai nghĩa pháp lý khó phát hiện | Disclaimer, tự rà soát mẫu, nêu rõ hạn chế khi bảo vệ |
| Ẩn dữ liệu bỏ sót hoặc làm mất thông tin cần thiết | Lộ dữ liệu cá nhân hoặc phân tích sai | Tập kiểm thử riêng cho dữ liệu cá nhân, giữ các trường số liệu, không cam kết tuyệt đối |
| Đo tỷ lệ bỏ sót bằng LLM-Judge thiếu tin cậy | Kết luận chất lượng khó đứng vững khi bảo vệ | Judge khác họ model, hiệu chuẩn thủ công, báo cáo kèm giới hạn |
| Chi phí và độ trễ API LLM | Vượt ngân sách, phản hồi chậm | Giới hạn file và lượt phân tích, lưu đệm kết quả trung gian |
| Luật thay đổi | Kết quả lỗi thời | Ghi phiên bản và hiệu lực từng văn bản, người phụ trách dữ liệu cập nhật |
| Tập hợp đồng kiểm thử nhỏ | Kết quả đo không đại diện | Bổ sung hợp đồng đa dạng trước khi đo |
| Hợp đồng có cấu trúc dị thường (Hard-cases): điều khoản quá dài, nhiều ý lồng nhau (hybrid), wording lạ, hoặc hoàn toàn không có tiêu đề/heading (chỉ có gạch đầu dòng). | Tách sai ranh giới điều khoản, phân loại nhầm nhãn, làm tụt F1 \< 0.85 .  | 1\. Kết hợp Regex nhận diện cấu trúc \+ LLM semantic chunking. 2\. Xây dựng chiến lược fallback: nếu không có heading thì phân đoạn theo paragraph/ngữ nghĩa. 3\. Bổ sung các ca dị thường này vào tập Prompt Few-shot để mô hình học mẫu. |
| Refine pipeline làm đổi thiết kế muộn | SDD, TDD và mã lệch nhau | Mọi thay đổi pipeline phải giữ các invariant ở SRS 4.2 (SRS OI-01) |
| Graph do giảng viên yêu cầu làm phình việc kho luật và retrieval | Trễ kho luật và truy xuất, kéo theo M8 và M3 | Graph là lớp mở rộng trên retrieval nền; hệ thống chạy được khi tắt Graph; cạnh cấu trúc sinh tự động; cạnh dẫn chiếu là hạng mục cắt số 5 (9.5) |
| Codebase hiện tại là thiết kế tuần 1, lệch tài liệu | Làm tiếp theo bản cũ rồi phải làm lại | Danh sách thay đổi ở SRS Phụ lục C và Phụ lục C của BRD; làm schema và mock mới trước để các mảng không bị chặn |

## **Phụ lục A: Nội dung hiển thị đề xuất**

**Disclaimer:** Kết quả do AI tạo ra chỉ mang tính tham khảo, không phải tư vấn pháp lý và không thay thế ý kiến của luật sư. Hệ thống có thể bỏ sót hoặc đánh giá chưa chính xác một số điều khoản.

**Thông báo dữ liệu:** Hệ thống tự động ẩn thông tin cá nhân nhận dạng được (họ tên, số giấy tờ, địa chỉ, thông tin liên lạc) trước khi gửi nội dung đi phân tích. Dữ liệu được xóa khi kết thúc phiên.

## **Phụ lục B: Thuật ngữ**

| Thuật ngữ | Ý nghĩa |
| :---- | :---- |
| NSDLĐ | Người sử dụng lao động |
| Kho luật | Tập văn bản pháp luật được nạp vào hệ thống, là nguồn duy nhất để trích dẫn |
| Phiên | Một lần làm việc trên web app với một vai trò và một hợp đồng. Kết thúc khi người dùng bấm kết thúc hoặc sau 60 phút không hoạt động. Đổi vai trò hoặc đổi file là mở phiên mới |
| Canonical text | Văn bản chuẩn duy nhất trích từ tệp gốc; dùng để tách điều khoản, lưu vị trí và highlight |
| Clause Segmentation | Tách hợp đồng thành các điều khoản, giữ vị trí trên canonical text |
| Clause taxonomy | Tập 12 nhãn mô tả loại điều khoản |
| Risk taxonomy | Tập nhãn mô tả loại rủi ro theo vai trò; tách biệt với clause taxonomy |
| Gold | Nhãn chuẩn dùng để chấm: người sửa tay, LLM gán rồi người xác minh, hoặc lỗi chèn |
| Lỗi chèn | Điều khoản vi phạm do nhóm tạo, chèn vào hợp đồng sạch để đo recall (8.4) |
| D1, D2, T1, T2 | Các tập dữ liệu dev và test (8.2) |
| Output | Một bản ghi rủi ro gồm điều khoản, nhãn, giải thích và citation (8.3) |
| LLM-as-a-judge | Dùng một LLM để chấm chất lượng đầu ra theo rubric; chỉ dùng sau khi hiệu chuẩn (M6) |
| Data Graph | Đồ thị trên kho luật: nút là điều luật (đơn vị trích dẫn được), cạnh là quan hệ cấu trúc, dẫn chiếu, hướng dẫn thi hành. Phục vụ Retrieval & Fact-finding: mở rộng và xếp hạng ứng viên khi truy xuất (BR-17) |
| Clause Graph | Đồ thị trên các điều khoản của một hợp đồng trong một phiên; chỉ chứa mã điều khoản và loại quan hệ; xóa cùng phiên. Phục vụ Validation & Reasoning: kiểm tra mâu thuẫn, suy diễn điều kiện (BR-18) |

INSTRUCTION:

## **11\. Open Issues**

Mục chưa chốt. Mỗi mục có người chịu trách nhiệm, hạn và giá trị tạm dùng cho đến khi chốt.

| ID | Vấn đề | Chịu trách nhiệm | Giá trị tạm dùng |
| :---- | :---- | :---- | :---- |
| OI-01 | Risk taxonomy chưa tồn tại (clause taxonomy 12 nhãn đã có) | Chưa phân công | Dựng bản đầu từ các quy định dùng cho lỗi chèn |
| OI-02 | Danh mục kho luật tầng 1 và các Điều dùng cho lỗi chèn | Người phụ trách dữ liệu | Bộ luật Lao động 2019 và nghị định hướng dẫn |
| OI-03 | Xác nhận văn bản hiện hành về bảo vệ dữ liệu cá nhân (kể cả gửi ra nhà cung cấp ở nước ngoài) và chính sách lưu, sử dụng dữ liệu của Gemini Paid Tier | Chưa phân công | Thông báo không cam kết tuyệt đối (Phụ lục A) |
| OI-04 | Phân công các mảng chưa có chủ (§9.6) | Cả nhóm | Chưa có |
| OI-05 | Xác nhận MS-2 đến MS-5 (§9.4) | Cả nhóm | Lịch đề xuất ở §9.4 |
| OI-06 | Hành vi khi hệ thống đang xử lý một phiên khác | Cả nhóm | Từ chối phiên mới kèm thông báo thử lại sau |
| OI-07 | Chọn LLM thông dụng làm baseline cho BL-1 | Cả nhóm | Chưa chọn; BL-1 là hạng mục cắt đầu tiên |
| OI-08 | Nghị định xử phạt vi phạm hành chính về lao động hiện hành tại ngày phân tích. Tra cứu ngày 12/10/2026 cho thấy có quy định xử phạt thay đổi từ 10/9/2026, chưa kiểm chứng | Người phụ trách dữ liệu | Báo cáo không nêu mức phạt |
| OI-09 | Đặt lại ngưỡng M2, M7, M3b sau số đo dev đầu tiên | Cả nhóm | 0.80, 0.80, 85% |
| OI-10 | Số hợp đồng của T1 và số lỗi chèn của T2 có thể đổi | Cả nhóm | Xem lại ngưỡng và cỡ mẫu (§8.2) |
| OI-11 | Chọn model Claude cụ thể làm judge và phần ngân sách | Cả nhóm | Một model Claude, chi phí trong \$15 |
| OI-12 | Mô hình chi phí; trần số điều khoản; ngưỡng ký tự DOCX theo số đo trên D1 | Cả nhóm | 150 điều khoản; 100.000 ký tự |
| OI-13 | Refine pipeline: xem SRS OI-01 | Cả nhóm | Pipeline ở SRS 2.2; mọi thay đổi giữ các invariant |
| OI-14 | Đã chốt 12/10/2026: Data Graph phục vụ Retrieval & Fact-finding; Clause Graph phục vụ Validation & Reasoning (kiểm tra mâu thuẫn, suy diễn điều kiện). Còn mở: thiết kế cụ thể cách Clause Graph dùng cho kiểm tra mâu thuẫn và suy diễn điều kiện (xem OI-17) | Cả nhóm | Clause Graph có cạnh cấu trúc (SRS FR-31); chưa gắn tính năng người dùng cho đến khi SDD và TDD quyết định |
| OI-15 | Đã chốt 12/10/2026: 10 tuần là 8 tuần xây dựng đến demo cộng 2 tuần đánh giá. Còn chờ xác nhận: các mốc MS-2, MS-4, MS-5 (9.4, cũng là OI-05) | Cả nhóm | Lịch ở 9.4 |
| OI-16 | Chính sách đa nhãn: dữ liệu gold hiện một nhãn mỗi dòng, quy tắc 6 ở 8.2 cho phép nhiều nhãn (SRS OI-10) | Người phụ trách dữ liệu, Clause AI | Mỗi clause 1 đến 3 nhãn; hướng dẫn gán: ưu tiên một nhãn, thêm nhãn khi câu không tách được |
| OI-17 | Thiết kế Graph ở mức SDD và TDD (loại nút và cạnh, nguồn cạnh, số bước mở rộng; SRS OI-08, OI-09) | Cả nhóm | Theo SRS FR-30, FR-31 |
| OI-18 | Duyệt thay đổi BRD 0.5 và SRS 1.3, gồm các điều ở Phụ lục C | Chủ sở hữu BRD, SRS | Chờ duyệt |

## **Phụ lục C: Chỗ codebase hiện tại lệch BRD (ghi nhận, chưa sửa code)**

Đối chiếu ngày 12/10/2026 với snapshot ai\_pipeline, backend, docs. Snapshot không có frontend nên phần giao diện chưa đối chiếu được. Danh sách thay đổi kỹ thuật chi tiết nằm ở SRS Phụ lục C.

| Hạng mục | Codebase hiện tại | BRD yêu cầu | Xử lý đã ghi nhận |
| :---- | :---- | :---- | :---- |
| Nhà cung cấp LLM | Gemini free tier và Qwen qua Ollama; model mặc định ngầm | Gemini Flash gói trả phí, không tự host (7.5, 9.1) | Gói miễn phí và Qwen chỉ dùng dev với dữ liệu de-identify; demo và đánh giá dùng gói trả phí |
| Lưu trữ | PostgreSQL lưu nội dung hợp đồng lâu dài | BR-13: xóa khi hết phiên | Không lưu nội dung hợp đồng ở kho bền vững (7.4; SRS NFR-DATA-04) |
| Định dạng nhận | Chỉ PDF | PDF và DOCX (BR-02) | Bổ sung DOCX |
| Nhãn và độ tin cậy | Điểm tự tin, tier theo nhãn, review\_zone; dữ liệu gold một nhãn mỗi dòng | Nhãn clause theo taxonomy; quy tắc 6 ở 8.2 | Bỏ điểm, tier, review\_zone; chốt chính sách đa nhãn (OI-16) |
| Tách điều khoản | LLM đọc văn bản chưa che, tự trả nguyên văn, hệ thống dò lại vị trí | BR-04, BR-05a, BR-05b: che trước, hệ thống tự tính vị trí | Tách bằng luật cấu trúc, LLM chỉ phân loại theo mã điều khoản |
| Kế hoạch dữ liệu | DATA\_PLAN: dữ liệu tổng hợp, 8 nhãn, 40 đến 50 hợp đồng | 8.2: D1, D2, T1, T2 với hợp đồng thật de-identify | DATA\_PLAN lỗi thời; thay bằng con trỏ về 8.2, giữ annotation guideline |
| Nguồn nhãn clause | Bốn bản (repo dữ liệu, taxonomy.py, docs, enum schema) | Taxonomy đóng băng ở MS-1 (8.2, quy tắc 5) | Một nguồn duy nhất trong code; enum schema sinh từ đó hoặc có test đối chiếu |
| Graph | Chưa có | BR-17, BR-18 | Thêm vào kế hoạch; thiết kế ở SDD và TDD |

## 