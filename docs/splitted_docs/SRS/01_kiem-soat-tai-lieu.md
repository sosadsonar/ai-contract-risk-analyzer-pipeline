<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > Kiểm soát tài liệu | 9331 ký tự | trước: 00_srs-ai-labor-contract-risk-analyzer-phien-ban-1-4.md | sau: 02_1-gioi-thieu.md -->

## Kiểm soát tài liệu

| Phiên bản | Ngày | Thay đổi | Lý do | Người duyệt |
|---|---|---|---|---|
| 1.1 | 10/10/2026 | Cập nhật theo review SRS 1.0 | Không ghi chi tiết | Không ghi |
| 1.2 | 12/10/2026 | Xem danh sách bên dưới | Review BRD 0.3 và SRS 1.1 ngày 12/10/2026; BRD 0.4; Decision Log | Chủ sở hữu SRS (chờ duyệt) |
| 1.3 | 12/10/2026 | Xem danh sách bên dưới | Yêu cầu của giảng viên (Data Graph, Clause Graph); đối chiếu codebase hiện tại; BRD 0.5 | Chủ sở hữu SRS (chờ duyệt) |
| 1.4 | 13/10/2026 | Xem danh sách bên dưới | Backport review kỹ thuật và TDD 0.2; sửa lifecycle upload/retry, graph evidence, offset và evaluation | Chủ sở hữu SRS (chờ duyệt) |

Thay đổi chính trong 1.4:

* Thống nhất Create/Upload theo lifecycle bất đồng bộ: các lỗi admission (thiếu role, SYSTEM_BUSY, quota, rate limit) không tạo phiên; sau khi admission thành công thì tạo session và mọi lỗi file/phạm vi/segmentation chuyển session sang REJECTED, quan sát qua Get Status (FR-02 đến FR-06, FR-09, mục 6 và 9).
* Làm rõ RiskResult: `risk_labels` vẫn là output AI, còn `risk_basis` được backend suy ra xác định từ risk taxonomy; bổ sung `related_clause_ids` tùy chọn và ContextResolutionTrace để chứng minh Clause Graph thực sự cung cấp context cho Risk stage mà không trao quyền quote/span cho AI (FR-13, FR-31, 4.1, 4.3, EV-09).
* Sửa retry/state: FAILED do local stage retry về VALIDATING, FAILED do processing stage retry về PROCESSING; retry phải giành lại processing slot atomically, SYSTEM_BUSY không làm tăng retry counter; RETRY_LIMIT_EXCEEDED chỉ dùng cho lần thử thủ công thứ 3 (FR-21, FR-26, 6).
* Khóa span theo Unicode code point sau NFC và clause span không chồng lấn; bổ sung rule loại trừ dẫn chiếu pháp luật khỏi Clause Graph REFERS_TO và yêu cầu phát hiện PDF font cũ TCVN3/VNI bằng fixture/heuristic chứ không chỉ U+FFFD (FR-08, FR-09, FR-31, NFR-DATA-02/03).
* Export phải chứa cả disclaimer và data notice; Clause Classification không nhận role; structured output của provider được dùng cho hai LLM stage (FR-11, FR-22, FR-25).
* Bổ sung các API error phụ (`INVALID_SESSION_STATE`, `SESSION_NOT_READY`, `SESSION_REJECTED`, `SESSION_EXPIRED`, `FEATURE_NOT_ENABLED`) và làm rõ End Session trả xác nhận + EXPIRED (6.2, 9).
* Sửa EV-08 để M8 graph on/off dùng cùng candidate budget/final_k và primary run dùng predicted clause labels; thêm EV-09 cho Clause Graph context trace và EV-10 tách quota/rate-limit của evaluation khỏi product runtime.
* Demo runtime dùng một backend worker/process với session store trong memory; mọi actual provider request kể cả auto-retry được tính vào cost/call ledger; quota demo phải chốt từ D1 và cost model thay vì hard-code một con số tùy ý (NFR-SCALE-01, NFR-COST-02).

Thay đổi chính trong 1.3:

* Thêm FR-30 (Data Graph, Retrieval & Fact-finding) và FR-31 (Clause Graph, Validation & Reasoning); cập nhật FR-12, FR-24, FR-29, mục 5; thêm R-17, R-18 (DEC-21).
* Thêm NFR-DATA-04 (không lưu bền vững nội dung hợp đồng), NFR-SEC-06 (nhà cung cấp LLM, cấu hình model), NFR-MAINT-03 (dữ liệu graph) (DEC-16, DEC-19).
* FR-09, FR-11: làm rõ luật cấu trúc là mặc định và nhãn không kèm điểm tin cậy (DEC-17, DEC-18); FR-08 giới hạn fixture theo hợp đồng thật (OI-11).
* 4.1, 4.2, 4.3: thêm LegalEdge, ClauseEdge, invariant của graph, stage dựng Clause Graph.
* Thêm EV-08 (M8 có và không graph). Các tham chiếu BRD 7.3, 7.5, 7.6, 9.4, 9.5 nay có trong BRD 0.5.
* Thêm DEC-16 đến DEC-22, OI-08 đến OI-12 và Phụ lục C: danh sách thay đổi cần làm ở codebase hiện tại (chỉ ghi nhận, chưa thực hiện).

Thay đổi chính trong 1.2:

* Pipeline và R-04: che dữ liệu cá nhân trên canonical text trước, văn bản đã che có cùng độ dài, tách điều khoản trên văn bản đã che (DEC-01).
* Bỏ contract_id và analysis_id, mọi thao tác theo session_id; REJECTED là trạng thái cuối; chỉ FAILED được thử lại, tối đa 2 lần (DEC-02, DEC-03).
* FR-06 chỉ dùng luật cục bộ; FR-08 thêm các ca DOCX và PDF của hợp đồng tiếng Việt; FR-18 và RiskResult dùng evidence_status, basis_type, severity có thể null (DEC-12).
* Thêm FR-26 đến FR-29 (một phiên xử lý tại một thời điểm, trần chi phí, xử lý theo lô, ghim phiên bản).
* Bỏ NFR-SCALE-01 (5 phiên song song); thêm NFR-REPRO-01 và NFR-COST-02; NFR-SEC-01 theo BRD 7.3.
* 8 chỉ dẫn ID chỉ số của BRD 8, không lặp ngưỡng; thêm yêu cầu hỗ trợ đánh giá.
* 6 sửa state machine và mở rộng mã lỗi; 11 truy vết hai chiều; 13 Open Issues; thêm Decision Log bên dưới.

### Decision Log

| ID | Quyết định | Ngày | Người chốt | Ảnh hưởng |
|---|---|---|---|---|
| DEC-01 | Che dữ liệu cá nhân trên toàn canonical text trước khi tách điều khoản; chuỗi thay thế cùng độ dài; tách điều khoản trên văn bản đã che | 12/10/2026 | Nhóm | R-04, FR-09, FR-10, 4 |
| DEC-02 | REJECTED là trạng thái cuối, muốn thử lại phải mở phiên mới; FAILED được thử lại thủ công tối đa 2 lần | 12/10/2026 | Nhóm | 6, FR-21 |
| DEC-03 | Bỏ contract_id và analysis_id; một phiên một hợp đồng; mọi thao tác theo session_id | 12/10/2026 | Nhóm | 4, 9 |
| DEC-04 | Highlight trên canonical text, không overlay lên PDF hoặc DOCX gốc | 12/10/2026 | Nhóm | FR-19; BRD BR-09 |
| DEC-05 | Bỏ yêu cầu 5 phiên song song; một phiên xử lý tại một thời điểm | 12/10/2026 | Nhóm | FR-26 |
| DEC-06 | Evaluation Plan nằm trong BRD 8; SRS chỉ dẫn ID | 12/10/2026 | Nhóm | 8 |
| DEC-07 | Judge dùng Claude, chạy ngoại tuyến, chỉ để chấm; M6 là điều kiện tin judge; judge không nằm trong danh sách cắt | 12/10/2026 | Nhóm | 8 |
| DEC-08 | M5 ≥ 90% với ≥ 30 lỗi chèn; F1 phân loại 0.80 đến khi có số đo dev; không có chỉ số role-differentiation | 12/10/2026 | Nhóm | 8 |
| DEC-09 | Ngân sách \$20: \$5 vận hành, \$15 đánh giá | 12/10/2026 | Nhóm | NFR-COST-01 |
| DEC-10 | Clause taxonomy, risk taxonomy, severity rubric, annotation guideline đóng băng ở MS-1 (25/10/2026) | 12/10/2026 | Nhóm | 2.3 |
| DEC-11 | FR-06 chỉ dùng luật cục bộ, không gọi LLM | 12/10/2026 | Nhóm | FR-06 |
| DEC-12 | Rủi ro thiếu căn cứ được giữ lại với evidence_status = INSUFFICIENT_EVIDENCE, severity null | 12/10/2026 | Nhóm | FR-14, FR-18, 4 |
| DEC-13 | Thứ tự cắt: BL-1, stage resume, LLM hỗ trợ tách điều khoản, export PDF | 12/10/2026 | Nhóm | 3 |
| DEC-14 | 8 tuần kể cả tuần 12/10/2026, hạn demo 06/12/2026 | 12/10/2026 | Nhóm | BRD 9 |
| DEC-15 | Không dùng mật khẩu demo; chống lạm dụng bằng trần call mỗi ngày và giới hạn tần suất theo IP | 12/10/2026 | Nhóm | FR-27 |
| DEC-16 | Nội dung hợp đồng của phiên không lưu ở cơ sở dữ liệu hay kho bền vững; chỉ ở bộ nhớ tiến trình hoặc kho tạm bị xóa theo FR-23. Bỏ PostgreSQL, SQLAlchemy, Alembic cho dữ liệu hợp đồng | 12/10/2026 | Nhóm | NFR-DATA-04, Phụ lục C |
| DEC-17 | Clause chỉ có clause_labels (1 đến 3 nhãn); bỏ type_scores, tier rủi ro theo nhãn, review_zone | 12/10/2026 | Không duyệt | FR-11, 4.1, Phụ lục C |
| DEC-18 | Tách điều khoản mặc định bằng luật cấu trúc kèm fallback paragraph; bỏ bộ định tuyến theo tỉ lệ dòng tiêu đề | 12/10/2026 | Nhóm | FR-09, Phụ lục C |
| DEC-19 | Demo và đánh giá dùng Gemini Flash gói trả phí; gói miễn phí dùng API Flash không trả phí | 12/10/2026 | Nhóm | NFR-SEC-06, FR-29 |
| DEC-20 | Danh sách nhãn clause có một nguồn duy nhất trong code; enum của JSON Schema sinh từ đó hoặc có test đối chiếu | 12/10/2026 | Nhóm | NFR-MAINT-02 |
| DEC-21 | Thêm Data Graph (phục vụ Retrieval & Fact-finding: tìm kiếm thông tin, truy vấn tri thức) và Clause Graph (phục vụ Validation & Reasoning: kiểm tra mâu thuẫn, suy diễn điều kiện) theo yêu cầu giảng viên; Data Graph là lớp trên retrieval nền, hệ thống chạy được khi tắt graph; thiết kế chi tiết ở SDD và TDD | 12/10/2026 | Nhóm | FR-12, FR-30, FR-31, BRD BR-17, BR-18 |
| DEC-22 | 10 tuần là 8 tuần xây dựng đến demo 06/12/2026 cộng 2 tuần đánh giá và báo cáo; mốc theo BRD 9.4 | 12/10/2026 | Cơ cấu 8+2 tuần đã xác nhận 12/10/2026; Nhóm | BRD 9 |
| DEC-23 | Create/Upload sau admission gate tạo session và trả sớm; các lỗi validate file/phạm vi/segmentation sau đó biểu diễn bằng state REJECTED của chính session đó, không vừa trả lỗi đồng bộ vừa có session | 13/10/2026 | Nhóm | FR-02..06, FR-09, 6, 9 |
| DEC-24 | `risk_basis` không do LLM tự khai mà backend derive từ `risk_labels` + risk taxonomy; Clause Graph cung cấp related context cho Risk stage và có ContextResolutionTrace; `related_clause_ids` trong RiskResult là tùy chọn, nếu có phải là tập con của context đã cấp | 13/10/2026 | Nhóm | FR-13, FR-31, 4, EV-09 |
| DEC-25 | Processing slot capacity=1 phải acquire atomically ở admission và acquire lại khi manual retry; FAILED local retry về VALIDATING, FAILED processing retry về PROCESSING; SYSTEM_BUSY không tăng retry counter | 13/10/2026 | Nhóm | FR-21, FR-26, 6 |
| DEC-26 | Mọi span dùng Unicode code point sau NFC; clause spans không chồng lấn. Với cấu trúc cha-con, phần text của clause cha kết thúc trước phần body thuộc clause con | 13/10/2026 | Nhóm | FR-09, 4.2, NFR-DATA-02 |
| DEC-27 | EV-08 so graph on/off với cùng final candidate budget và primary M8 dùng predicted clause labels; evaluation bypass runtime quota/rate-limit nhưng ghi cost ledger riêng | 13/10/2026 | Nhóm | FR-12, FR-30, EV-08, EV-10 |
| DEC-28 | Demo deploy một backend worker/process, không autoscale/serverless, vì session store và processing slot là process-local; CPU-heavy local work không được làm block status polling | 13/10/2026 | Nhóm | NFR-SCALE-01, NFR-PERF-02, NFR-DATA-04 |
