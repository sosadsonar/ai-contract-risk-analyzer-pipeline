

**SYSTEM DESIGN DOCUMENT**

**AI Labor Contract Risk Analyzer**

SDD phiên bản 0.1 (Draft)

Cơ sở: BRD 0.5 \+ SRS 1.3  
Ngày: 12/10/2026

| Tài liệu này thiết kế kiến trúc hệ thống ở mức SDD. Các endpoint cụ thể, JSON Schema, class/function, thư viện và cấu hình số chi tiết được khóa ở TDD/API Contract. |
| :---- |

# **Kiểm soát tài liệu**

| Mục | Giá trị |
| :---- | :---- |
| Tên tài liệu | System Design Document \- AI Labor Contract Risk Analyzer |
| Phiên bản | 0.1 \- Draft |
| Nguồn yêu cầu | BRD 0.5 (draft) và SRS 1.3 |
| Phạm vi | Thiết kế tổng thể, component, data flow, graph, security, deployment và mapping yêu cầu |
| Không thuộc SDD | HTTP endpoint cụ thể, JSON Schema chi tiết, class/function, package/thư viện cụ thể, prompt chi tiết |

# **1\. Mục đích và nguyên tắc thiết kế**

SDD chuyển các yêu cầu nghiệp vụ và yêu cầu phần mềm thành một kiến trúc có thể triển khai, đồng thời giữ nguyên các invariant và giới hạn đã chốt trong BRD/SRS.

## **1.1 Nguyên tắc kiến trúc**

* Modular Monolith: một backend triển khai duy nhất, chia module rõ ràng thay vì microservices. Lý do: nhóm 5 người, 8 tuần xây dựng, ngân sách hạn chế và chỉ một phiên xử lý tại một thời điểm.  
* Privacy by design: canonical text không rời trusted backend; chỉ masked text được gửi tới LLM bên thứ ba.  
* Backend authoritative: backend sở hữu session, span, quote, citation validation và final assembly; LLM chỉ trả structured analysis theo ID.  
* Ephemeral session data: nội dung hợp đồng, kết quả và Clause Graph chỉ tồn tại trong bộ nhớ/kho tạm theo phiên, không ghi vào kho bền vững.  
* Closed-corpus grounding: mọi citation phải xuất phát từ kho luật nội bộ, đúng phiên bản hiệu lực tại ngày phân tích.  
* Graph as augmentation, not authority: Data Graph chỉ mở rộng retrieval; Clause Graph chỉ hỗ trợ Validation & Reasoning, không được sửa quote/span.  
* Graceful fallback: Data Graph bị tắt/lỗi thì dùng retrieval nền; các tính năng cắt theo BRD không được phá luồng chính.

## **1.2 Các quyết định SDD bổ sung**

| ID | Quyết định SDD | Lý do / nguồn |
| :---- | :---- | :---- |
| SDD-01 | Backend dùng kiến trúc Modular Monolith với một Analysis Orchestrator trung tâm. | Phù hợp giới hạn 5 người, 8 tuần, một phiên xử lý. |
| SDD-02 | Session store mặc định ở bộ nhớ tiến trình; file upload chỉ dùng temp storage nếu parser yêu cầu và bị xóa theo session. | Tuân NFR-DATA-04; codebase hiện tại cần bỏ lưu contract trong PostgreSQL. |
| SDD-03 | Retrieval nền \= bảng ánh xạ clause/risk label sang provision \+ lexical search; embedding chưa thuộc baseline. | Theo giá trị tạm OI-07; embedding chỉ cân nhắc nếu M8 trên D2 không đạt. |
| SDD-04 | Data Graph được load thành adjacency index trong backend; không dùng graph database cho demo. | Giảm phạm vi; graph là dữ liệu corpus, không cần hạ tầng riêng. |
| SDD-05 | Data Graph mở rộng tối đa 1 hop từ seed candidate; seed được ưu tiên trước neighbor; trọng số chi tiết để TDD chốt. | Theo giá trị tạm OI-09; kiểm soát chi phí/độ trễ. |
| SDD-06 | Clause Graph được dùng làm Context Resolver cho Risk stage: lấy các clause liên quan trực tiếp để cung cấp masked context, không tạo thêm LLM call. | Hiện thực mục tiêu Validation & Reasoning mà không đổi pipeline hai LLM call. |
| SDD-07 | Operational metadata (RunLog, quota/rate counters) có thể lưu bền vững nhưng tuyệt đối không chứa contract content. | NFR-DATA-04 chỉ cấm nội dung phiên; NFR-COST cần log chi phí. |

# **2\. System Context**

Hệ thống gồm web frontend, một backend duy nhất, kho luật nội bộ, Gemini Flash là LLM sản phẩm và một evaluation harness ngoại tuyến. Claude chỉ dùng cho đánh giá, không nằm trong product runtime.

![](/docs/diagrams/system_context.png)

*Hình 1\. System Context*

## **2.1 Trust boundary**

* Browser \-\> Backend: dữ liệu gốc có PII, bắt buộc HTTPS trong môi trường deploy.  
* Trusted Backend: được phép giữ canonical text trong session tạm thời và thực hiện extraction, masking, segmentation, graph build, retrieval, assembly.  
* Backend \-\> Gemini: chỉ masked text và metadata cần thiết; không gửi raw/canonical text chưa che.  
* Evaluation Harness \-\> Claude: chỉ dữ liệu đã che hoặc đã de-identify; không có API judge trong sản phẩm.

# **3\. Kiến trúc tổng thể**

Backend được thiết kế thành các module độc lập theo trách nhiệm nhưng chạy trong cùng một deployment. Analysis Orchestrator điều phối state machine và pipeline; các module local không phụ thuộc LLM.

![](/docs/diagrams/system_overall.png)

*Hình 2\. Component Architecture*

## **3.1 Phân rã component**

| Component | Trách nhiệm | Ràng buộc |
| :---- | :---- | :---- |
| Web Frontend | Upload, chọn role, polling status, hiển thị canonical text/highlight, kết quả và export. | Không tự merge AI result hay tính span. |
| API / Session Controller | Nhận operation, tạo session\_id, enforce SYSTEM\_BUSY/rate/quota, expose status/result/retry/end. | Không chứa logic AI. |
| Analysis Orchestrator | Điều phối stage, state transition, retry, batch, version pinning và error mapping. | Nguồn điều phối duy nhất. |
| Ephemeral Session Store | Giữ session, canonical/masked text, clauses, Clause Graph, AI outputs tạm thời. | Không lưu bền vững; TTL 60 phút. |
| Document Processing | PDF/DOCX extraction, NFC normalization, reading order, header/footer/table handling. | Sinh canonical\_text \+ extraction\_version. |
| Scope Precheck | Luật cục bộ xác nhận tài liệu thuộc HĐLĐ. | Không gọi LLM. |
| PII Masker | Che PII trên toàn canonical text bằng placeholder cùng độ dài. | Không lưu mapping ngược. |
| Clause Segmenter | Tách clause bằng rule structural \+ paragraph fallback, backend tính span. | LLM segmentation chỉ là optional/cut item. |
| Clause Graph Builder | Dựng NEXT/PARENT\_OF/REFERS\_TO chỉ bằng clause\_id. | Ephemeral, không chứa text. |
| Clause Classification Adapter | Batch masked clauses tới LLM, validate structured output. | LLM call \#1. |
| Legal Corpus Manager | Load/validate corpus, version/effective dates, index và LegalEdge. | Fail fast khi corpus conflict. |
| Baseline Retriever | Label mapping \+ lexical search tạo seed candidates. | Hoạt động độc lập Data Graph. |
| Data Graph Service | Mở rộng/rank candidates tối đa 1 hop. | Có thể tắt; không sinh citation mới. |
| Risk Analysis Adapter | Risk labels, severity, explanation, citation selection từ candidates. | LLM call \#2. |
| Citation Validator | Existence/version/candidate validation; log citation ngoài candidate. | Backend authoritative. |
| Result Assembler | Join theo clause\_id với original\_text/span, dựng final response. | Không dùng masked text làm quote. |
| Report Exporter | Xuất DOCX/PDF theo khả năng đã chốt. | Không lưu report sau session. |
| LLM Client | Timeout 30s, auto-retry 1, model id bắt buộc, token/cost logging. | Gemini Flash paid tier demo/eval. |
| RunLog / Quota / Rate Limit | Metadata stage/call/token/cost/error; daily quota; rate limit theo IP. | Không log content/PII. |
| Evaluation Harness | Chạy pipeline như thư viện, không đi qua API/session; M1-M8/EV-08. | Dữ liệu dev/test de-identify. |

# **4\. Pipeline xử lý end-to-end**

![](/docs/diagrams/pipeline.png)

*Hình 3\. Pipeline runtime đã refine ở mức SDD*

Pipeline giữ đúng các quy tắc của SRS: PII masking trước segmentation; masked\_text cùng độ dài canonical\_text; chỉ có hai bước LLM bắt buộc; legal retrieval chạy cục bộ; backend merge theo clause\_id.

## **4.1 Trình tự Happy Path**

1. API nhận role \+ PDF/DOCX, kiểm tra global processing lock, rate limit và quota.  
2. Tạo session\_id ngẫu nhiên, state \= UPLOADED rồi chuyển VALIDATING.  
3. Document Processing tạo canonical\_text, chuẩn hóa NFC và kiểm tra chất lượng extraction.  
4. Scope Precheck xác nhận HĐLĐ bằng luật cục bộ.  
5. PII Masker tạo masked\_text cùng độ dài canonical\_text.  
6. Clause Segmenter tách clause trên masked\_text nhưng original\_text lấy từ canonical\_text theo cùng span.  
7. Clause Graph Builder tạo NEXT, PARENT\_OF, REFERS\_TO bằng ID.  
8. State chuyển PROCESSING; Clause Classification xử lý theo lô qua Gemini.  
9. Baseline Retriever tạo seed legal candidates; Data Graph mở rộng tối đa 1 hop và lọc hiệu lực.  
10. Clause Graph Context Resolver chọn related\_clause\_ids; backend lấy masked text tương ứng làm context cho Risk stage.  
11. Risk LLM trả risk labels, severity/explanation/citation\_ids/evidence\_status theo clause\_id.  
12. Citation Validator loại citation không hợp lệ; Result Assembler ghép quote/span chuẩn.  
13. Nếu toàn bộ stage thành công, state \= COMPLETED; frontend lấy result/highlight/export.

## **4.2 Retry và lỗi**

* REJECTED dùng cho input không hợp lệ/out-of-scope và là trạng thái cuối; muốn thử file khác phải mở session mới.  
* FAILED dùng cho lỗi pipeline/provider; không expose partial result như final.  
* LLM timeout 30 giây; auto-retry tối đa 1 lần cho một call.  
* Manual retry tối đa 2 lần/session. Nếu stage resume còn được giữ, chỉ chạy lại từ stage lỗi khi toàn bộ version pin không đổi.  
* Nếu Data Graph lỗi runtime, không fail toàn pipeline: fallback sang baseline retrieval và ghi RunLog.  
* End Session phải hủy call đang chạy nếu có, xóa dữ liệu tạm và chuyển EXPIRED.

# **5\. Thiết kế Data Graph**

Data Graph là lớp kiến thức bổ sung trên closed legal corpus, phục vụ Retrieval & Fact-finding. Nó không thay thế retriever nền và không có quyền tạo citation ngoài corpus.

![](/docs/diagrams/graphs.png)

*Hình 4\. Data Graph và Clause Graph trong pipeline*

## **5.1 Mô hình Data Graph**

| Thành phần | Thiết kế SDD |
| :---- | :---- |
| Node | LegalProvision, định danh bởi citation\_id. |
| PARENT\_OF | Sinh tự động từ parent\_path; phải acyclic. |
| REFERS\_TO | Dữ liệu corpus do người phụ trách dữ liệu xác minh; có thể được gợi ý tự động nhưng không dùng trực tiếp khi chưa xác minh. |
| GUIDES | Dữ liệu corpus mô tả văn bản hướng dẫn thi hành; được người phụ trách dữ liệu xác minh. |
| Storage | Artifact dữ liệu cùng legal corpus; khi backend khởi động/reload sẽ validate rồi tạo adjacency index trong memory. |
| Validation | Mọi endpoint của edge phải tồn tại; PARENT\_OF không có cycle; conflict làm build/reload fail fast. |
| Lifecycle | Persistent như corpus, nhưng không chứa dữ liệu hợp đồng. |

## **5.2 Retrieval \+ Graph Expansion**

![](/docs/diagrams/retrieval.png)

* Seed candidate luôn được ưu tiên hơn candidate chỉ xuất hiện do graph expansion.  
* Expansion mặc định tối đa 1 hop; số seed/top candidate và số candidate cuối cấu hình ở TDD.  
* Neighbor hết hiệu lực tại analysis date bị bỏ qua.  
* Exact scoring/weight theo edge type để TDD chốt sau số đo D1/D2; SDD không khóa số trọng số.  
* Embedding không thuộc baseline. Chỉ thêm nếu M8 trên D2 cho thấy mapping \+ lexical \+ graph chưa đủ.  
* EV-08 chạy cùng pipeline với Data Graph bật và tắt để báo M8 ở hai cấu hình.

# **6\. Thiết kế Clause Graph**

Clause Graph là đồ thị tạm thời của một session, dựng ngay sau segmentation. Graph chỉ chứa ID và quan hệ; mọi text được truy xuất từ session store khi cần.

## **6.1 Mô hình Clause Graph**

| Edge | Nguồn | Ý nghĩa |
| :---- | :---- | :---- |
| NEXT | Thứ tự span | Clause kế tiếp trong canonical text. |
| PARENT\_OF | Đánh số cấu trúc | Điều chứa khoản/điểm con. |
| REFERS\_TO | Luật cục bộ/regex trên masked clause | Điều khoản dẫn chiếu rõ tới clause khác trong cùng hợp đồng. |

## **6.2 Cách dùng cho Validation & Reasoning**

SDD chốt Clause Graph là một Context Resolver, không phải nguồn dữ liệu phân tích độc lập và không tạo thêm LLM stage.

* Đối với mỗi target clause, Context Resolver lấy các clause liên quan trực tiếp qua REFERS\_TO và PARENT\_OF; NEXT có thể dùng làm ngữ cảnh lân cận khi cần.  
* Backend lấy masked text của các related\_clause\_ids từ cùng session và truyền dưới dạng context bổ sung cho Risk LLM.  
* Risk LLM vẫn phải trả kết quả cho target clause\_id; related clauses chỉ hỗ trợ phát hiện điều kiện, mâu thuẫn hoặc phụ thuộc.  
* Clause Graph không được thay đổi segmentation, original\_text, span hoặc quote.  
* Nếu không có cạnh liên quan, Risk stage chạy như pipeline bình thường với target clause.  
* Số related clauses/context limit được cấu hình ở TDD để kiểm soát token/cost.

# **7\. Kiến trúc dữ liệu và lưu trữ**

## **7.1 Phân loại dữ liệu**

| Loại dữ liệu | Ví dụ | Lưu trữ | Vòng đời |
| :---- | :---- | :---- | :---- |
| Session content | File gốc, canonical\_text, masked\_text, clauses, RiskResult, Clause Graph | Memory / temp storage | Xóa khi End Session hoặc 60 phút inactivity; mất khi restart. |
| Legal knowledge | LegalProvision, LegalEdge, taxonomy artifacts | Versioned corpus artifacts / index | Persistent, cập nhật ngoài source code. |
| Operational metadata | RunLog, token/cost, quota counter, error metadata | Metadata-only store/log | Có thể persistent; không chứa contract content/PII. |
| Evaluation data | D1/D2/T1/T2 đã de-identify, gold, metrics output | Evaluation workspace | Ngoài session runtime; theo BRD 8\. |

## **7.2 Session aggregate**

Session  
- session_id
- role
- status / current_stage
- created_at / last_activity_at
- manual_retry_count
- filename
- extraction_version
- canonical_text
- masked_text
- clauses[]
- clause_graph
- clause_classification_outputs
- legal_candidates
- risk_results[]
- version_pins
- last_error

Đây là aggregate runtime ở mức thiết kế; exact schema/class được định nghĩa trong TDD. Không có contract\_id hoặc analysis\_id theo DEC-03.

## **7.3 Invariant dữ liệu**

* canonical\_text\[start\_char:end\_char\] \== original\_text với mọi clause.  
* len(masked\_text) \== len(canonical\_text).  
* Không clause boundary nào nằm giữa một placeholder.  
* Không có bảng mapping placeholder \-\> giá trị gốc.  
* Mọi RiskResult có clause\_id.  
* Severity null khi evidence\_status \= INSUFFICIENT\_EVIDENCE.  
* Citation phải thuộc final candidate list, closed corpus và hiệu lực ở analysis date.  
* Clause Graph chỉ chứa clause\_id và edge\_type; Data Graph không chứa contract data.

# **8\. Session, State Machine và điều phối**

![](/docs/diagrams/state_machine.png)

Analysis Orchestrator là component duy nhất được phép chuyển state. Các service trả typed result/error, không tự thay đổi state.

## **8.1 Single-session processing**

* Backend có một global processing lock/semaphore capacity \= 1\.  
* Lock được giữ trong thời gian VALIDATING hoặc PROCESSING.  
* Upload mới khi lock bận bị từ chối SYSTEM\_BUSY và không tạo session.  
* Session đã COMPLETED/FAILED/REJECTED không giữ processing lock.  
* Session store vẫn phải cô lập dữ liệu theo session\_id, dù demo chỉ xử lý một phiên tại một thời điểm.

# **9\. LLM Integration Design**

## **9.1 Hai adapter sản phẩm**

| Adapter | Input | Output | Quy tắc |
| :---- | :---- | :---- | :---- |
| Clause Classification | Batch (clause\_id, masked clause) | clause\_id \+ 1..3 clause\_labels | Không quote/span/score tự khai. |
| Risk Analysis | Target clause \+ labels \+ role \+ legal candidates \+ optional related clause context | risk\_labels, severity, explanation, citation\_ids, evidence\_status | Chỉ chọn citation trong candidates; severity null nếu thiếu evidence. |

## **9.2 LLM Client cross-cutting**

* Provider cho demo/evaluation: Gemini Flash paid tier; model id bắt buộc cấu hình.  
* Timeout mỗi call 30 giây; auto-retry tối đa 1 lần cho lỗi tạm thời.  
* Structured output phải được validate; sai schema sau retry \-\> AI\_OUTPUT\_INVALID.  
* Batch nhiều clause/call, mức batch và parallelism cấu hình theo D1.  
* LLM call/token/estimated cost được ghi RunLog; log không chứa prompt chứa contract text.  
* API key qua header, không hard-code, không log.

# **10\. Legal Corpus và Citation Validation**

* Legal corpus là nguồn đóng duy nhất. Mỗi LegalProvision có citation\_id deterministic, version, effective\_from/effective\_to.  
* Corpus build/reload chạy validator trước khi publish index; overlap version hoặc edge invalid \-\> LEGAL\_CORPUS\_CONFLICT và fail fast.  
* Analysis date là ngày hệ thống phân tích, vì hợp đồng trong phạm vi là hợp đồng chưa ký.  
* Citation Validator kiểm tra: candidate membership \-\> existence \-\> version/effectivity \-\> structured metadata.  
* Relevance là quality property được đánh giá bằng M3b; runtime không tự tuyên bố relevance chỉ vì citation tồn tại.  
* Nếu không đủ căn cứ: giữ RiskResult với INSUFFICIENT\_EVIDENCE, citation\_ids rỗng và severity null.

# **11\. Security và Privacy Architecture**

| Kiểm soát | Thiết kế |
| :---- | :---- |
| Transport | HTTPS Browser-\>Backend và Backend-\>Gemini trong deployment. |
| Session identity | session\_id opaque/random (UUID v4 hoặc tương đương). |
| PII boundary | Chỉ masked text ra ngoài trusted backend. |
| PII preservation | Placeholder cùng độ dài; không lưu mapping ngược. |
| Secrets | Environment/secret configuration; model id bắt buộc. |
| Logging | Chỉ ID/stage/timing/error/token/cost; không raw/canonical/masked text đầy đủ. |
| Retention | End Session hoặc 60 phút inactivity; session content bị xóa. |
| Persistent storage | Không lưu file/canonical/masked/result/Clause Graph vào DB hoặc durable storage. |
| Abuse control | Daily LLM-call quota \+ IP rate limit; không dùng demo password. |

# **12\. Reliability, Performance và Cost**

* E2E target: 90% successful runs với PDF \<=15 trang hoặc DOCX \<=50.000 canonical characters hoàn thành \<=120s.  
* UI phải chuyển trạng thái VALIDATING/PROCESSING trong \<=2s sau khi backend nhận upload.  
* Không expose partial final report khi FAILED.  
* Batching giảm số LLM calls; Data Graph/Clause Graph chạy local, không tăng số LLM calls.  
* Nếu Data Graph lỗi runtime, fallback retrieval nền thay vì fail toàn phiên.  
* Trần file: PDF \<=10MB/30 trang; DOCX \<=10MB/100.000 canonical chars; \<=150 clauses.  
* Budget demo: \$20, trong đó \$5 vận hành và \$15 đánh giá; quota daily phải cấu hình theo phần \$5.

# **13\. Deployment Architecture**

![](/docs/diagrams/web_flow.png)

*Hình 5\. Deployment Architecture cho demo*

SDD không khóa nhà cung cấp hosting. Deployment chỉ yêu cầu một web frontend và một backend service đơn, có HTTPS, temp storage và quyền đọc legal corpus artifacts. Không cần database chứa nội dung hợp đồng.

## **13.1 Startup sequence**

14. Load configuration: model id, API key reference, timeout, quota/rate settings, graph enable flag.  
15. Load clause/risk taxonomy \+ version metadata.  
16. Load legal corpus; validate version overlap và citation IDs.  
17. Build baseline retrieval index.  
18. Build Data Graph adjacency index; nếu corpus/graph conflict thì startup/reload fail fast.  
19. Khởi tạo in-memory Session Store, processing lock, RunLog/quota services.  
20. Chỉ sau khi các bước trên thành công mới nhận upload.

# **14\. Evaluation Architecture**

Evaluation Harness dùng cùng các module pipeline nhưng chạy như thư viện ngoại tuyến, không qua API/session runtime.

* Input: D1/D2/T1/T2 đã de-identify thủ công.  
* Output: JSON artifacts và metrics M1-M8; không bị session cleanup xóa.  
* M8 phải chạy hai cấu hình: Data Graph enabled và disabled.  
* Judge Claude là tool offline riêng; chỉ chạy sau calibration M6 và không nằm trong product API.  
* Mọi output evaluation chứa version pins và commit hash theo EV-04/EV-07.

# **15\. Traceability: SRS \-\> Component**

| Yêu cầu | Component chịu trách nhiệm chính |
| :---- | :---- |
| FR-01..06, FR-26..27 | API/Session Controller, Orchestrator, Scope Precheck, Quota/Rate |
| FR-07..10 | Document Processing, PII Masker, Clause Segmenter |
| FR-11, FR-28..29 | Clause Classification Adapter, LLM Client, Orchestrator |
| FR-12, FR-15..16, FR-24, FR-30 | Legal Corpus Manager, Baseline Retriever, Data Graph Service, Citation Validator |
| FR-13..18 | Risk Analysis Adapter, Clause Graph Context Resolver, Citation Validator |
| FR-19..20, FR-22, FR-25 | Result Assembler, Web Frontend, Report Exporter |
| FR-21, FR-23 | Orchestrator, Session Store, Cleanup Scheduler |
| FR-31 | Clause Graph Builder \+ Context Resolver |
| NFR-SEC / DATA / REL / COST | Cross-cutting: Session Store, LLM Client, RunLog, Config, Deployment |
| EV-01..08 | Evaluation Harness \+ shared pipeline modules |

# **16\. Các điểm để TDD chốt**

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

# **17\. Rủi ro kiến trúc và biện pháp**

| Rủi ro | Tác động | Thiết kế giảm thiểu |
| :---- | :---- | :---- |
| Graph làm phình scope | Trễ retrieval/pipeline | Baseline retrieval độc lập graph; max 1 hop; non-structural edges là cut item. |
| Parser/PII làm lệch span | Highlight sai | Same-length masking \+ invariant \+ backend-authoritative span. |
| LLM output sai schema | Pipeline fail/merge sai | Structured validation \+ one auto-retry \+ AI\_OUTPUT\_INVALID. |
| Provider chậm/lỗi | Không đạt 120s | Batch, timeout 30s, manual retry, stage resume nếu giữ. |
| PII leak | Rủi ro bảo mật | Local masking, HTTPS, privacy tests, no content logs. |
| Corpus/version lỗi | Citation sai | Fail-fast corpus validator \+ effectivity filter \+ closed corpus. |
| Codebase lệch tài liệu | Rework | TDD/API schemas trước khi triển khai; traceability; update docs cùng code. |

# **18\. Kết luận thiết kế**

Kiến trúc đề xuất giữ hệ thống ở mức vừa sức cho demo: một modular monolith, session data tạm thời, hai LLM calls bắt buộc, retrieval cục bộ với Data Graph là lớp mở rộng và Clause Graph là lớp context cho reasoning. Thiết kế ưu tiên privacy, khả năng truy vết, kiểm thử và khả năng fallback hơn độ phức tạp hạ tầng.