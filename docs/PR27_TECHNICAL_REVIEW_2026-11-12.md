# PR #27 — Biên bản review và quyết định kỹ thuật

**Ngày:** 12/11/2026. **Người review:** trợ lý AI, theo yêu cầu của N4, thực hiện review kỹ thuật thay các vai trò N1/N2/N3/N5.

**Nguồn yêu cầu:** [PR #27](https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline/pull/27), [comment nhận xét](https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline/pull/27#issuecomment-6737264769), [approve có lưu ý còn vấn đề](https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline/pull/27#pullrequestreview-5839922432).

## 1. Phạm vi, cách đọc và kết luận

Review trên working tree `backend/n4-w4` sau khi ghép `origin/main` nhưng **chưa commit merge**:

- HEAD: `0085b495af979b85156be2142af13b493fcc28ae`.
- MERGE_HEAD: `85474cad3f88b0e3c8c963e68f96b46525c74733`.
- Submodule dữ liệu: `d9b393efa7b51eef55326bf808cea352891348c5`.
- Không sửa implementation, taxonomy, gold, cấu hình runtime hoặc trạng thái SRS/PROGRESS trong lượt review này. Không stage/commit/push; chỉ thêm biên bản này.

**Kết luận:** duyệt có giới hạn phần accounting của PR và thuật toán offset frontend; chốt hướng chính sách đa nhãn và giữ regex/heuristic cho lần tích hợp này. **Không duyệt đóng OI-03/05/11 hoặc nghiệm thu PII hiện tại.** Có hai lỗi numbering đã tái hiện, một thiếu hụt usage có sẵn từ trước và một khoảng cách giữa chính sách nhãn với validator.

“Chốt” trong biên bản là kết luận kỹ thuật của reviewer được N4 yêu cầu, không phải chữ ký của các thành viên, không thay cho phê duyệt pháp lý/quyền sử dụng dữ liệu. Phê duyệt một hướng thiết kế không có nghĩa implementation đã đáp ứng toàn bộ hướng đó. Các OI dưới đây là **ID trong SRS**, không phải ID trùng số của BRD.

| Hạng mục | Kết luận lần review này | Trạng thái không được suy diễn |
| --- | --- | --- |
| N1 — request/retry/schema accounting | Duyệt phần sửa bookkeeping của PR trong phạm vi wrapper và ledger độc lập | Không phải bảo đảm đầy đủ token bị tính phí hoặc RunLog production |
| OI-03 — scope | Giữ ruleset mặc định theo TDD §9 cho dev | Chưa đóng keyword/ngưỡng cuối cùng hoặc nghiệm thu precision/recall |
| OI-05 — quota/reserve | Chưa chốt giá trị số; giữ yêu cầu cấu hình demo fail-closed | Không đặt reserve = 16 hoặc coi cost = 0 là miễn phí |
| OI-10 — đa nhãn | Chốt hướng chính sách ở §5; chưa hoàn tất đồng bộ implementation/guideline | Không ghi rằng N2/N3 đã ký hoặc semantic freeze đã hoàn thành |
| OI-11 — DOCX | Giữ python-docx + OOXML, phạm vi fixture giới hạn; chưa duyệt numbering đầy đủ | Hai lỗi ở §3 phải xử lý, cần mẫu thực và expected text |
| N5 — offset/highlight | Duyệt thuật toán ánh xạ code point → UTF-16 dưới contract span hiện có | Không phải nghiệm thu giao diện bằng browser hoặc độ trung thực DOCX gốc |
| OI-12 — PII | Giữ regex/heuristic, không thêm NER trong lần tích hợp này | Chưa nghiệm thu masker hiện tại trên gold độc lập; chưa loại bỏ NER vĩnh viễn |
| OI-09 — graph | Không mở lại quyết định đã CLOSED | Không đồng nghĩa graph đạt M8 hoặc toàn bộ pipeline đã sẵn sàng |

## 2. Thay N1: provider, usage, quota và RunLog

### 2.1. Phần được duyệt

Đã đọc `backend/app/ai/provider.py`, `backend/app/ops/{quota,runlog,metadata_db}.py` và các test liên quan, không chạy suite.

- `call_with_retry` gọi `before_call` trước từng attempt, kể cả retry; retry tổng bị giới hạn một lần, không phải mỗi loại lỗi được retry riêng một lần.
- Response đã parse nhưng sai schema được ghi token/cost kèm `schema_invalid`; response thành công sau đó là một request riêng. Các nhánh cancel và lỗi bất ngờ đóng bookkeeping của attempt.
- `DailyQuota` tăng lượt gọi trước request, gắn usage với ngày request bắt đầu kể cả qua nửa đêm. Quota chặn nhận **phiên mới**; retry của phiên đã nhận có thể vượt quota. Đây là chính sách hiện tại, không phải hard spending cap hay một thao tác đặt chỗ ngân sách cho toàn phiên.
- `EvalCostLedger` tách CSV eval khỏi SQLite/quota sản phẩm, ghi sự kiện bắt đầu/kết thúc và đếm được attempt chưa kết thúc.
- `RunLogWriter` nhận trường metadata đã kiểm kiểu/giá trị, không nhận prompt, nội dung hợp đồng hay tên file. Chưa có đường production orchestrator phát RunLog thật; runner D1 hiện vẫn dùng `InMemoryLedger`.

**Duyệt:** logic bookkeeping được sửa trong PR #27, trong phạm vi trên. Không phát hiện lỗi mới có bằng chứng trong phần sửa wrapper/ledger này.

### 2.2. Thiếu hụt đã tái hiện: response JSON lỗi làm mất usage

**Ưu tiên P2 — chặn chốt số đo chi phí, có từ trước PR chứ không phải regression của merge.**

`backend/app/ai/gemini_client.py:84–106` parse nội dung trước khi lấy `usageMetadata`. Khi nội dung không phải JSON hợp lệ, nó raise `ProviderFailure`; exception không mang usage (`provider.py:36–43`), và wrapper ghi 0 token/0 cost (`provider.py:127–128`).

Smoke offline chạy đúng `GeminiProductClient` và `call_with_retry`, chỉ thay transport bằng hàm trong RAM: request đầu HTTP 200 có JSON lỗi cùng usage 100 input/20 output; request retry hợp lệ có usage 110 input/25 output.

```text
transport_calls=2; ledger_calls=2; errors=[invalid_json]
usage transport cung cấp: input=210, output=45
usage ledger giữ lại: input=110, output=25
cost=0.0
```

Đếm request đúng, nhưng mất token của response đầu. Với response thành công, Gemini client cũng không truyền chi phí; `LLMResponse.cost` mặc định 0. Vì vậy không thể diễn giải trường cost hiện tại là số USD đã được đối soát.

**Điều kiện gỡ blocker:** giữ usage được provider trả về cả khi output lỗi; phân biệt usage không biết với usage bằng 0; tính cost bằng giá model có nguồn và thời điểm hiệu lực. Đây là yêu cầu sửa tiếp, chưa được sửa trong review này.

## 3. Thay N2/N5: DOCX numbering và highlight

### 3.1. Dữ liệu thực sự có thể kiểm tra

Đã kiểm kê toàn bộ `.docx` dưới `ai_pipeline/data` và đọc ZIP/XML bằng thư viện chuẩn; chỉ có ba file sau:

| File | Paragraph XML | Direct numPr | Định nghĩa format numbering | Restart/override/style link |
| --- | ---: | ---: | ---: | --- |
| HDLD004.docx | 100 | 0 | 0 | Không có |
| HDLD005.docx | 136 | 0 | 0 | Không có |
| HDLD006.docx | 124 | 0 | 0 | Không có |

D1 chính thức trong pipeline là HDLD001–004; HDLD004 là DOCX duy nhất của D1 ở checkout này. HDLD005/006 không được cộng vào bốn hợp đồng D1. Các nguồn restricted T1 được tài liệu nhắc tới không có đầy đủ file tại máy này; không coi chúng là đã review.

**Kết luận:** các file hiện có chứng minh một phần đường đọc nội dung, không chứng minh auto-numbering. Danh sách decimal/decimalZero/chữ cái/Roman/bullet trong code là khả năng triển khai dự kiến, chưa phải danh sách đã được nghiệm thu trên D1/T1.

### 3.2. Hai lỗi numbering đã chạy tái hiện

Cả hai nằm trong extractor C-08(b) đã có ở PR #27, không phải lỗi N5 vừa merge. Đã tạo DOCX tổng hợp trong thư mục tạm, chạy trực tiếp `extract_docx`, rồi xóa file tạm.

**P2-DOCX-1 — Format override không được dùng khi thay placeholder.**

- Vị trí: `backend/app/document/docx_extractor.py:100–125`.
- Đầu vào: abstract level 0 là decimal, numbering instance override level 0 thành `upperRoman`, mẫu `%1.`.
- Mong đợi: `I. item0`. Thực tế: **`1. item0`**.
- Nguyên nhân: chọn effective level ở đầu hàm nhưng `substitute()` lại đọc format từ abstract `levels`; startOverride của cấp cha chưa xuất hiện cũng có nguy cơ bị bỏ qua.
- Cần sửa: dùng effective level và effective start thống nhất cho cấp hiện tại lẫn cấp được tham chiếu. Canonical sai sẽ kéo theo quote, segmentation và tham chiếu Điều/Khoản sai.

**P2-DOCX-2 — `lvlRestart=0` vẫn bị reset.**

- Vị trí: `backend/app/document/docx_extractor.py:111–115`.
- Đầu vào: cấp con có `lvlRestart=0` (không restart); chuỗi level 0 → 1 → 0 → 1.
- Mong đợi cấp con lần lượt `1`, `2`. Thực tế extractor cho `1`, **`1`**; output đầy đủ: `1. item0`, `1. item1`, `2. item2`, `1. item3`.
- Nguyên nhân: sau mỗi paragraph đều reset toàn bộ bộ đếm cấp sâu hơn, không đọc quy tắc restart.
- Cần sửa: áp dụng restart theo từng level thay vì reset vô điều kiện.

**Giới hạn khác, chưa khẳng định là lỗi đã tái hiện:** chưa có coverage đầy đủ cho numbering style links, suy level từ `pStyle`, shared numbering giữa textbox và đoạn neo, hoặc mọi dạng tracked changes. Không nên quảng bá hỗ trợ toàn bộ OOXML.

### 3.3. Chốt phạm vi kỹ thuật và điều kiện đóng OI-11

- Giữ `python-docx` + đọc OOXML; không viết một bộ render Word hoặc triển khai toàn bộ specification.
- Chưa duyệt OI-11 CLOSED. Cần sửa hai lỗi trên và xác định fixture thực tương ứng với các kiểu thực sự cần hỗ trợ.
- Mỗi fixture phải có expected canonical được đối chiếu với tài liệu gốc; ghi riêng định dạng không hỗ trợ. Không lấy fixture tổng hợp thay cho bằng chứng hợp đồng thực.
- Nếu sửa numbering làm thay đổi canonical text, phải quản lý extraction version và tính lại spans; không dùng lại offset cũ.

### 3.4. Phần frontend được duyệt

Đã đọc `frontend/src/lib/offset.ts`, `segments.ts` và điểm gọi trong `Result.tsx`. `buildCodePointIndex` duyệt theo code point, lưu vị trí UTF-16 và sentinel cuối; `cpSlice` kiểm biên rồi slice theo bảng ánh xạ. Segment builder giữ nguyên canonical text, thêm vùng plain text giữa các clause, không tự normalize.

Đã chạy module TypeScript thật bằng Node với `A😀B`: bảng ánh xạ **[0,1,3,4]**, slice code point `[1,2)` trả đúng **😀**. Đây là smoke thuật toán, **không phải browser/visual review**. Không tìm thấy lỗi mới có bằng chứng trong thuật toán highlight dưới contract span không chồng lấn của backend.

Chốt giữ contract offset Unicode code point. Highlight đúng canonical không bảo đảm canonical trung thực với Word: hai lỗi numbering phía trên vẫn phải giải quyết riêng.

## 4. Chốt OI-03 và OI-05 đến mức bằng chứng cho phép

### 4.1. OI-03 — nhận diện hợp đồng lao động

`scope_precheck.py:31–78` phù hợp mô hình TDD §9: title chỉ xét vùng đầu, cặp party +2, content tối đa +3, structure +1, negative và luật accept tương ứng. Matching dùng bản sao NFC/casefold, không đổi canonical.

Đã chạy precheck trên sáu raw-text snapshot đang có: HDLD001–006 đều accept, score 9. Smoke D1 local của reviewer cũng chạy thành công cả HDLD001–004. Đây là quan sát trên đầu vào dương, **không phải specificity/precision/recall**. Có 11 fixture scope tổng hợp; không tìm thấy gold scope dương/âm thực tế đã adjudicate trong checkout. Trường `gold_scope` của báo cáo T1 là số lượng mẫu đánh giá, không phải nhãn in-scope/out-of-scope.

**Chốt:** tiếp tục dùng ruleset theo TDD cho dev, không thay bằng keyword AI chưa kiểm chứng. **Không đóng OI-03** tới khi có ca dương/âm độc lập, review false accept/false reject và khóa keyword/ngưỡng có version. Không tune theo T1/T2 rồi dùng chính tập đó làm bằng chứng độc lập.

### 4.2. OI-05 — quota/reserve

Main mới đã có dữ liệu hơn hồ sơ MS-2 cũ. Hai artifact lưu kết quả classification D1:

| Artifact | Calls | Input tokens | Output tokens | Lỗi ghi nhận | Cost lưu |
| --- | ---: | ---: | ---: | --- | ---: |
| `evaluation/runs/w4_d1/report.json` | 12 | 22411 | 7518 | Không | 0.0 |
| `evaluation/runs/w4_d1_test2/report.json` | 13 | 22411 | 7372 | http:503 | 0.0 |

Cả hai pin model `gemini-3.5-flash-lite`, prompt `clause_prompt_v1+v04+28987a13`. Đây là artifact đã đọc, **không gọi lại provider để xác minh**. Runner dùng một `InMemoryLedger` tổng cho cả bốn hợp đồng, chỉ chạy clause classification, không phải pipeline đầy đủ hai stage AI hay ledger CSV bền vững theo từng request.

Reviewer chạy benchmark local một lượt/đầu vào: clause counts vẫn 43/47/40/68, planned calls 11/11/9/16. Đây là smoke khả năng chạy, không phải phép đo percentile hiệu năng có ý nghĩa với một lượt/file.

**Chốt:** không đặt giá trị `DAILY_LLM_CALL_QUOTA`/`SESSION_CALL_RESERVE` ở lần review này. Cần usage đầy đủ, chi phí theo giá model, số liệu từng phiên trên cả classify+risk, retry và ngân sách/số phiên vận hành. Giữ demo fail-closed khi thiếu cấu hình; không lấy p95 planned = 16 làm một reserve đã nghiệm thu.

## 5. Thay N1/N2/N3: chốt hướng chính sách đa nhãn OI-10

**Đồng ý chính sách sau về mặt kỹ thuật:**

1. Mặc định một nhãn chính; tối đa ba nhãn, không trùng và phải thuộc vocabulary hiện hành.
2. Chỉ thêm nhãn phụ cho một ý trọn vẹn có chủ đề riêng; không thêm do nhắc thoáng qua keyword.
3. Nhãn chính là chủ đề chiếm nhiều nội dung thực chất nhất; nếu ngang nhau, chọn chủ đề xuất hiện trước. Nhãn phụ đứng sau.
4. `OTHER` chỉ đứng một mình khi không có nhãn cụ thể phù hợp. Clause chỉ gồm heading vẫn gán theo chủ đề heading; classification không nhận role.
5. Pin vocabulary riêng với revision policy/prompt; không tự đổi 12 nhãn hoặc ghi lại gold lịch sử trong review này.
6. Với phép đo có predicted spans khác gold, theo **BRD hiện hành: greedy one-to-one IoU ≥0.5**. Không áp dụng đề xuất overlap-union cũ khi nó mâu thuẫn nguồn ưu tiên cao hơn. Khi chấm đa nhãn, nhãn thừa phải tính FP, nhãn thiếu FN; thống kê nhãn chính và số nhãn trung bình là diagnostics, không thay chỉ số chính.
7. Giữ báo cáo lịch sử cùng phương pháp đã dùng; không đổi cách chấm âm thầm để làm đẹp số liệu.

**Khoảng cách implementation đã chứng minh:** `taxonomy.py:87–105` kiểm số lượng, vocabulary và trùng nhãn nhưng không cấm `OTHER` đi cùng nhãn khác. Smoke trực tiếp `validate_labels(['OTHER','JOB_INFO'])` trả lại cả hai nhãn, không reject. Prompt có hướng dẫn nhưng adapter không enforce exclusivity. Tài liệu hiện cũng công khai việc này; không coi đây là regression mới.

**Kết luận:** hướng chính sách được reviewer chấp thuận, **semantic freeze chưa hoàn tất**. Việc enforce `OTHER`, đồng bộ prompt/adapter/guideline, version phù hợp và kiểm chứng behavior phải thành thay đổi implementation riêng. Không ghi thêm chữ ký N2/N3 vào bảng sign-off, không đánh dấu OI-10 CLOSED khi các phần đó chưa đồng bộ.

Nguồn đối chiếu: `docs/CLAUSE_TAXONOMY_FREEZE.md`, `ai_pipeline/data/docs/annotation_guideline_oi10_draft.md`, `backend/app/clause/taxonomy.py`, `backend/app/ai/prompts/clause_v1.py`, `clause_adapter.py`, `ai_pipeline/evaluation/metrics/clause_classification.py` và BRD §8.3. Bản draft overlap-union không được ưu tiên hơn BRD mới.

## 6. Thay N2/N3: bằng chứng PII và quyết định OI-12

### 6.1. Đã có báo cáo gold mới, nhưng chưa chạy lại được gold tại checkout này

Không còn đúng nếu nói toàn bộ dự án chỉ có gold tự tạo. `reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/result.json` và tài liệu đi kèm đã có báo cáo T1:

| Lát cắt báo cáo | Nhóm nhạy cảm cao | Nhóm tiêu chuẩn | Preserve |
| --- | --- | --- | --- |
| T1 unique 8 | 3/3 | 18/18 | 55/56 |
| T1 real/template 9 | 3/3 | 18/18 | 62/63 |
| T1 composite 10 | 3/3 | 18/18 | 69/70 |
| T2 tham chiếu suy ra | 3/3 | 18/18 | 62/63 |

Point estimates đạt ngưỡng trong báo cáo, nhưng support rất nhỏ. Thêm mẫu synthetic control không tăng số PII; T2 là reference suy ra, không phải tập privacy độc lập đã adjudicate. Không dùng bootstrap CI 100–100 của mẫu toàn-success để tuyên bố population recall hoàn hảo.

Checkout đã cập nhật submodule nhưng không có thư mục restricted/gói gold privacy được các runner tham chiếu. Đã tìm cả file ẩn/ignored và không có gói `T1_privacy_gold_v01`, `*.gold_privacy.json` hoặc P1 đã sinh. Vì vậy **không chạy lại eval gold** hoặc tự bịa số đo mới. Masker hiện tại là `pii_draft_0.4`; baseline cũ trước X-17 là `pii_draft_0.3`, còn báo cáo T1 không pin rõ masker version. Số đo cũ không tự nghiệm thu phiên bản mới.

### 6.2. Đánh giá công cụ và P1

- `eval_pii_gold.py` tính full-span coverage/preserve, báo nhóm thiếu support là `NOT_ESTIMABLE`, tách thông tin lỗi nhạy cảm sang output restricted. Tuy nhiên status/hash chỉ kiểm nếu có; tool không tự chứng nhận gold độc lập hoặc người adjudicate.
- P1 sinh gold từ tọa độ chèn, không gọi detector để tạo gold; hữu ích để tránh chấm detector bằng chính output của nó. Tuy vậy mẫu tên/địa chỉ chủ yếu có anchor, nên không giải quyết đầy đủ rủi ro tên/địa chỉ trong văn xuôi không anchor.
- P1 không thay cho hợp đồng thật độc lập. Output lỗi của `eval_p1.py` có thể chứa giá trị synthetic bị bỏ sót; không dùng tùy tiện với PII thật rồi công bố output.
- Smoke hiện tại chỉ dùng email tổng hợp: masker che email, giữ nguyên độ dài và ký tự non-BMP. **Không suy ra recall thực tế từ smoke này.**

### 6.3. Quyết định reviewer

**Chốt giữ regex/anchor + heuristic và không đưa thêm local NER vào lần tích hợp này.** Chưa có phép đo hiện tại đủ chứng minh cần thêm một component NER ngay; báo cáo T1 hiện có cũng không cho thấy point estimate nhóm B dưới ngưỡng. Đây là quyết định phạm vi triển khai, không phải nghiệm thu privacy hoặc tuyên bố NER không bao giờ cần.

**Giữ OI-12 NARROWED**, chưa CLOSED. Muốn nghiệm thu masker hiện tại cần gói gold được phép truy cập, hash/version, provenance/adjudication, số mẫu theo từng loại PII, số đo độc lập trên phiên bản đang dùng và review lỗi bỏ sót/che nhầm. Mở lại quyết định NER khi dữ liệu real-contract độc lập cho thấy nhóm B <90% hoặc xuất hiện lỗi cần năng lực nhận diện rộng hơn. Không tune trên held-out T1/T2 rồi báo lại như đánh giá độc lập; không suy ra quyền đưa PII lên cloud từ kết quả kỹ thuật.

## 7. Bằng chứng thực thi và giới hạn review

| Kiểm tra đã thực hiện | Kết quả và phạm vi |
| --- | --- |
| CLI benchmark D1 `--repeats 1` | Bốn đầu vào chạy xong, hash được runner kiểm; chỉ local, không gọi LLM |
| Gemini client + retry wrapper, transport giả trong RAM | Hai request được đếm; usage của JSON lỗi bị mất như §2 |
| Inventory ZIP/XML ba DOCX hiện có | Không có định nghĩa auto-numbering để nghiệm thu kiểu numbering thực |
| DOCX tổng hợp override Roman và never-restart | Tái hiện cả hai lỗi §3 bằng extractor thật |
| Scope precheck trên sáu raw-text snapshot | Đều accept/score 9; chỉ ca dương, không phải accuracy |
| Node chạy `offset.ts` với non-BMP | Slice đúng emoji; không chạy browser |
| Python chạy validator và masker | OTHER mixed được chấp nhận; smoke email tổng hợp giữ length/non-BMP |

Không chạy full pytest/build/lint; không gọi Gemini thật; không đo lại gold T1/T2, không gửi PII ra ngoài. Một môi trường `backend/.venv` thiếu `lxml` khi thử extractor; smoke DOCX đã được thực hiện thành công bằng Python đang chạy được benchmark, không coi lỗi môi trường đó là lỗi sản phẩm.

Ba reviewer kỹ thuật độc lập được phân công provider/quota, DOCX/scope/frontend và privacy/taxonomy; kết luận được tổng hợp vào đây. Findings numbering ban đầu từ source đã được reviewer chính chạy tái hiện trước khi ghi là lỗi xác nhận.

## 8. Những thông tin cũ cần đọc lại sau merge và bước xử lý

- Hồ sơ `MS2_CONFIG_REVIEW_N4.md` nói chưa có actual calls/tokens: nay đã có **artifact classification**, nhưng chưa có cost/per-session end-to-end đầy đủ.
- Hồ sơ cũ nói corpus DRAFT: manifest hiện là **APPROVED**. Không dùng trạng thái cũ làm blocker; approval corpus không bù cho thiếu bằng chứng chi phí hoặc privacy.
- Nhận xét “chỉ có PII gold tự tạo” không mô tả đầy đủ main mới: đã có báo cáo T1 gold, nhưng source/gold restricted không hiện diện tại checkout và version masker cần đối chiếu lại.

**Thứ tự đề nghị xử lý sau review:**

1. Sửa hai lỗi DOCX đã xác nhận, quản lý extraction version và thêm regression theo hành vi; lấy mẫu thực để kết thúc OI-11.
2. Sửa đường giữ usage của response lỗi và bổ sung pricing có nguồn trước khi chốt OI-05; ghép ledger/RunLog vào pipeline thực ở phần tích hợp.
3. Triển khai chính sách OI-10 đã chấp thuận, đồng bộ guideline/prompt/adapter/version; khi hoàn tất mới cập nhật trạng thái đóng.
4. Lấy quyền truy cập gold restricted để kiểm chứng PII phiên bản hiện tại, bổ sung scope gold dương/âm; giữ nguyên ranh giới Dev/Test.

Đây là các việc được nêu ra từ review, **chưa thực hiện sửa code**. File này là kết luận và bằng chứng để N4/nhóm giao việc hoặc quyết định thay đổi tiếp theo; không ghi tất cả OI thành CLOSED để thay cho phần việc chưa làm.
