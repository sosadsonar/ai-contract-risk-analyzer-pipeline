# OPEN_ISSUES_HANDLE_v4 — Quyết định và giải pháp cho SRS OI-03, OI-05, OI-10, OI-11, OI-12

**Ngày:** 13/11/2026. **Phạm vi ID:** SRS 1.5 §13
**Nguồn:** `PR27_TECHNICAL_REVIEW_2026-11-12.md` (N4), `decision_SRS_OI-11_v3.md`, `open-issues-core.md`, codebase `ai-contract-risk-analyzer-pipeline-main` (snapshot GitHub mới nhất), và các probe chạy ngoài repo (ghi rõ ở từng mục).

**Trạng thái tài liệu:** quyết định của N3, soạn cùng trợ lý AI. **Chưa có xác nhận của N1/N2/N4/N5** — bảng §7 để trống có chủ ý. Tài liệu này không thay phê duyệt pháp lý/quyền sử dụng dữ liệu, và không sửa code; các thay đổi code nằm ở danh sách việc của từng mục.

OI-11 đã có quyết định riêng (file riêng: `decision_SRS_OI-11_v3.md`): chốt phương án A — Visual text fidelity; mở rộng `structure_parser` nhận diện Roman numerals và bullet `+`. Extractor không xuất level/parent/loại numbering; parser suy ra level/parent theo quy tắc hiện tại. Giữ giới hạn singleton/sequence/hierarchy; OI-11 chưa CLOSED cho đến khi hoàn tất fixture thực, hai regression DOCX đã biết và kiểm chứng tích hợp. OI-09 đã CLOSED; tài liệu này không mở lại hai mục đó.

## 0. Tổng quan

| OI | Quyết định | Trạng thái đề xuất sau quyết định | Điều kiện để đổi trạng thái |
|---|---|---|---|
| OI-05 | Đặt tạm `SESSION_CALL_RESERVE=40`, `DAILY_LLM_CALL_QUOTA=300`; ghi rõ giới hạn admission/cost | **CLOSED về cách làm**; hai giá trị vẫn provisional và được tune sau đo end-to-end | Số đo end-to-end và pricing có nguồn (§2.5) |
| OI-10 | Chốt chính sách đa nhãn + `OTHER` đứng một mình; tie-break IoU xác định | **Chốt chính sách**; chỉ CLOSED khi C1–C6 (mục 3.4) xong | Code, guideline, prompt, version và test đồng bộ |
| OI-03 | Giữ ruleset TDD §9, nâng lên `scope_rules_v2`; phụ lục đứng riêng out-of-scope, vá false accept | **Vẫn OPEN** | 10/10 ca âm reject; ít nhất 5/6 ca dương accept; review lỗi (§4.4) |
| OI-12 | Giữ regex/anchor + heuristic, không thêm NER lần này | **Vẫn NARROWED** | Point estimate theo BRD và cận dưới 95% CI ≥85% riêng từng nhóm PII (§5.3) |
| OI-11 | Chốt phương án A; parser nhận diện Roman numerals và `+` bullet; giữ giới hạn singleton/hierarchy | **Đã chốt hướng; chưa CLOSED** | Fixture thực, regression DOCX, extraction → parser và span/highlight integration tests; kiểm tra giới hạn (§6) |
| OI-09 | Giữ nguyên quyết định Data Graph adjacency in-memory, tối đa một hop | **CLOSED** | Không mở lại; việc tune M8 là hoạt động đánh giá riêng |

## 1. Quyết định chung được dùng lại

- Phụ lục HĐLĐ **đứng riêng** -> **out of scope** cho demo. Phụ lục nằm **trong cùng file** với hợp đồng vẫn nằm trong phạm vi (BRD A1, TDD §9 dòng "phụ lục nằm cùng file được chấp nhận").
- Tên nhãn rủi ro giữ nguyên `POST_EMPLOYMENT_RESTRICTION`; không đổi tên.
- Không sửa gold lịch sử, không đổi 12 nhãn clause, không đổi cách chấm lịch sử để làm đẹp số liệu.

## 2. OI-05 — Quota và reserve

### 2.1. Quyết định

| Biến | Giá trị tạm | Ghi chú |
|---|---|---|
| `SESSION_CALL_RESERVE` | **40** | Phiên mới chỉ được nhận khi số call còn lại trong ngày ≥ 40 |
| `DAILY_LLM_CALL_QUOTA` | **300** | Số call/ngày (UTC), đếm cả retry |
| `RATE_LIMIT_UPLOADS` | giữ 5 / 10 phút / IP | Chưa có dữ liệu tải để đổi |

Hai giá trị gắn nhãn **provisional**: ghi vào `.env.example` và SRS §13 cùng câu "giá trị tạm, tune sau số đo end-to-end". Demo/eval vẫn **fail-closed** khi thiếu cấu hình (`validate_for_env` giữ nguyên); chỉ dev được để trống.

**Lưu ý về ý nghĩa và giới hạn:** `SESSION_CALL_RESERVE=40` là ngưỡng admission: chỉ nhận phiên mới khi quota còn lại ít nhất 40 calls; đây không phải thao tác giữ riêng 40 calls cho session và không bảo đảm session sẽ hoàn thành. Nếu nhiều yêu cầu admission có thể chạy đồng thời, cần bảo đảm kiểm tra/cập nhật quota là atomic hoặc có giới hạn một phiên hoạt động; nếu không, nhiều phiên có thể cùng vượt qua kiểm tra dựa trên cùng số dư. Retry của phiên đã được nhận vẫn có thể làm tổng calls vượt `DAILY_LLM_CALL_QUOTA`; vì vậy 300 là call-count limit, **không phải hard spending cap**. Hiện `cost=0.0` không có nghĩa request miễn phí hay ngân sách USD đã được kiểm soát.

### 2.2. Cơ sở của reserve = 40

- Số call planned mỗi hợp đồng = ceil(clause/20) classify + ceil(clause/6) risk. D1: 43/47/40/68 clause → **11/11/9/16 call** (đã gồm cả hai stage; artifact `w4_d1` chỉ chạy classify nên có 12 call cho cả bốn hợp đồng).
- Trần cứng theo `MAX_CLAUSES=150`: 8 + 25 = **33 call** không retry.
- 40 ≈ 33 cộng khoảng 20% dự phòng retry. Không dùng p95 = 16: đó là phân bố của bốn hợp đồng D1, không phải trần của hợp đồng hợp lệ lớn nhất.
- Chính sách giữ nguyên: quota chặn nhận **phiên mới**; retry của phiên đã nhận có thể vượt quota (không phải hard spending cap).

### 2.3. Cơ sở của quota = 300 (giả định, không phải số đo)

Dữ liệu duy nhất có sẵn: 12 call classify, 22.411 token vào, 7.518 token ra (trung bình khoảng 1,87k vào / 0,63k ra mỗi call), model `gemini-3.5-flash-lite`, cost lưu = 0,0. Chi phí risk stage **chưa được đo**; tính dưới giả định risk stage tốn gấp 3–10 lần tổng token classify.

| Kịch bản giá (USD / 1M token, vào / ra) | Classify 1 hợp đồng D1 | 1 phiên (risk = 3×…10× classify) | Số phiên trong $5 |
|---|---:|---:|---:|
| 0,30 / 2,50 | ≈ $0,006 | $0,026–0,070 | ≈ 70–195 |
| 0,54 / 4,50 | ≈ $0,011 | $0,046–0,126 | ≈ 40–110 |

- Ở kịch bản bi quan, chi phí xấp xỉ $0,0105/call, nên **300 call ≈ $3,2/ngày**; 400 call sẽ ≈ $4,2, gần hết $5 chỉ trong một ngày. Vì vậy chọn 300 (khoảng 25 phiên cỡ D1 mỗi ngày).
- **Giá chưa được kiểm chứng.** Hai nguồn thứ cấp lệch nhau (eesel.ai và OpenRouter: $0,30/$2,50; mức Google AI Studio trên pricepertoken: $0,54/$4,50). Phải đối chiếu trang giá chính thức của Google (ghi nguồn + ngày hiệu lực) trước khi ghi giá vào SRS hoặc code. Thinking token tính như output.
- Quota đếm số call; **cost hiện luôn = 0** nên ngân sách USD chưa kiểm soát được bằng code (xem 2.4). Không được diễn giải quota 300 là cam kết không vượt ngân sách USD.

### 2.4. Việc kéo theo

1. **Giữ usage khi response JSON lỗi** (`gemini_client.py:84–106`, `provider.py:36–43,127–128`): đã tái hiện — usage transport 210/45 nhưng ledger chỉ giữ 110/25. Giải pháp: `ProviderFailure` mang usage của response; phân biệt "usage không biết" (None) với 0.
2. **Bảng giá có nguồn** (model, giá vào/ra, ngày hiệu lực) và tính `LLMResponse.cost` từ đó; ghi nguồn vào config, không hard-code ngầm.
3. Ghép ledger/RunLog vào orchestrator thật (runner D1 hiện dùng `InMemoryLedger`).

### 2.5. Điều kiện thay giá trị tạm bằng số đo

Chạy end-to-end (classify + risk, đã che PII) trên D1, ghi actual calls kể cả retry, token vào/ra, cost theo bảng giá, cost/phiên. Khi đó:
- `RESERVE = ceil(1,2 × số call lớn nhất quan sát được hoặc 33, lấy giá trị lớn hơn)`.
- `DAILY_QUOTA = floor(ngân sách ngày / cost p90 mỗi call)`, trong đó ngân sách ngày = phần của $5 chia cho số ngày chạy demo/diễn tập.
- Bắt buộc xem lại nếu cost thực tế/phiên > $0,15 hoặc giá chính thức khác mức đã giả định.

## 3. OI-10 — Chính sách đa nhãn

### 3.1. Chính sách chốt (kỹ thuật)

1. Mặc định một nhãn chính; tối đa ba nhãn, không trùng, thuộc taxonomy hiện hành.
2. Chỉ thêm nhãn phụ cho một ý trọn vẹn có chủ đề riêng (một câu hoặc mệnh đề); nhắc thoáng keyword không đủ.
3. Nhãn đầu = nhãn chính = chủ đề chiếm nhiều nội dung thực chất nhất; khi hòa, chủ đề xuất hiện trước.
4. `OTHER` chỉ đứng một mình. Clause chỉ có tiêu đề gán theo chủ đề tiêu đề (không có nhãn rỗng). Phân loại không nhận role.
5. Pin vocabulary riêng với revision policy/prompt; không đổi 12 nhãn, không ghi lại gold lịch sử.
6. Đo M7 khi span khác gold theo **BRD hiện hành: greedy one-to-one IoU ≥ 0,5**; không dùng overlap-union của bản draft cũ. Candidate pairs được sắp xếp theo IoU giảm dần; nếu bằng nhau, `gold_start` tăng dần rồi `predicted_start` tăng dần; nếu vẫn bằng nhau, dùng original indices làm tie-break cuối cùng. Mỗi gold/predicted span chỉ được ghép một lần. Nhãn thừa = FP, nhãn thiếu = FN; "nhãn chính đúng" và số nhãn trung bình/clause là chẩn đoán, không thay chỉ số chính.
7. Báo cáo lịch sử giữ nguyên phương pháp cũ; số đo trước/sau thay đổi semantics không so sánh trực tiếp.

### 3.2. Ba topic chưa có nhãn riêng

| Topic | Gán | Trạng thái xác nhận |
|---|---|---|
| Bảo mật / không cạnh tranh / SHTT | Chính `EMPLOYEE_OBLIGATIONS_DISCIPLINE`; thêm phụ `TERMINATION` **chỉ khi** clause tự nêu hậu quả/điều kiện sau chấm dứt HĐ. Khớp risk label `POST_EMPLOYMENT_RESTRICTION` → clause label `EMPLOYEE_OBLIGATIONS_DISCIPLINE` (`RISK_TAXONOMY_v0.1.md`, `risk/taxonomy.py`) | **N3 xác nhận** (tài liệu này) |
| Giải quyết tranh chấp / luật áp dụng | `OTHER` (một nhãn) | Đề xuất N1, **chờ N2** |
| Quyền được bồi thường của NLĐ | Theo chủ thể câu: nghĩa vụ NSDLĐ → `EMPLOYER_RIGHTS_OBLIGATIONS`; quyền chung của NLĐ không có chủ thể NSDLĐ rõ → `OTHER` | Đề xuất N1, **chờ N2**; cần kiểm lại 1–2 mẫu (vd. HDLD004_C027) |

### 3.3. Khoảng cách implementation đã chứng minh

`validate_labels` (`backend/app/clause/taxonomy.py:87–105`) kiểm số lượng, vocabulary và trùng nhưng không cấm `OTHER` đi cùng nhãn khác: `validate_labels(['OTHER','JOB_INFO'])` trả cả hai. Prompt (`clause_v1.py` dòng 67) chỉ nhắc "dùng OTHER chỉ khi không nhãn nào khác phù hợp"; adapter không ép.

**Lưu ý về schema cho greedy tie-break:** quy tắc tie-break chỉ dùng `start` đã có trong `GoldSpan`/`PredClause` và index của phần tử đầu vào. Không thêm field, không đổi schema của gold/prediction, API hay cấu trúc JSON báo cáo metric. Thay đổi (nếu cần) nằm trong logic alignment và unit tests. Kết quả matching/metric chỉ có thể khác ở các trường hợp IoU bằng nhau mà thứ tự đầu vào không tương đương thứ tự `start`; không sửa hoặc tính lại báo cáo lịch sử để thay thế số liệu cũ.

### 3.4. Checklist triển khai (một thay đổi riêng, không gộp vào PR #27)

- **C1.** `validate_labels`: raise `ValueError` nếu `OTHER` xuất hiện cùng nhãn khác. Adapter đã chuyển `ValueError` thành `AiOutputInvalid` → đi qua đường retry hiện có.
- **C2.** Tăng `TAXONOMY_VERSION` (đổi semantics prompt/validator), cập nhật `FROZEN_*` và fingerprint trong `test_clause_taxonomy_freeze.py`, cập nhật bảng §1.1 của `CLAUSE_TAXONOMY_FREEZE.md`; ghi lý do vào `PROGRESS.md` §9.
- **C3.** Prompt: nêu rõ `OTHER` loại trừ nhãn khác và quy tắc nhãn phụ/nhãn chính; đồng bộ chữ với guideline (một nguồn: guideline ↔ `taxonomy.py` ↔ prompt).
- **C4.** Test hành vi: `['OTHER']` hợp lệ; `['OTHER','JOB_INFO']` bị từ chối; hai nhãn không trùng hợp lệ; ba nhãn hợp lệ; bốn nhãn bị từ chối.
- **C4b.** Test greedy alignment: IoU giảm dần; tie-break lần lượt theo `gold_start`, `predicted_start`, rồi original indices; mỗi span chỉ match một lần. Không thay schema đầu vào/đầu ra của metric.
- **C5.** Đo trên D1: tỷ lệ output bị từ chối vì `OTHER` + nhãn khác. Nếu > 2% số clause, cân nhắc chuyển sang chuẩn hóa tất định ở adapter (bỏ `OTHER` khi có nhãn cụ thể, có đếm) — đây là quyết định riêng, không tự đổi.
- **C6.** N2 cập nhật annotation guideline theo §3.1–3.2 sau khi xác nhận; N1/N2/N3 ký bảng §4 của `CLAUSE_TAXONOMY_FREEZE.md`.

Không ghi OI-10 là CLOSED và không thêm chữ ký N2 khi C1–C6 chưa xong.

## 4. OI-03 — Scope precheck

### 4.1. Quyết định

- Tiếp tục dùng ruleset theo TDD §9 cho dev, nâng thành **`scope_rules_v2`** (đổi `SCOPE_RULE_VERSION`) với hai thay đổi dưới đây. Không dùng keyword AI chưa kiểm chứng.
- **Phụ lục HĐLĐ đứng riêng bị từ chối.** Phụ lục nằm trong file hợp đồng chính vẫn được chấp nhận.
- OI-03 **vẫn OPEN**; chưa khóa keyword/ngưỡng cuối cùng.

### 4.2. Vấn đề đã tái hiện (probe trên `precheck` hiện tại, đầu vào tổng hợp, không phải precision/recall)

| Mẫu | v1 hiện tại | Ghi chú |
|---|---|---|
| Nội quy lao động (hai bên + lương + giờ làm) | accept, score 5 | false accept |
| Cam kết bảo mật có "người lao động", lương, công việc | accept, score 4 | false accept |
| Hợp đồng dịch vụ có "người lao động", lương | accept, score 4 | false accept qua nhánh `score ≥ 4` + một bên |
| Phụ lục HĐLĐ đứng riêng | accept, score 6 | trái quyết định §1 |
| Mua bán, thuê nhà, tiêu đề ngoài 1.000 ký tự đầu | reject | đúng |

Nguyên nhân: nhánh `score >= 4 and (employee or employer)` không cần strong title nên nhận mọi văn bản về lao động; và `_TITLE` khớp "hợp đồng lao động" bên trong "phụ lục hợp đồng lao động".

### 4.3. Thay đổi `scope_rules_v2` (đã thử nguyên mẫu ngoài repo; chưa nằm trong code)

- **R1 — title âm:** nếu dòng không rỗng đầu tiên (NFC/casefold, trong title window) bắt đầu bằng một trong: `phụ lục`, `nội quy`, `quy chế`, `thỏa ước`, `cam kết`, `biên bản`, `quyết định`, `hợp đồng dịch vụ/mua bán/thuê/khoán` → reject, signal `negative_title`. Giữ cách kiểm tra prefix như nguyên mẫu. **Guard khi mở rộng danh sách:** mỗi keyword/prefix mới phải có ít nhất một ca âm làm căn cứ và phải chạy regression trên các ca dương liên quan để kiểm tra false reject; chỉ cập nhật trong một `SCOPE_RULE_VERSION` mới.
- **R2 — nhánh không có strong title** (`score ≥ 4`) yêu cầu **cả hai bên** (NLĐ và NSDLĐ) xuất hiện, không chỉ một.
- Giữ: title chỉ xét vùng đầu, cặp party +2, content tối đa +3, structure +1, matching trên bản sao NFC/casefold, canonical không đổi.

Kết quả nguyên mẫu (không đầu vào nào phải sửa offset hay canonical):

| Mẫu | v1 | v2 |
|---|---|---|
| Hợp đồng lao động, hợp đồng thử việc, HĐLĐ không strong title nhưng đủ hai bên | accept | accept |
| HĐLĐ có "PHỤ LỤC 01" ở cuối file | accept | accept |
| Nội quy, cam kết, dịch vụ, phụ lục đứng riêng | accept | **reject** |

Một fixture hiện có phải **đổi**: `appendix-with-contract` trong `tests/fixtures/extraction/scope_cases.json` hiện là `"PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG\nThỏa thuận điều chỉnh lương…"` với `accept: true` — đó chính là phụ lục đứng riêng; đổi thành `accept: false` (tên mới `standalone-appendix`) và thêm fixture `contract-with-trailing-appendix` (`accept: true`). Raw-text D1 HDLD001–006 không có trong zip nên **chưa chạy lại v2 trên D1**; bắt buộc chạy lại (kỳ vọng vẫn accept, score ≥ 9 trước đây) trước khi merge.

### 4.4. Điều kiện đóng OI-03

1. Bộ ca độc lập đã review, **không tune trên chính bộ này rồi dùng làm bằng chứng**:
   - **10 ca âm phải đạt 10/10 reject**: nội quy, thỏa ước, quyết định nhân sự, cam kết, thư mời nhận việc, hợp đồng dịch vụ/khoán, phụ lục đứng riêng, mua bán, thuê, biên bản. Không chấp nhận false accept trong bộ nghiệm thu này.
   - **6 ca dương phải đạt ít nhất 5/6 accept**: HDLD001–004, hợp đồng thử việc, hợp đồng có phụ lục cuối file, có đại diện PDF và DOCX. Nếu có false reject (tối đa một ca theo ngưỡng này), phải review riêng, ghi nguyên nhân và quyết định xử lý; không được âm thầm bỏ ca khỏi bộ test.
2. Báo confusion matrix + review từng lỗi false accept/false reject; mỗi lỗi ghi nguyên nhân và quyết định xử lý.
3. Khóa keyword/ngưỡng theo `SCOPE_RULE_VERSION` và ghi vào SRS §13.
4. Sửa chữ BRD A1 và TDD §9 để nói rõ "phụ lục nằm cùng file" khác "phụ lục đứng riêng (không hỗ trợ)".
5. Nguồn ca âm thật: N2/N1 cung cấp; N3 không tự bịa ca và không dùng T1/T2 để tune.

## 5. OI-12 — PII local

### 5.1. Quyết định

Giữ **regex/anchor + heuristic**; **không thêm local NER** trong lần tích hợp này. Đây là quyết định phạm vi triển khai, không phải nghiệm thu privacy và không loại NER vĩnh viễn. OI-12 giữ **NARROWED**.

### 5.2. Vì sao chưa nghiệm thu

- Báo cáo T1 (`reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06`) có point estimate đạt ngưỡng nhưng support rất nhỏ: nhóm nhạy cảm cao 3/3, chuẩn 18/18. Cận dưới Clopper-Pearson 95% hai phía khoảng **29%** cho 3/3 và **82%** cho 18/18, nên không dùng để khẳng định recall quần thể.
- Báo cáo không pin version masker; masker hiện tại là `pii_draft_0.4`, baseline cũ là `pii_draft_0.3`. Số đo cũ không tự nghiệm thu bản mới.
- Gold privacy restricted (`T1_privacy_gold_v01`, `*.gold_privacy.json`) không có trong checkout; N2 giữ. Không chạy lại, không bịa số.
- T2 là reference suy ra, không phải tập privacy độc lập đã adjudicate. P1 sinh gold từ tọa độ chèn nên chỉ đo PII trong khung nhãn chuẩn, không thay hợp đồng thật; tên/địa chỉ trong văn xuôi không anchor chưa được đo.

### 5.3. Giải pháp và điều kiện đóng

1. **N2** chạy `ai_pipeline/eval/eval_pii_gold.py` trên T1 gold với masker `pii_draft_0.4` (kiểm lại tham số của script trước khi giao việc), ghi masker version, hash gold, provenance/adjudication.
2. Báo cáo theo từng loại PII: số mẫu, full-span coverage, preserve, lỗi bỏ sót và che nhầm; nhóm thiếu support báo `NOT_ESTIMABLE`; kèm khoảng tin cậy chính xác, không dùng bootstrap trên mẫu toàn-success.
3. Ghi rõ giới hạn trong báo cáo: loại SIGNATURE; P1 chỉ đo PII trong khung nhãn chuẩn, không thay T1.
4. **Quy tắc nghiệm thu theo từng nhóm PII của BRD §7.3:**
   - High-sensitivity: point estimate recall ≥99%.
   - Standard-sensitivity: point estimate recall ≥90%.
   - Với **mỗi nhóm**, cận dưới của **95% CI hai phía exact Clopper–Pearson phải ≥85%**. Không đặt giới hạn cho cận trên; CI có cận trên lớn hơn 95% vẫn đạt điều kiện này.
   - Báo cáo riêng từng loại PII, support, số tài liệu, full-span coverage, preserve, false negative và false positive. Không để một loại PII có support tốt che khuất loại khác. Loại/nhóm thiếu support được ghi `NOT_ESTIMABLE`; không tính là pass và OI-12 chưa được đóng hoàn toàn.
   - Mốc tham khảo: nếu không có false negative, cần khoảng 23 PII spans độc lập trong một nhóm để cận dưới của 95% CI Clopper–Pearson hai phía đạt 85%; có lỗi bỏ sót thì cần support lớn hơn. Không mặc định nhiều spans trong cùng một hợp đồng là các quan sát độc lập; phải báo cáo phân bố theo tài liệu và xem xét sự phụ thuộc.
   - Nếu point estimate không đạt ngưỡng BRD hoặc review phát hiện dạng bỏ sót cần năng lực nhận diện rộng hơn, mở đánh giá local NER (chạy cục bộ, không gửi PII ra cloud). Nếu chỉ thiếu support/CI chưa đạt do bất định, ưu tiên bổ sung gold độc lập; không tự động kết luận phải dùng NER.
5. Không tune trên held-out T1/T2 rồi báo như đánh giá độc lập; không suy ra quyền đưa PII lên cloud từ kết quả kỹ thuật (OI-03 của BRD về dữ liệu cá nhân/Gemini vẫn là việc pháp lý riêng).
6. Output lỗi của `eval_p1.py` có thể chứa giá trị synthetic bị bỏ sót; không dùng tùy tiện với PII thật rồi công bố.

## 6. OI-11 — DOCX numbering và hợp đồng extractor–parser

### 6.1. Quyết định

Chốt **Phương án A — Visual text fidelity**. Extractor bảo toàn nội dung văn bản hiển thị, gồm numbering/bullet tự động trong phạm vi hỗ trợ và marker người soạn gõ tay. Extractor không khôi phục đầy đủ cây Multilevel List, không xuất `level`, `parent` hoặc loại numbering.

Mở rộng `structure_parser` để nhận diện:

- Roman numerals hợp lệ, ví dụ `I.`, `II.`, `III.`, `IV.`; nhận diện hoa/thường và phân biệt pattern Roman với lettered đơn.
- Bullet `+` cùng các marker dash hiện có (`-`, `–`, `•`). `+` thuộc nhóm weak marker `dash`, không tạo loại cấu trúc mới.

Đối với numbering gõ tay, marker là text thường: extractor chỉ giữ nguyên, không xóa, tự thêm hoặc nhân đôi. Với numbering tự động, extractor materialize marker trong phạm vi format hỗ trợ; kiểm thử phải phát hiện trường hợp marker thiếu/trùng, đặc biệt khi automatic numbering cùng tồn tại với text marker gõ tay.

### 6.2. Giới hạn parser được giữ nguyên

- `numbered`: tối thiểu hai mục anh em, bắt đầu từ 1 và liên tiếp.
- `lettered`: tối thiểu hai mục anh em, bắt đầu từ a và liên tiếp.
- `roman`: tối thiểu hai mục anh em, bắt đầu từ I/i và là chuỗi Roman hợp lệ, liên tiếp.
- `dash` (`-`, `–`, `•`, `+`): tối thiểu hai mục anh em; không yêu cầu sequence.
- Một mục lẻ không tạo ranh giới clause. Danh sách thiếu marker hoặc bị đứt chuỗi có thể bị parser loại bỏ; không tự suy đoán marker để vá.
- Parser tiếp tục suy luận `level`/`parent` từ thứ tự và kiểu marker. Đây không phải bằng chứng tái tạo chính xác level/hierarchy nội tại của Word. Không mở rộng thành semantic hierarchy đầy đủ trong OI-11.

`ROMAN` là phân loại marker nội bộ bổ sung cho kết quả `HeadingMark`; `+` được gom vào loại `DASH` hiện có. Không thay schema extractor, gold DOCX, API hay persistence schema. Các consumer nội bộ kiểm tra cứng tập `kind` cần được rà soát khi thêm giá trị `roman`; segmenter hiện sử dụng các thông tin `start`, `level`, `number`, `parent_index` để dựng clause structure.

### 6.3. Tiêu chí nghiệm thu

1. Mỗi fixture có `expected canonical_text` được đối chiếu với tài liệu gốc/hiển thị trong Word, không lấy output extractor làm expected.
2. Fixtures tối thiểu gồm Multilevel List, Roman list, bullet (`-`, `–`, `•`, `+`), numbering gõ tay và mixed automatic/manual.
3. Chạy pipeline test: DOCX extraction → so `canonical_text` → `structure_parser` → so expected parser marks, `level` và `parent` theo quy tắc suy luận parser.
4. Có test chứng minh Roman numerals được nhận diện riêng và theo sequence; `+` được nhận diện trong nhóm dash; singleton và nhóm numbering không liên tiếp vẫn bị loại theo chính sách hiện tại.
5. Regression tests cho hai lỗi P2 đã tái hiện trong review N4: (a) effective level/format override phải được dùng khi thay placeholder; (b) `lvlRestart=0` không được reset counter sai.
6. Nếu canonical thay đổi, quản lý/tăng extraction version phù hợp và tính lại spans phụ thuộc; không sử dụng offset từ canonical version cũ.
7. Với clause phía sau numbering được materialize, N5 xác minh span trỏ đúng substring trong canonical text và frontend highlight phủ đúng substring sau ánh xạ code point → UTF-16.
8. Ghi rõ format tự động ngoài phạm vi là không hỗ trợ; không tuyên bố hỗ trợ mọi OOXML numbering, custom picture bullets hay symbol fonts.

Chi tiết quyết định và phương pháp kiểm chứng nằm trong `decision_SRS_OI-11_v3.md`.

### 6.4. Trạng thái

**Đã chốt hướng, chưa CLOSED.** Chỉ xem xét đóng khi N2 xác nhận fixture thực/expected; N4 xác nhận extraction/parser và hai regression numbering; N5 xác nhận spans/highlight; integration test extraction → parser → span/highlight đạt và giới hạn đã được ghi nhận rõ. Việc mở rộng parser để nhận Roman/`+` là phần implementation cần làm, chưa được xem là đã triển khai.

## 7. Việc kéo theo và thứ tự đề nghị

1. OI-11: N2 cung cấp fixture/expected canonical; N4 xử lý extractor/parser, Roman numerals, `+` bullet và hai lỗi P2 đã tái hiện; N5 xác minh spans/highlight. Quản lý extraction version và tính lại spans nếu canonical đổi.
2. Usage/pricing (§2.4), rồi chạy end-to-end D1 để thay giá trị tạm OI-05.
3. OI-10: C1–C6 (§3.4).
4. OI-03: `scope_rules_v2` + fixture, rồi bộ ca độc lập (§4).
5. OI-12: lấy quyền truy cập gold, chạy đo bản 0.4 (§5.3).
6. Cập nhật SRS §13, BRD A1/TDD §9 và `PROGRESS.md` sau khi người phụ trách duyệt; không đánh dấu CLOSED thay cho phần việc chưa làm.

## 8. Xác nhận

| Người | Phạm vi xác nhận | Trạng thái |
|---|---|---|
| N3 | Toàn bộ quyết định ở §1–§6; topic bảo mật/không cạnh tranh (§3.2) | Đã duyệt nội dung (13/11/2026) |
| N1 | OI-10 §3.1, §3.4; OI-05 §2.4 (provider) | Chờ |
| N2 | OI-10 §3.2 (hai topic cuối); OI-03 §4.4 (ca âm thật); OI-11 §6 (DOCX fixture/expected canonical); OI-12 §5.3 (gold) | Chờ |
| N4 | Đối chiếu technical review; OI-11 §6 (extractor/parser, hai regression numbering và extraction version) | Chờ |
| N5 | OI-11 §6: xác minh spans và highlight đúng canonical text sau khi numbering được materialize; giữ contract code point → UTF-16 | Chờ |

Không ghi chữ ký thay người khác; ô "Chờ" chỉ được đổi khi chính người đó xác nhận.


## 9. Ghi nhận các quyết định bổ sung ngày 13/11/2026

- **OI-05:** giữ nguyên giá trị provisional 40/300; bổ sung cảnh báo reserve chỉ là admission threshold, không phải hard reservation; quota call-count không phải hard spending cap.
- **OI-03:** chốt acceptance của bộ độc lập là 10/10 ca âm reject và ít nhất 5/6 ca dương accept; false reject phải review; mở rộng negative title phải có ca âm và positive regression.
- **OI-10:** chốt tie-break greedy theo IoU giảm dần, `gold_start` tăng dần, `predicted_start` tăng dần, original indices làm tie-break cuối. Không thay schema.
- **OI-12:** chốt đánh giá riêng từng nhóm theo ngưỡng point estimate của BRD (high-sensitivity ≥99%, standard-sensitivity ≥90%) và cận dưới 95% CI hai phía exact Clopper–Pearson ≥85%; nhóm thiếu support là `NOT_ESTIMABLE`, chưa được đóng.
- **OI-11:** chốt mở rộng parser nhận Roman numerals và `+` bullet; giữ singleton/sequence/hierarchy limits và acceptance/regression conditions tại §6.
