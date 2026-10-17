<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 16. Các điểm để TDD chốt | 787 ký tự | trước: 16_15-traceability-srs-component.md | sau: 18_17-rui-ro-kien-truc-va-bien-phap.md -->

# 16. Các điểm để TDD chốt

Các nội dung dưới đây không nên tiếp tục quyết định ở SDD; TDD/API Contract sẽ khóa chi tiết.

* Tên endpoint, HTTP status mapping, request/response JSON và JSON Schema version.
* Định dạng placeholder cụ thể theo từng loại PII.
* Chi tiết regex/heuristic của HĐLĐ precheck và clause segmentation.
* Batch size, mức parallelism trong một session, daily quota và IP rate limit cụ thể.
* Định dạng file legal corpus, index implementation và lexical search implementation.
* Exact formula/weight cho Data Graph ranking; SDD chỉ khóa max 1 hop và seed-first.
* Số related clauses đưa vào Risk LLM và thứ tự context từ Clause Graph.
* Cấu trúc class/module/package, exception class, test fixture format.
* Thời gian lưu tombstone EXPIRED (giá trị tạm SRS: 24 giờ).
