# Kho luật tầng 1 — hồ sơ C-12/X-03 (N2)

Trạng thái **DRAFT — KHÔNG ĐƯỢC DÙNG ĐỂ CITE / ĐÁNH GIÁ HỢP ĐỒNG**. Loader từ chối
`release_status: DRAFT` theo mặc định; chỉ được mở bằng `allow_draft=True` cho
kiểm tra dữ liệu offline. Không sửa `release_status` trước khi có sign-off
Data Lead, N3 và người kiểm tra nội dung/hiệu lực pháp lý.

## Nguồn và phạm vi

- Văn bản gốc **Bộ luật Lao động 45/2019/QH14**, có hiệu lực từ 01/01/2021:
  https://vanban.chinhphu.vn/?classid=1&docid=198540&pageid=27160&typegroupid=3
- **Văn bản hợp nhất 18/VBHN-VPQH (12/02/2026)**, nguồn tra cứu các lần sửa đổi:
  https://vanban.chinhphu.vn/?classid=0&docid=217002&pageid=27160
- Công báo VBHN số 18: https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971/62878.htm

## Kiểm kê snapshot hiện tại

`provisions.jsonl` hiện có **16 provision candidate**, 16 `citation_id` duy
nhất: Điều 13 (2), Điều 14 (2), Điều 15 (2), Điều 16 (2), Điều 17 (3) và
Điều 21 khoản 1 (5 điểm c/d/đ/g/i). `label_map.yaml` có 5 nhãn ánh xạ tới
5 điểm Điều 21. Đây là số liệu cấu trúc của working tree; không đồng nghĩa
với việc 16 provision đã được rà soát hoặc đủ để chạy baseline có ý nghĩa.

Đối chiếu máy ở dạng chuỗi chuẩn hóa khoảng trắng với OCR candidate của
18/VBHN-VPQH (nguồn hợp nhất ban hành 12/02/2026) cho kết quả 7/16 nội dung
khớp nguyên văn, 9/16 không khớp nguyên văn. OCR candidate chưa được soát
trang; khác biệt có thể do OCR, sửa đổi luật hoặc cách chia provision. Vì vậy
không tự sửa câu chữ, `version` hay khoảng hiệu lực theo phép so khớp này.
Toàn bộ 16 dòng tiếp tục là `PENDING_LEGAL_REVIEW`; cần đối chiếu PDF Công
báo/VBHN và lịch sử sửa đổi trước khi dùng làm nguồn retrieval.

Năm điểm Điều 21 nêu trên là **ứng viên nhập liệu ban đầu** được đối chiếu sơ
bộ với văn bản công bố. Ngày 01/01/2021 là ngày có hiệu lực của Bộ luật gốc,
**chưa phải xác nhận hiệu lực hiện tại của từng điểm**.

`edges.jsonl` hiện có một cạnh `REFERS_TO` cho `BLLD2019:art14:cl1` →
`BLLD2019:art14:cl2`. Cạnh thể hiện đúng tham chiếu “khoản 2 Điều này” ở
khoản 1 Điều 14, đã được đối chiếu trực quan tại trang 7 của PDF chính thức
18/VBHN-VPQH ngày 12/02/2026 (SHA-256 của PDF đã kiểm tra:
`5A01A5B4B778B78C7BC9372E3A7270735BD98C28160604BFF95DB06BB3345A6F`). Đây chỉ
là xác minh quan hệ tham chiếu theo nguồn hợp nhất; không xác nhận nguyên văn
của snapshot 45/2019/QH14, hiệu lực hiện tại của hai provision, hay diễn giải
pháp lý. Cạnh còn ở trạng thái chờ reviewer pháp lý độc lập và corpus vẫn DRAFT.
`edge_suggestions.jsonl` chỉ dành cho gợi ý chưa duyệt và **không được loader đọc**.
`label_map.yaml` chứa trọng số đề xuất kỹ thuật để thử sau khi corpus được duyệt,
không phải nhãn rủi ro/nhận định pháp lý. Nguồn quote đầy đủ và hiệu lực
phải được đối chiếu lần cuối với bản Công báo/VBHN khi đóng phiên bản chính thức.

## Danh mục tầng 1 đề xuất để nhóm duyệt (chưa chốt)

| Ưu tiên | Văn bản và nguồn tra cứu chính thức | Lý do đề xuất | Cổng còn mở |
| --- | --- | --- | --- |
| P0 | [Bộ luật Lao động 45/2019/QH14](https://vanban.chinhphu.vn/?classid=1&docid=198540&pageid=27160), đối chiếu [VBHN 18/VBHN-VPQH ngày 12/02/2026](https://vanban.chinhphu.vn/?classid=0&docid=217002&pageid=27160) | Hợp đồng lao động: nội dung, giao kết, thực hiện, sửa đổi, chấm dứt | Xác nhận từng điều/khoản/điểm, sửa đổi và các khoảng hiệu lực; VBHN chỉ hỗ trợ tra cứu |
| P1 | [Nghị định 145/2020/NĐ-CP](https://vanban.chinhphu.vn/?docid=201967&pageid=27160) | Hướng dẫn điều kiện lao động và quan hệ lao động | Rà soát sửa đổi, điều khoản áp dụng và thời điểm hiệu lực; không suy từ văn bản gốc ra hiệu lực hiện hành |
| P1 | [Thông tư 10/2020/TT-BLĐTBXH](https://vbpl.vn/botuphap/Pages/vbpq-toanvan.aspx?ItemID=146696) | Hướng dẫn chi tiết nội dung hợp đồng lao động | Kiểm tra lịch sử hiệu lực, phạm vi điều khoản và văn bản thay thế/sửa đổi trước nhập liệu |

Đây là **shortlist phục vụ chốt phạm vi**, chưa phải danh mục được N1/N3 và
reviewer pháp lý phê duyệt. `PROGRESS.md` gọi việc chốt danh mục là OI-02;
trong SRS §13, mã OI-02 lại dành cho quy ước PII placeholder (đã CLOSED).
Nhóm cần thống nhất mã theo dõi, tránh dùng nhầm hai quyết định khác nhau.

Hồ sơ sign-off cho từng provision/cạnh trước khi đề xuất `APPROVED` cần ghi
`document_id`, văn bản/bản hợp nhất tham chiếu, nguồn truy cập, điều/khoản/điểm,
nguyên văn sau đối chiếu, `effective_from`/`effective_to` và căn cứ thay đổi,
reviewer N2, reviewer pháp lý, ngày duyệt, cùng diff/checksum phiên bản.
Manifest SHA-256 chỉ phát hiện dữ liệu thay đổi; **không chứng minh văn bản
đúng pháp luật hoặc đã được người có thẩm quyền duyệt**.

## Quy ước C-12(b) đang kiểm thử

`BaselineRetriever` nhận corpus đã validate, mặc định từ chối `DRAFT`.
Mỗi ngày phân tích chỉ lấy provision đang hiệu lực, chọn đúng một version
cho mỗi `citation_id` và tính điểm `0.70 * label_weight + 0.30 * bm25_normalized`.
Với 2–3 nhãn clause, dùng trọng số **lớn nhất được cấu hình tường minh** để
tránh tự cộng điểm; BM25 dùng tokenizer Unicode theo từ đơn giản, chuẩn hóa
trên các provision đang hiệu lực và chặn điểm BM25 âm về 0.
Đây là các quy ước kỹ thuật cần đánh giá lại trên D1/D2, **chưa phải phép
đo recall hoặc bảo đảm chất lượng truy xuất tiếng Việt**. `baseline_pool`
chứa tối đa `final_k` và `seeds` chỉ là tối đa `seed_k` phần tử đầu của pool
cho Data Graph; graph-disabled/fallback vẫn phải dùng toàn pool.

`DataGraph` (C-13a) hiện dựng cấu trúc `PARENT_OF` từ `parent_path`
và index cạnh `REFERS_TO/GUIDES` đã có trong `edges.jsonl`; các chiều
duyệt vẫn giữ hướng gốc để C-13b tính bonus. Fixture mô phỏng edge MANUAL,
nhưng **corpus luật thật chưa có cạnh nào được reviewer duyệt**. Bước
`DataGraph.expand`, cap/ranking/fallback (C-13b) còn để thực hiện riêng.

## Quy trình duyệt và tái tạo

1. N2 và reviewer xác nhận nguyên văn, article/clause/point, nguồn và từng mốc
   hiệu lực; ghi reviewer/date/source version vào hồ sơ review trước khi chuyển
   corpus sang APPROVED.
2. Chốt danh mục tầng 1 và nhãn (OI-02/OI-10) cùng N1/N3; chỉ đưa cạnh đã
   kiểm chứng vào `edges.jsonl`, `origin: MANUAL`.
3. Sau mọi sửa đổi, chạy `python -m scripts.update_legal_corpus_checksums`,
   kiểm thử `pytest tests/unit/test_legal_corpus.py`, rồi review Git diff.
4. `effective_to` là **ngày hiệu lực cuối cùng, tính bao gồm** theo quy ước
   kỹ thuật hiện tại (cần nhóm chấp thuận nếu tài liệu có quy ước khác).

Luồng nguồn luật tách biệt với `ai_pipeline/data`, vốn là submodule lưu dữ
liệu hợp đồng do N2 quản lý. Đường dẫn đặt theo TDD §14.1 tại repo nhóm:
`data/legal_corpus/`.

## Line ending (LF) và checksum

`provisions.jsonl`, `edges.jsonl`, `label_map.yaml` được băm SHA-256 trên **byte LF** đã commit
(`.gitattributes` đặt `eol=lf`, `.editorconfig` cho editor). Nếu loader báo lệch checksum trên máy
Windows/VS Code sau khi editor đổi sang CRLF: chạy `git checkout -- data/legal_corpus` (hoặc
`git add --renormalize data/legal_corpus`) để khôi phục LF. **Không** chuyển sang CRLF rồi băm lại:
Git vẫn lưu LF nên checksum CRLF sẽ lệch trên CI và mọi máy khác, loader sẽ từ chối corpus.
