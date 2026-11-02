# Kiểm kê tiến độ Data Lead (N2) — 01/11/2026

## Cách tính

Mẫu số là 19 checkbox cấp đầu việc nằm trực tiếp dưới `**N2**` trong các
tuần 1–7 của `PROGRESS.md`; không đếm checkbox con, việc của vai trò khác
hoặc mốc tuần như đầu việc. Tại thời điểm kiểm kê có 4 mục `[x]` và 15
mục `[ ]` tại lần kiểm kê ban đầu ngày 01/11: **4/19 = 21,1% theo số đầu
việc**, chưa phải tỷ lệ khối lượng,
giờ công hay giá trị nghiệm thu. Đạt ít nhất 50% theo cách đếm này cần 10/19
mục hoàn thành, tức thêm 6 mục có bằng chứng.

## Đã đóng theo PROGRESS.md

- Tuần 1: định dạng corpus và provision mẫu; danh mục luật tầng 1 bản nháp.
- Tuần 3: C-12(a) loader/validator với fixture.
- Tuần 4: C-12(b) BaselineRetriever với fixture.

## Cập nhật ngày 01/11/2026

C-13(b) đã hoàn tất phạm vi kỹ thuật bằng fixture/offline và được đánh dấu
`[x]` trong PROGRESS.md. C-18 nay có loader, M3a/M4/M5, M8 và paired fixture
runner, nhưng checkbox cấp đầu việc vẫn mở vì còn production adapter/metrics
khác/gold được duyệt. Checklist N2 vẫn **5/19 = 26,3%**; đây không phải tỷ lệ
khối lượng hay nghiệm thu C-18.

- 25 test Data Graph và 35 test graph/retriever đạt.
- C-18 fixture core: dataset loader (7 test), M3a/M4/M5 (9 test), M8 +
  callback runner (15 test); tổng 31 test trọng tâm đạt. Chưa có tích hợp
  pipeline thật, chưa chạy T2 hoặc kết quả retrieval trên gold đã duyệt.
- Toàn suite đạt; 9 test bị skip vì thiếu private data submodule.
- Ruff các file legal và test liên quan đạt; `git diff --check` đạt.
- Không đo Recall@5; corpus DRAFT và gold D1 chưa được duyệt.

## Có tiến triển nhưng chưa đóng

- C-13(a): index graph và PARENT_OF có test; cạnh REFERS_TO/GUIDES thật chưa
  được người kiểm pháp lý duyệt.
- C-13(b): code/test fixture đã đóng; review độc lập phát hiện, sau đó đã
  sửa seed vượt `final_k`, lệch budget baseline/graph, xếp hạng child ngoài
  baseline và rank metadata; chưa nối runtime production và không
  chứng minh chất lượng truy xuất trên luật đã duyệt. Coverage gồm
  direction/ranking, tổng cap/con cap, dedupe nhiều seed, seed-first, cùng
  final_k, graph-off, fallback, lỗi baseline và invalid caps.
- X-03: receipt nguồn và Điều 20–22 dạng nháp đã merge ở repo dữ liệu qua
  PR #13; chưa là corpus APPROVED hoặc đã đồng bộ sang pipeline.
- X-04: adapter nhãn v06 đã có nhưng gold segmentation D1, lựa chọn bốn
  hợp đồng và nhãn kiểm duyệt vẫn mở.
- X-10: dữ liệu T1 được chấp nhận hiện 0/10; cần quyền xử lý, khử PII và
  nghiệm thu độc lập.

## Cổng còn lại để đạt 50% và thứ tự thực hiện

1. C-13(b) technical fixture, tests, Ruff và full suite đã hoàn tất.
2. Chốt D1 và gold segmentation/privacy với người phụ trách; không biến
   nhãn lịch sử hoặc OCR nháp thành gold tự động.
3. Đối chiếu nguồn luật, hiệu lực và cạnh graph có reviewer trước khi đóng
   C-13(a), X-03 và kho luật tầng 1.
4. C-18 tiếp: nối adapter vào pipeline đánh giá khi upstream prediction APIs
   ổn định; triển khai M1/M2/M6/M7, ledger/schema báo cáo; chỉ chạy D1/T2 sau
   khi gold và corpus được duyệt.

Kiểm tra ngày 01/11: graph/retriever trước đó **35 passed**; evaluation focused
suite **31 passed**; toàn suite đạt với **9 skipped** vì thiếu private data
submodule. Ruff scoped evaluation đạt; `git diff --check` đạt. Chưa kiểm CI
GitHub cho các thay đổi này.
