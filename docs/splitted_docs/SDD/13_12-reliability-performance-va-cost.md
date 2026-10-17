<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 12. Reliability, Performance và Cost | 646 ký tự | trước: 12_11-security-va-privacy-architecture.md | sau: 14_13-deployment-architecture.md -->

# 12. Reliability, Performance và Cost

* E2E target: 90% successful runs với PDF <=15 trang hoặc DOCX <=50.000 canonical characters hoàn thành <=120s.
* UI phải chuyển trạng thái VALIDATING/PROCESSING trong <=2s sau khi backend nhận upload.
* Không expose partial final report khi FAILED.
* Batching giảm số LLM calls; Data Graph/Clause Graph chạy local, không tăng số LLM calls.
* Nếu Data Graph lỗi runtime, fallback retrieval nền thay vì fail toàn phiên.
* Trần file: PDF <=10MB/30 trang; DOCX <=10MB/100.000 canonical chars; <=150 clauses.
* Budget demo: \$20, trong đó \$5 vận hành và \$15 đánh giá; quota daily phải cấu hình theo phần \$5.
